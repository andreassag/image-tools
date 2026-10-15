import io
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from PIL import Image

from image_tools.common import resolve_target_format_and_ext, save_processed_image
from image_tools.converter import ConversionResult, prepare_image_for_export
from image_tools.metadata import build_exif


def parse_size_bytes(size_str: str) -> int:
    """
    Parse a human-readable size string (e.g. '500KB', '2MB', '1.5M', '500000') into bytes.
    """
    s = size_str.strip().lower()
    match = re.match(r"^([0-9.]+)\s*([a-z]*)$", s)
    if not match:
        raise ValueError(f"Invalid size specification: '{size_str}'")

    val_float = float(match.group(1))
    unit = match.group(2)

    units_map = {
        "": 1,
        "b": 1,
        "bytes": 1,
        "k": 1024,
        "kb": 1024,
        "kib": 1024,
        "m": 1024 * 1024,
        "mb": 1024 * 1024,
        "mib": 1024 * 1024,
        "g": 1024 * 1024 * 1024,
        "gb": 1024 * 1024 * 1024,
        "gib": 1024 * 1024 * 1024,
    }

    if unit not in units_map:
        raise ValueError(f"Unknown size unit: '{unit}' in '{size_str}'")

    return int(val_float * units_map[unit])


def sanitize_exif(
    exif: Image.Exif,
    strip_exif: bool = False,
    strip_gps: bool = False
) -> Optional[Image.Exif]:
    """
    Apply EXIF metadata privacy sanitization:
    - strip_exif: Returns empty EXIF object.
    - strip_gps: Strips GPSInfo tag (34853).
    """
    if strip_exif:
        return Image.Exif()

    clean_exif = Image.Exif()
    for k, v in exif.items():
        if strip_gps and k == 34853:
            continue
        clean_exif[k] = v

    return clean_exif


def compress_image(
    input_path: Path,
    output_dir: Optional[Path] = None,
    target_size: Optional[str] = None,
    quality: int = 85,
    format: Optional[str] = None,
    strip_exif: bool = False,
    strip_gps: bool = False,
    touch_mtime: bool = False,
    bg_color: Tuple[int, int, int] = (255, 255, 255),
    dry_run: bool = False
) -> ConversionResult:
    """
    Compress an image to target quality or target maximum file size.
    """
    input_path = Path(input_path).resolve()
    if not input_path.exists():
        return ConversionResult(
            input_path=input_path,
            success=False,
            error_message=f"File not found: {input_path}"
        )

    target_fmt, target_ext = resolve_target_format_and_ext(format, input_path)

    target_dir = Path(output_dir).resolve() if output_dir else input_path.parent
    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)

    result = ConversionResult(input_path=input_path)
    target_bytes = parse_size_bytes(target_size) if target_size else None

    try:
        with Image.open(input_path) as img:
            dpi = img.info.get("dpi", (300.0, 300.0))
            icc_profile = img.info.get("icc_profile")
            n_frames = getattr(img, "n_frames", 1)

            for frame_idx in range(n_frames):
                img.seek(frame_idx)
                frame_img = img.copy()

                out_filename = (
                    f"{input_path.stem}_p{frame_idx + 1}{target_ext}"
                    if n_frames > 1 else f"{input_path.stem}{target_ext}"
                )
                out_path = target_dir / out_filename

                raw_exif = build_exif(
                    img=frame_img,
                    file_path=input_path,
                    metadata_mode="strip" if strip_exif else "preserve",
                    dpi=dpi
                )
                exif_obj = sanitize_exif(raw_exif, strip_exif=strip_exif, strip_gps=strip_gps)

                export_img = prepare_image_for_export(frame_img, target_fmt, bg_color=bg_color)

                final_quality = quality
                if target_bytes and target_fmt in ("JPEG", "JPG", "WEBP"):
                    low_q, high_q = 5, 95
                    best_q = low_q

                    while low_q <= high_q:
                        mid_q = (low_q + high_q) // 2
                        buf = io.BytesIO()
                        save_opts: Dict[str, Any] = {"dpi": dpi, "quality": mid_q, "optimize": True}
                        if target_fmt in ("JPEG", "JPG") and exif_obj:
                            save_opts["exif"] = exif_obj
                        elif target_fmt == "WEBP" and exif_obj:
                            try:
                                save_opts["exif"] = exif_obj.tobytes()
                            except Exception:
                                pass

                        export_img.save(buf, target_fmt, **save_opts)
                        size_bytes = buf.tell()

                        if size_bytes <= target_bytes:
                            best_q = mid_q
                            low_q = mid_q + 1
                        else:
                            high_q = mid_q - 1

                    final_quality = best_q

                if not dry_run:
                    save_processed_image(
                        img=export_img,
                        out_path=out_path,
                        target_format=target_fmt,
                        quality=final_quality,
                        exif=exif_obj,
                        dpi=dpi,
                        icc_profile=icc_profile,
                        touch_mtime=touch_mtime,
                        optimize=True
                    )

                result.output_paths.append(out_path)
                result.frames_processed += 1

    except Exception as e:
        result.success = False
        result.error_message = str(e)

    return result
