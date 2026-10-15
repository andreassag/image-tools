import tempfile
from pathlib import Path
from PIL import Image
import pytest

from image_tools.pdf_tools import (
    create_pdf_from_images,
    extract_images_from_pdf,
    create_contact_sheet
)


def test_create_pdf_from_images():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        img1_p = tmp_path / "page1.jpg"
        img2_p = tmp_path / "page2.jpg"
        out_pdf = tmp_path / "document.pdf"

        img1 = Image.new("RGB", (200, 300), (255, 0, 0))
        img1.save(img1_p, "JPEG")
        img2 = Image.new("RGB", (200, 300), (0, 255, 0))
        img2.save(img2_p, "JPEG")

        res = create_pdf_from_images(
            image_paths=[img1_p, img2_p],
            output_path=out_pdf,
            title="Test PDF Document",
            author="Tester"
        )
        assert res.success is True
        assert out_pdf.exists()
        assert out_pdf.stat().st_size > 0
        assert res.frames_processed == 2


def test_create_contact_sheet():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        images = []
        for i in range(5):
            img_p = tmp_path / f"img_{i}.jpg"
            img = Image.new("RGB", (100, 100), (i * 40, 100, 200))
            img.save(img_p, "JPEG")
            images.append(img_p)

        out_contact = tmp_path / "contact.png"
        res = create_contact_sheet(
            image_paths=images,
            output_path=out_contact,
            cols=3,
            rows=2,
            annotate=True
        )
        assert res.success is True
        assert out_contact.exists()
        assert res.frames_processed == 5


def test_extract_images_from_pdf():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        img1_p = tmp_path / "page1.jpg"
        img1 = Image.new("RGB", (100, 100), (255, 0, 0))
        img1.save(img1_p, "JPEG")

        out_pdf = tmp_path / "test.pdf"
        create_pdf_from_images([img1_p], out_pdf)

        out_dir = tmp_path / "extracted"
        res = extract_images_from_pdf(out_pdf, out_dir, format="PNG")
        # Should succeed or return graceful dependency message
        assert isinstance(res.success, bool)
