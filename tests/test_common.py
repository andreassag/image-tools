import tempfile
from pathlib import Path
from PIL import Image
import pytest

from image_tools.common import (
    resolve_target_format_and_ext,
    save_processed_image,
    find_image_files,
    run_batch
)
from image_tools.converter import ConversionResult


def _module_level_worker(kw):
    """Module-level worker function so it can be pickled by ProcessPoolExecutor."""
    if kw.get("fail"):
        raise RuntimeError("Deliberate failure")
    return ConversionResult(
        input_path=Path(kw["name"]),
        output_paths=[Path(kw["name"])],
        success=True
    )


def test_resolve_target_format_and_ext():
    fmt, ext = resolve_target_format_and_ext("jpeg", Path("photo.png"))
    assert fmt == "JPEG"
    assert ext == ".jpg"

    fmt, ext = resolve_target_format_and_ext("PNG", Path("photo.jpg"))
    assert fmt == "PNG"
    assert ext == ".png"

    fmt, ext = resolve_target_format_and_ext(None, Path("photo.webp"))
    assert fmt == "WEBP"
    assert ext == ".webp"

    fmt, ext = resolve_target_format_and_ext("UNKNOWN_FMT", Path("photo.xyz"))
    assert fmt == "JPEG"
    assert ext == ".jpg"


def test_save_processed_image():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        out_jpg = tmp_path / "saved.jpg"

        img = Image.new("RGB", (60, 60), (200, 100, 50))
        exif = Image.Exif()
        exif[271] = "CommonSaveMake"

        save_processed_image(
            img=img,
            out_path=out_jpg,
            target_format="JPEG",
            quality=85,
            exif=exif,
            dpi=(150.0, 150.0)
        )

        assert out_jpg.exists()
        with Image.open(out_jpg) as opened:
            assert opened.size == (60, 60)
            opened_exif = opened.getexif()
            assert opened_exif.get(271) == "CommonSaveMake"


def test_find_image_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        (tmp_path / "img1.JPG").touch()
        (tmp_path / "img2.png").touch()
        (tmp_path / "doc.txt").touch()

        subdir = tmp_path / "sub"
        subdir.mkdir()
        (subdir / "img3.webp").touch()

        # Non-recursive
        files_flat = find_image_files(tmp_path, recursive=False)
        assert len(files_flat) == 2

        # Recursive
        files_rec = find_image_files(tmp_path, recursive=True)
        assert len(files_rec) == 3


def test_run_batch_resilience_on_worker_error():
    tasks = [
        {"name": "file1.jpg", "fail": False},
        {"name": "file2.jpg", "fail": True},
        {"name": "file3.jpg", "fail": False},
    ]

    # Test sequential
    succ, fail = run_batch(tasks, _module_level_worker, jobs=1)
    assert succ == 2
    assert fail == 1

    # Test parallel (ProcessPool)
    succ_p, fail_p = run_batch(tasks, _module_level_worker, jobs=2)
    assert succ_p == 2
    assert fail_p == 1
