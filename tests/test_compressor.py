import tempfile
import random
from pathlib import Path
from PIL import Image
import pytest

from image_tools.compressor import parse_size_bytes, sanitize_exif, compress_image


def test_parse_size_bytes():
    assert parse_size_bytes("500KB") == 500 * 1024
    assert parse_size_bytes("2MB") == 2 * 1024 * 1024
    assert parse_size_bytes("1.5M") == int(1.5 * 1024 * 1024)
    assert parse_size_bytes("1024") == 1024
    assert parse_size_bytes("500b") == 500

    with pytest.raises(ValueError):
        parse_size_bytes("invalid_size")

    with pytest.raises(ValueError):
        parse_size_bytes("500XYZ")


def test_sanitize_exif():
    exif = Image.Exif()
    exif[271] = "CameraMake"  # Make
    exif[34853] = 12345       # GPSInfo tag

    # Strip all EXIF
    stripped = sanitize_exif(exif, strip_exif=True)
    assert len(stripped) == 0

    # Strip GPS only
    gps_stripped = sanitize_exif(exif, strip_gps=True)
    assert 271 in gps_stripped
    assert 34853 not in gps_stripped


def test_compress_image_quality():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        input_jpg = tmp_path / "sample.jpg"
        out_dir = tmp_path / "output"

        # Create noisy image so compression quality makes a measurable size difference
        img = Image.new("RGB", (300, 300))
        pixels = [(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)) for _ in range(300 * 300)]
        img.putdata(pixels)
        img.save(input_jpg, "JPEG", quality=95)
        input_size = input_jpg.stat().st_size

        res = compress_image(
            input_path=input_jpg,
            output_dir=out_dir,
            quality=40,
            format="JPEG"
        )
        assert res.success is True
        assert len(res.output_paths) == 1
        out_path = res.output_paths[0]
        assert out_path.exists()
        assert out_path.stat().st_size < input_size


def test_compress_image_target_size():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        input_jpg = tmp_path / "sample.jpg"
        out_dir = tmp_path / "output"

        img = Image.new("RGB", (800, 800), (255, 100, 50))
        img.save(input_jpg, "JPEG", quality=95)

        target_str = "40KB"
        target_bytes = parse_size_bytes(target_str)

        res = compress_image(
            input_path=input_jpg,
            output_dir=out_dir,
            target_size=target_str,
            format="JPEG"
        )
        assert res.success is True
        out_path = res.output_paths[0]
        assert out_path.exists()
        assert out_path.stat().st_size <= target_bytes + 2048  # Within acceptable margin
