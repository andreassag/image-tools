import tempfile
from pathlib import Path
from PIL import Image
import pytest

from image_tools.cli import (
    main,
    inspect_main,
    resize_main,
    compress_main,
    orient_main,
    edit_exif_main,
    rename_main,
    watermark_main,
    pdf_main,
    parse_convert_args,
    parse_resize_args,
    parse_compress_args,
    parse_orient_args,
    parse_edit_exif_args,
    parse_rename_args,
    parse_watermark_args,
    parse_pdf_args
)


def test_parse_convert_args_defaults():
    args = parse_convert_args(["input.tif"])
    assert args.input_path == "input.tif"
    assert args.format == "JPEG"
    assert args.quality == 95
    assert args.pages == "all"
    assert args.no_preserve_metadata is False


def test_cli_main_dry_run():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        tif_file = tmp_path / "test.tif"
        img = Image.new("RGB", (50, 50))
        img.save(tif_file, "TIFF")

        exit_code = main([str(tif_file), "--dry-run", "-v"])
        assert exit_code == 0
        assert not (tmp_path / "test.jpg").exists()


def test_cli_inspect_main():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        jpg_file = tmp_path / "test.jpg"
        img = Image.new("RGB", (50, 50))
        exif = Image.Exif()
        exif[271] = "TestMake"
        img.save(jpg_file, "JPEG", exif=exif)

        exit_code = inspect_main([str(jpg_file)])
        assert exit_code == 0


def test_cli_resize_main_dry_run():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        jpg_file = tmp_path / "test.jpg"
        img = Image.new("RGB", (200, 100))
        img.save(jpg_file, "JPEG")

        exit_code = resize_main([str(jpg_file), "-w", "100", "--dry-run"])
        assert exit_code == 0


def test_cli_resize_missing_sizing_arg():
    exit_code = resize_main(["test.jpg"])
    assert exit_code == 1


def test_cli_compress_main_dry_run():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        jpg_file = tmp_path / "test.jpg"
        img = Image.new("RGB", (300, 300))
        img.save(jpg_file, "JPEG")

        exit_code = compress_main([str(jpg_file), "-t", "50KB", "--dry-run"])
        assert exit_code == 0


def test_cli_orient_main_dry_run():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        jpg_file = tmp_path / "test.jpg"
        img = Image.new("RGB", (300, 300))
        img.save(jpg_file, "JPEG")

        exit_code = orient_main([str(jpg_file), "--auto-rotate", "--dry-run"])
        assert exit_code == 0


def test_cli_orient_missing_transform_arg():
    exit_code = orient_main(["test.jpg"])
    assert exit_code == 1


def test_cli_edit_exif_main_dump():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        jpg_file = tmp_path / "test.jpg"
        json_file = tmp_path / "meta.json"
        img = Image.new("RGB", (50, 50))
        exif = Image.Exif()
        exif[271] = "TestMake"
        img.save(jpg_file, "JPEG", exif=exif)

        exit_code = edit_exif_main([str(jpg_file), "--dump-json", str(json_file)])
        assert exit_code == 0
        assert json_file.exists()


def test_cli_rename_main_dry_run():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        jpg_file = tmp_path / "test.jpg"
        img = Image.new("RGB", (50, 50))
        img.save(jpg_file, "JPEG")

        exit_code = rename_main([str(jpg_file), "--pattern", "{make}_{stem}.{ext}", "--dry-run"])
        assert exit_code == 0


def test_cli_watermark_main_dry_run():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        jpg_file = tmp_path / "test.jpg"
        img = Image.new("RGB", (100, 100))
        img.save(jpg_file, "JPEG")

        exit_code = watermark_main([str(jpg_file), "-t", "SAMPLE", "--dry-run"])
        assert exit_code == 0


def test_cli_watermark_missing_source():
    exit_code = watermark_main(["test.jpg"])
    assert exit_code == 1


def test_cli_pdf_main_build():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        jpg1 = tmp_path / "1.jpg"
        jpg2 = tmp_path / "2.jpg"
        out_pdf = tmp_path / "doc.pdf"

        Image.new("RGB", (50, 50)).save(jpg1, "JPEG")
        Image.new("RGB", (50, 50)).save(jpg2, "JPEG")

        exit_code = pdf_main(["build", str(jpg1), str(jpg2), "-o", str(out_pdf)])
        assert exit_code == 0
        assert out_pdf.exists()


def test_cli_pdf_main_contact():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        jpg1 = tmp_path / "1.jpg"
        out_sheet = tmp_path / "sheet.png"

        Image.new("RGB", (50, 50)).save(jpg1, "JPEG")

        exit_code = pdf_main(["contact", str(tmp_path), "-o", str(out_sheet)])
        assert exit_code == 0
        assert out_sheet.exists()
