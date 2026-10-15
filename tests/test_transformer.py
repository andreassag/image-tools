import tempfile
from pathlib import Path
from PIL import Image
import pytest

from image_tools.transformer import transform_image


def test_transform_image_rotate_90():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        input_jpg = tmp_path / "sample.jpg"
        out_dir = tmp_path / "output"

        img = Image.new("RGB", (200, 100), (255, 0, 0))
        img.save(input_jpg, "JPEG")

        res = transform_image(
            input_path=input_jpg,
            output_dir=out_dir,
            rotate=90,
            format="JPEG"
        )
        assert res.success is True
        assert len(res.output_paths) == 1
        out_path = res.output_paths[0]
        assert out_path.exists()

        with Image.open(out_path) as out_img:
            assert out_img.size == (100, 200)


def test_transform_image_rotate_180_and_270():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        input_jpg = tmp_path / "sample.jpg"
        out_dir = tmp_path / "output"

        img = Image.new("RGB", (200, 100), (255, 0, 0))
        img.save(input_jpg, "JPEG")

        res180 = transform_image(
            input_path=input_jpg,
            output_dir=out_dir,
            rotate=180,
            format="JPEG"
        )
        assert res180.success is True
        with Image.open(res180.output_paths[0]) as out_img:
            assert out_img.size == (200, 100)

        res270 = transform_image(
            input_path=input_jpg,
            output_dir=out_dir,
            rotate=270,
            format="JPEG"
        )
        assert res270.success is True
        with Image.open(res270.output_paths[0]) as out_img:
            assert out_img.size == (100, 200)


def test_transform_image_flips():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        input_jpg = tmp_path / "sample.jpg"
        out_dir = tmp_path / "output"

        img = Image.new("RGB", (100, 100), (0, 255, 0))
        img.save(input_jpg, "JPEG")

        res = transform_image(
            input_path=input_jpg,
            output_dir=out_dir,
            flip_h=True,
            flip_v=True,
            format="JPEG"
        )
        assert res.success is True
        out_path = res.output_paths[0]
        assert out_path.exists()


def test_transform_image_auto_rotate():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        input_jpg = tmp_path / "sample.jpg"
        out_dir = tmp_path / "output"

        img = Image.new("RGB", (200, 100), (0, 0, 255))
        exif = Image.Exif()
        exif[274] = 6
        img.save(input_jpg, "JPEG", exif=exif)

        res = transform_image(
            input_path=input_jpg,
            output_dir=out_dir,
            auto_rotate=True,
            format="JPEG"
        )
        assert res.success is True
        out_path = res.output_paths[0]
        assert out_path.exists()

        with Image.open(out_path) as out_img:
            assert out_img.size == (100, 200)
            out_exif = out_img.getexif()
            assert out_exif.get(274) == 1
