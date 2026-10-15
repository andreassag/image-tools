import tempfile
from pathlib import Path
from PIL import Image
import pytest

from image_tools.metadata import extract_datetime, build_exif, PRESETS


def test_extract_datetime_filename_regex():
    path = Path("/tmp/scan_2023-11-25_143000.tif")
    img = Image.new("RGB", (10, 10))
    date_str = extract_datetime(img, path, strategy="filename")
    assert date_str == "2023:11:25 14:30:00"


def test_build_exif_preset():
    path = Path("/tmp/scan.tif")
    img = Image.new("RGB", (10, 10))
    exif = build_exif(img, path, preset_name="canon_lide_400", dpi=(600, 600))

    assert exif[271] == "Canon"
    assert exif[272] == "CanoScan LiDE 400"
    assert exif[305] == "IJ Scan Utility"
    assert exif[282] == 600.0
    assert exif[283] == 600.0


def test_build_exif_custom_override():
    path = Path("/tmp/scan.tif")
    img = Image.new("RGB", (10, 10))
    custom = {271: "CustomMake", 272: "CustomModel"}
    exif = build_exif(img, path, custom_exif=custom)

    assert exif[271] == "CustomMake"
    assert exif[272] == "CustomModel"
