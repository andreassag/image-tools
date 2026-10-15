import argparse
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import List, Dict, Any, Callable, Optional, Set, Tuple
from PIL import Image

from image_tools.metadata import sync_file_mtime


SUPPORTED_IMAGE_EXTENSIONS: Set[str] = {
    ".tif", ".tiff", ".jpg", ".jpeg", ".png", ".webp", ".bmp"
}

FORMAT_EXT_MAP: Dict[str, str] = {
    "JPEG": ".jpg",
    "JPG": ".jpg",
    "PNG": ".png",
    "WEBP": ".webp",
    "TIFF": ".tif",
    "TIF": ".tif",
    "BMP": ".bmp",
}


def resolve_target_format_and_ext(
    format_name: Optional[str],
    source_path: Path
) -> Tuple[str, str]:
    """
    Resolve canonical image format string (e.g. 'JPEG') and target extension (e.g. '.jpg').
    """
    target_fmt = format_name.upper() if format_name else source_path.suffix.lstrip(".").upper()
    if target_fmt == "JPG":
        target_fmt = "JPEG"
    elif target_fmt == "TIF":
        target_fmt = "TIFF"

    if target_fmt not in ("JPEG", "PNG", "WEBP", "TIFF", "BMP"):
        target_fmt = "JPEG"

    target_ext = FORMAT_EXT_MAP.get(target_fmt, f".{target_fmt.lower()}")
    return target_fmt, target_ext


def save_processed_image(
    img: Image.Image,
    out_path: Path,
    target_format: str,
    quality: int = 95,
    exif: Optional[Image.Exif] = None,
    dpi: Optional[Tuple[float, float]] = None,
    icc_profile: Optional[bytes] = None,
    touch_mtime: bool = False,
    optimize: bool = False
) -> None:
    """
    Save processed image with format settings, EXIF metadata, ICC color profile, and timestamp sync.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    target_fmt = target_format.upper()
    if target_fmt == "JPG":
        target_fmt = "JPEG"

    save_kwargs: Dict[str, Any] = {}
    if dpi:
        save_kwargs["dpi"] = dpi
    if optimize:
        save_kwargs["optimize"] = True
    if icc_profile:
        save_kwargs["icc_profile"] = icc_profile

    if target_fmt in ("JPEG", "WEBP"):
        save_kwargs["quality"] = quality

    if exif:
        if target_fmt == "JPEG":
            save_kwargs["exif"] = exif
        elif target_fmt in ("WEBP", "PNG"):
            try:
                save_kwargs["exif"] = exif.tobytes()
            except Exception:
                pass

    img.save(out_path, target_fmt, **save_kwargs)

    if touch_mtime and exif:
        date_str = str(exif.get(306, ""))
        if date_str:
            sync_file_mtime(out_path, date_str)


def find_image_files(
    target_path: Path,
    recursive: bool = False,
    valid_exts: Optional[Set[str]] = None
) -> List[Path]:
    """
    Find image files at target path (file or directory).
    """
    exts = set(e.lower() for e in valid_exts) if valid_exts else SUPPORTED_IMAGE_EXTENSIONS

    if target_path.is_file():
        if target_path.suffix.lower() in exts:
            return [target_path]
        return []

    if target_path.is_dir():
        pattern = "**/*" if recursive else "*"
        return sorted([
            f for f in target_path.glob(pattern)
            if f.is_file() and f.suffix.lower() in exts
        ])

    return []


def add_common_batch_args(parser: argparse.ArgumentParser) -> None:
    """Add standard batch processing arguments to an ArgumentParser."""
    parser.add_argument(
        "input_path",
        nargs="?",
        default=".",
        help="Path to an image file or a directory containing images (default: current directory)."
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=str,
        default=None,
        help="Directory to save output images (default: same directory as input)."
    )
    parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        help="Recursively search subdirectories for images."
    )
    parser.add_argument(
        "-j", "--jobs",
        type=int,
        default=4,
        help="Number of concurrent worker processes for batch processing (default: 4)."
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without writing files to disk."
    )


def run_batch(
    tasks: List[Dict[str, Any]],
    worker_fn: Callable[[Dict[str, Any]], Any],
    jobs: int = 4,
    dry_run: bool = False
) -> Tuple[int, int]:
    """
    Execute batch tasks sequentially or in parallel using ProcessPoolExecutor.
    Returns (success_count, failure_count).
    """
    if not tasks:
        print("No tasks to process.")
        return 0, 0

    print(f"Found {len(tasks)} image(s) to process.")
    if dry_run:
        print("[DRY RUN MODE ENABLED]")

    successful = 0
    failed = 0

    if len(tasks) == 1 or jobs <= 1:
        for kwargs in tasks:
            try:
                res = worker_fn(kwargs)
                if res.success:
                    successful += 1
                    for out_p in res.output_paths:
                        print(f"Processed: {res.input_path.name} -> {out_p.name}")
                else:
                    failed += 1
                    print(f"Failed: {res.input_path.name} | Error: {res.error_message}")
            except Exception as exc:
                failed += 1
                inp = kwargs.get("input_path")
                inp_name = inp.name if isinstance(inp, Path) else str(inp)
                print(f"Failed: {inp_name} | Error: {exc}")
    else:
        with ProcessPoolExecutor(max_workers=jobs) as executor:
            future_to_task = {executor.submit(worker_fn, kw): kw for kw in tasks}
            for future in as_completed(future_to_task):
                try:
                    res = future.result()
                    if res.success:
                        successful += 1
                        for out_p in res.output_paths:
                            print(f"Processed: {res.input_path.name} -> {out_p.name}")
                    else:
                        failed += 1
                        print(f"Failed: {res.input_path.name} | Error: {res.error_message}")
                except Exception as exc:
                    failed += 1
                    task_kw = future_to_task[future]
                    inp = task_kw.get("input_path")
                    inp_name = inp.name if isinstance(inp, Path) else str(inp)
                    print(f"Failed: {inp_name} | Worker Exception: {exc}")

    print(f"\nSummary: {successful} succeeded, {failed} failed.")
    return successful, failed
