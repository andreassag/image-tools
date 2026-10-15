import tempfile
from pathlib import Path
from PIL import Image
import pytest

from image_tools.watermark import (
    parse_color_rgba,
    calculate_position,
    apply_watermark
)


def test_parse_color_rgba():
    rgba = parse_color_rgba("white", opacity=0.5)
    assert rgba == (255, 255, 255, 127)

    rgba_hex = parse_color_rgba("#FF0000", opacity=1.0)
    assert rgba_hex == (255, 0, 0, 255)


def test_calculate_position():
    pos_top_left = calculate_position(1000, 1000, 100, 50, position="top-left", margin=20)
    assert pos_top_left == (20, 20)

    pos_center = calculate_position(1000, 1000, 100, 50, position="center", margin=20)
    assert pos_center == (450, 475)

    pos_bottom_right = calculate_position(1000, 1000, 100, 50, position="bottom-right", margin=20)
    assert pos_bottom_right == (880, 930)


def test_apply_watermark_text():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        input_jpg = tmp_path / "sample.jpg"
        out_dir = tmp_path / "output"

        img = Image.new("RGB", (400, 400), (0, 0, 0))
        img.save(input_jpg, "JPEG")

        res = apply_watermark(
            input_path=input_jpg,
            output_dir=out_dir,
            text="CONFIDENTIAL",
            position="center",
            opacity=0.8,
            color="red",
            format="JPEG"
        )
        assert res.success is True
        assert len(res.output_paths) == 1
        out_file = res.output_paths[0]
        assert out_file.exists()


def test_apply_watermark_logo():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        input_jpg = tmp_path / "sample.jpg"
        logo_png = tmp_path / "logo.png"
        out_dir = tmp_path / "output"

        base = Image.new("RGB", (500, 500), (200, 200, 200))
        base.save(input_jpg, "JPEG")

        logo = Image.new("RGBA", (100, 50), (255, 0, 0, 255))
        logo.save(logo_png, "PNG")

        res = apply_watermark(
            input_path=input_jpg,
            output_dir=out_dir,
            image_logo=logo_png,
            position="bottom-right",
            opacity=0.6,
            format="JPEG"
        )
        assert res.success is True
        out_file = res.output_paths[0]
        assert out_file.exists()


def test_apply_watermark_tiled():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        input_jpg = tmp_path / "sample.jpg"
        out_dir = tmp_path / "output"

        img = Image.new("RGB", (300, 300), (50, 50, 50))
        img.save(input_jpg, "JPEG")

        res = apply_watermark(
            input_path=input_jpg,
            output_dir=out_dir,
            text="DRAFT",
            position="tiled",
            opacity=0.3,
            format="JPEG"
        )
        assert res.success is True
        out_file = res.output_paths[0]
        assert out_file.exists()
