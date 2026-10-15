import tempfile
from pathlib import Path
from PIL import Image
import pytest

from image_tools.resizer import calculate_target_dimensions, resize_image


def test_calculate_target_dimensions_scale():
    w, h = calculate_target_dimensions(orig_w=200, orig_h=100, scale=50.0)
    assert (w, h) == (100, 50)


def test_calculate_target_dimensions_max_dim():
    w, h = calculate_target_dimensions(orig_w=400, orig_h=200, max_dim=100)
    assert (w, h) == (100, 50)

    w, h = calculate_target_dimensions(orig_w=150, orig_h=300, max_dim=100)
    assert (w, h) == (50, 100)


def test_calculate_target_dimensions_explicit_width_only():
    w, h = calculate_target_dimensions(orig_w=200, orig_h=100, width=100)
    assert (w, h) == (100, 50)


def test_calculate_target_dimensions_aspect_ratio_modes():
    # Fit inside 100x100 box
    w, h = calculate_target_dimensions(orig_w=200, orig_h=100, width=100, height=100, aspect_ratio_mode="fit")
    assert (w, h) == (100, 50)

    # Stretch to 100x100 box
    w, h = calculate_target_dimensions(orig_w=200, orig_h=100, width=100, height=100, aspect_ratio_mode="stretch")
    assert (w, h) == (100, 100)

    # Fill 100x100 box
    w, h = calculate_target_dimensions(orig_w=200, orig_h=100, width=100, height=100, aspect_ratio_mode="fill")
    assert (w, h) == (200, 100)


def test_resize_image_file_execution():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        input_jpg = tmp_path / "sample.jpg"
        img = Image.new("RGB", (400, 200), (0, 0, 255))
        exif = Image.Exif()
        exif[271] = "TestCamera"
        img.save(input_jpg, "JPEG", exif=exif)

        res = resize_image(
            input_path=input_jpg,
            output_dir=tmp_path,
            width=200,
            format="JPEG",
            quality=90
        )
        assert res.success is True
        assert len(res.output_paths) == 1
        out_file = res.output_paths[0]
        assert out_file.exists()

        with Image.open(out_file) as out_img:
            assert out_img.size == (200, 100)
            out_exif = out_img.getexif()
            assert out_exif.get(271) == "TestCamera"


def test_resize_image_pad_mode():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        input_jpg = tmp_path / "sample.jpg"
        img = Image.new("RGB", (200, 100), (255, 0, 0))
        img.save(input_jpg, "JPEG")

        res = resize_image(
            input_path=input_jpg,
            output_dir=tmp_path,
            width=100,
            height=100,
            aspect_ratio_mode="pad",
            format="JPEG"
        )
        assert res.success is True
        out_file = res.output_paths[0]
        with Image.open(out_file) as out_img:
            assert out_img.size == (100, 100)
