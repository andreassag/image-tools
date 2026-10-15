import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from PIL import Image
from PIL.ExifTags import TAGS

from image_tools.converter import ConversionResult
from image_tools.metadata import extract_datetime, sync_file_mtime

TAG_NAME_TO_ID: Dict[str, int] = {name.lower(): tag_id for tag_id, name in TAGS.items()}

WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10))
}


def parse_tag_key(key_str: str) -> int:
    """Parse tag name (e.g. 'Make', 'artist') or numeric ID (e.g. '271') to EXIF tag ID."""
    s = key_str.strip()
    if s.isdigit():
        return int(s)

    lower_key = s.lower()
    if lower_key in TAG_NAME_TO_ID:
        return TAG_NAME_TO_ID[lower_key]

    raise ValueError(f"Unknown EXIF tag name: '{key_str}'")


def parse_tag_value(val: Any) -> Any:
    """Parse string value into integer or float if applicable, otherwise strip/leave as string."""
    if not isinstance(val, str):
        return val
    v = val.strip()
    if re.match(r"^-?\d+$", v):
        try:
            return int(v)
        except ValueError:
            pass
    if re.match(r"^-?\d+\.\d+$", v):
        try:
            return float(v)
        except ValueError:
            pass
    return v


def sanitize_filename_component(val: str) -> str:
    """Sanitize string for safe use in file paths across Linux, macOS, and Windows."""
    if not val:
        return "unknown"
    cleaned = re.sub(r'[\\/:*?"<>|\s]+', "_", val.strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_. ")
    if cleaned.upper() in WINDOWS_RESERVED_NAMES:
        cleaned = f"{cleaned}_file"
    return cleaned or "unknown"


def export_exif_json(input_path: Path) -> Dict[str, Any]:
    """Extract EXIF metadata from image as a serializable dictionary."""
    input_path = Path(input_path).resolve()
    with Image.open(input_path) as img:
        exif = img.getexif()
        result: Dict[str, Any] = {}
        if exif:
            for tag_id, val in exif.items():
                tag_name = TAGS.get(tag_id, f"Tag_{tag_id}")
                if isinstance(val, bytes):
                    try:
                        val = val.decode("utf-8", errors="ignore").strip()
                    except Exception:
                        val = str(val)
                result[tag_name] = val
        return result


def set_exif_tags(
    input_path: Path,
    output_dir: Optional[Path] = None,
    set_tags: Optional[Dict[str, Any]] = None,
    delete_tags: Optional[List[str]] = None,
    dry_run: bool = False
) -> ConversionResult:
    """Set or delete specific EXIF tags in an image."""
    input_path = Path(input_path).resolve()
    if not input_path.exists():
        return ConversionResult(
            input_path=input_path,
            success=False,
            error_message=f"File not found: {input_path}"
        )

    target_dir = Path(output_dir).resolve() if output_dir else input_path.parent
    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)

    out_path = target_dir / input_path.name
    result = ConversionResult(input_path=input_path)

    try:
        with Image.open(input_path) as img:
            dpi = img.info.get("dpi", (300.0, 300.0))
            icc_profile = img.info.get("icc_profile")
            exif = img.getexif()

            if delete_tags:
                for t in delete_tags:
                    try:
                        tag_id = parse_tag_key(t)
                        if tag_id in exif:
                            del exif[tag_id]
                    except ValueError:
                        pass

            if set_tags:
                for k, v in set_tags.items():
                    tag_id = parse_tag_key(k)
                    exif[tag_id] = parse_tag_value(v)

            if not dry_run:
                save_fmt = img.format if img.format else "JPEG"
                if save_fmt.upper() == "JPG":
                    save_fmt = "JPEG"
                save_kwargs: Dict[str, Any] = {"dpi": dpi}
                if icc_profile:
                    save_kwargs["icc_profile"] = icc_profile

                if save_fmt.upper() in ("JPEG", "JPG"):
                    save_kwargs["quality"] = 95
                    save_kwargs["exif"] = exif
                elif save_fmt.upper() in ("WEBP", "PNG"):
                    if save_fmt.upper() == "WEBP":
                        save_kwargs["quality"] = 95
                    try:
                        save_kwargs["exif"] = exif.tobytes()
                    except Exception:
                        pass
                else:
                    save_kwargs["exif"] = exif

                img.save(out_path, save_fmt, **save_kwargs)

            result.output_paths.append(out_path)
            result.frames_processed += 1

    except Exception as e:
        result.success = False
        result.error_message = str(e)

    return result


def rename_image_by_metadata(
    input_path: Path,
    pattern: str = "{date}_{make}_{model}_{stem}.{ext}",
    output_dir: Optional[Path] = None,
    dry_run: bool = False
) -> ConversionResult:
    """
    Rename image based on metadata pattern template.
    Placeholders: {date}, {make}, {model}, {software}, {stem}, {ext}
    """
    input_path = Path(input_path).resolve()
    if not input_path.exists():
        return ConversionResult(
            input_path=input_path,
            success=False,
            error_message=f"File not found: {input_path}"
        )

    target_dir = Path(output_dir).resolve() if output_dir else input_path.parent
    result = ConversionResult(input_path=input_path)

    try:
        with Image.open(input_path) as img:
            exif = img.getexif()

            raw_date = extract_datetime(img, input_path, strategy="auto")
            clean_date = raw_date.replace(":", "-").replace(" ", "_")

            make = sanitize_filename_component(str(exif.get(271, "UnknownMake")))
            model = sanitize_filename_component(str(exif.get(272, "UnknownModel")))
            software = sanitize_filename_component(str(exif.get(305, "UnknownSoftware")))
            stem = input_path.stem
            ext = input_path.suffix.lstrip(".")

            new_name = pattern.format(
                date=clean_date,
                make=make,
                model=model,
                software=software,
                stem=stem,
                ext=ext
            )

            out_path = target_dir / new_name

            # Collision resolution: append _1, _2 if target file exists and is not the same input file
            base_stem = out_path.stem
            counter = 1
            while out_path.exists() and out_path != input_path:
                out_path = target_dir / f"{base_stem}_{counter}.{ext}"
                counter += 1

            if not dry_run and out_path != input_path:
                target_dir.mkdir(parents=True, exist_ok=True)
                os.rename(input_path, out_path)

            result.output_paths.append(out_path)
            result.frames_processed += 1

    except Exception as e:
        result.success = False
        result.error_message = str(e)

    return result
