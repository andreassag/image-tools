import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from PIL import Image

PRESETS: Dict[str, Dict[int, Any]] = {
    "canon_lide_400": {
        271: "Canon",                # Make
        272: "CanoScan LiDE 400",   # Model
        305: "IJ Scan Utility",     # Software
        274: 1,                      # Orientation
        296: 2,                      # ResolutionUnit (Inches)
        531: 1,                      # YCbCrPositioning
    },
    "generic_scanner": {
        271: "Generic",              # Make
        272: "Flatbed Scanner",      # Model
        305: "image-tools",          # Software
        274: 1,                      # Orientation
        296: 2,                      # ResolutionUnit (Inches)
        531: 1,                      # YCbCrPositioning
    },
}


def extract_datetime(
    img: Image.Image,
    file_path: Path,
    strategy: str = "auto"
) -> str:
    """
    Extract date/time string formatted as 'YYYY:MM:DD HH:MM:SS'.
    
    Strategies:
    - 'exif': Check EXIF tag 306 or internal TIFF tag 306.
    - 'filename': Look for YYYY-MM-DD or YYYYMMDD in filename.
    - 'mtime': Use file modification timestamp.
    - 'auto': Try exif -> filename -> mtime.
    """
    if strategy in ("auto", "exif"):
        # 1. EXIF tag 306 (DateTime)
        try:
            exif = img.getexif()
            if exif and 306 in exif and exif[306]:
                return str(exif[306])
        except Exception:
            pass

        # 2. Internal TIFF tag 306
        if hasattr(img, "tag_v2") and 306 in img.tag_v2:
            return str(img.tag_v2[306])

        if strategy == "exif":
            # Fallback if exif strategy was explicitly requested but tag missing
            pass

    if strategy in ("auto", "filename"):
        # Match YYYY-MM-DD, YYYY_MM_DD, or YYYYMMDD in filename
        name = file_path.stem
        match = re.search(r"(\d{4})[-_]?(\d{2})[-_]?(\d{2})(?:[-_ ]?(\d{2})[-_]?(\d{2})[-_]?(\d{2}))?", name)
        if match:
            y, m, d, hh, mm, ss = match.groups()
            hh = hh or "00"
            mm = mm or "00"
            ss = ss or "00"
            return f"{y}:{m}:{d} {hh}:{mm}:{ss}"

    # Default fallback to file mtime or current time
    try:
        mtime = os.path.getmtime(file_path)
        return datetime.fromtimestamp(mtime).strftime("%Y:%m:%d %H:%M:%S")
    except Exception:
        return datetime.now().strftime("%Y:%m:%d %H:%M:%S")


def build_exif(
    img: Image.Image,
    file_path: Path,
    metadata_mode: str = "preserve",
    preset_name: Optional[str] = None,
    date_strategy: str = "auto",
    custom_exif: Optional[Dict[int, Any]] = None,
    dpi: Optional[tuple[float, float]] = None
) -> Image.Exif:
    """
    Construct or modify PIL.Image.Exif object based on settings.
    """
    exif = Image.Exif()

    # Preserve existing EXIF tags if requested and available
    if metadata_mode == "preserve":
        try:
            source_exif = img.getexif()
            if source_exif:
                for k, v in source_exif.items():
                    exif[k] = v
        except Exception:
            pass

    # Apply scanner/device preset if specified
    if preset_name and preset_name in PRESETS:
        for k, v in PRESETS[preset_name].items():
            exif[k] = v

    # Ensure DPI / Resolution tags are present
    if dpi:
        x_res, y_res = float(dpi[0]), float(dpi[1])
        exif[282] = x_res  # XResolution
        exif[283] = y_res  # YResolution
        if 296 not in exif:
            exif[296] = 2  # ResolutionUnit (Inches)

    # Ensure DateTime tag is populated
    date_str = extract_datetime(img, file_path, strategy=date_strategy)
    exif[306] = date_str  # DateTime

    # Apply custom EXIF key-value overrides
    if custom_exif:
        for k, v in custom_exif.items():
            exif[k] = v

    return exif


def sync_file_mtime(file_path: Path, date_str: str) -> bool:
    """
    Set file modification time (mtime) to match EXIF date string (YYYY:MM:DD HH:MM:SS).
    """
    try:
        dt = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
        timestamp = dt.timestamp()
        os.utime(file_path, (timestamp, timestamp))
        return True
    except Exception:
        return False
