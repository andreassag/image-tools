import tempfile
from pathlib import Path
from PIL import Image, ImageCms
import pytest

from image_tools.converter import convert_image, prepare_image_for_export


def create_sample_tiff(path: Path, mode: str = "RGB", size=(100, 100), color=(255, 0, 0)):
    img = Image.new(mode, size, color)
    img.save(path, "TIFF", dpi=(300.0, 300.0))


def create_multipage_tiff(path: Path):
    img1 = Image.new("RGB", (100, 100), (255, 0, 0))
    img2 = Image.new("RGB", (100, 100), (0, 255, 0))
    img1.save(path, "TIFF", save_all=True, append_images=[img2], dpi=(300.0, 300.0))


def test_prepare_image_rgba_to_jpeg():
    rgba_img = Image.new("RGBA", (50, 50), (255, 0, 0, 128))
    prepared = prepare_image_for_export(rgba_img, "JPEG")
    assert prepared.mode == "RGB"


def test_convert_single_page_tiff():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        input_tiff = tmp_path / "sample.tif"
        create_sample_tiff(input_tiff)

        res = convert_image(input_tiff, output_dir=tmp_path, format="JPEG", quality=90)
        assert res.success is True
        assert len(res.output_paths) == 1
        assert res.output_paths[0].name == "sample.jpg"
        assert res.output_paths[0].exists()

        with Image.open(res.output_paths[0]) as out_img:
            assert out_img.format == "JPEG"


def test_convert_multipage_tiff():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        input_tiff = tmp_path / "multipage.tif"
        create_multipage_tiff(input_tiff)

        res = convert_image(input_tiff, output_dir=tmp_path, format="JPEG", pages="all")
        assert res.success is True
        assert len(res.output_paths) == 2
        assert res.output_paths[0].name == "multipage_p1.jpg"
        assert res.output_paths[1].name == "multipage_p2.jpg"
        assert res.output_paths[0].exists()
        assert res.output_paths[1].exists()


def test_convert_preserves_icc_profile():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        input_jpg = tmp_path / "with_profile.jpg"

        srgb_profile = ImageCms.createProfile("sRGB")
        icc_bytes = ImageCms.ImageCmsProfile(srgb_profile).tobytes()

        img = Image.new("RGB", (50, 50), (100, 150, 200))
        img.save(input_jpg, "JPEG", icc_profile=icc_bytes)

        res = convert_image(input_jpg, output_dir=tmp_path, format="PNG")
        assert res.success is True
        out_png = res.output_paths[0]
        assert out_png.exists()

        with Image.open(out_png) as out_img:
            assert "icc_profile" in out_img.info
            assert len(out_img.info["icc_profile"]) > 0
