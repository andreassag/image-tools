import tempfile
import json
from pathlib import Path
from PIL import Image
import pytest

from image_tools.metadata_editor import (
    parse_tag_key,
    parse_tag_value,
    sanitize_filename_component,
    export_exif_json,
    set_exif_tags,
    rename_image_by_metadata
)


def test_parse_tag_key():
    assert parse_tag_key("Make") == 271
    assert parse_tag_key("271") == 271
    assert parse_tag_key("Model") == 272

    with pytest.raises(ValueError):
        parse_tag_key("NonExistentTagNameXYZ")


def test_parse_tag_value():
    assert parse_tag_value("1") == 1
    assert parse_tag_value("274") == 274
    assert parse_tag_value("-10") == -10
    assert parse_tag_value("300.5") == 300.5
    assert parse_tag_value("Canon") == "Canon"
    assert parse_tag_value(123) == 123


def test_sanitize_filename_component():
    assert sanitize_filename_component("Canon EOS / 5D") == "Canon_EOS_5D"
    assert sanitize_filename_component("  foo  ") == "foo"
    assert sanitize_filename_component("CON") == "CON_file"
    assert sanitize_filename_component("") == "unknown"


def test_set_exif_tags_and_export_json():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        input_jpg = tmp_path / "sample.jpg"

        img = Image.new("RGB", (100, 100), (255, 0, 0))
        img.save(input_jpg, "JPEG")

        res = set_exif_tags(
            input_path=input_jpg,
            set_tags={"Make": "Canon", "Model": "TestLiDE", "Orientation": "1"}
        )
        assert res.success is True

        exif_dict = export_exif_json(input_jpg)
        assert exif_dict.get("Make") == "Canon"
        assert exif_dict.get("Model") == "TestLiDE"
        assert exif_dict.get("Orientation") == 1


def test_rename_image_by_metadata():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        input_jpg = tmp_path / "photo.jpg"

        img = Image.new("RGB", (100, 100), (0, 255, 0))
        exif = Image.Exif()
        exif[271] = "Epson"
        exif[272] = "V600"
        img.save(input_jpg, "JPEG", exif=exif)

        res = rename_image_by_metadata(
            input_path=input_jpg,
            pattern="{make}_{model}_{stem}.{ext}"
        )
        assert res.success is True
        out_file = res.output_paths[0]
        assert out_file.name == "Epson_V600_photo.jpg"
        assert out_file.exists()


def test_rename_image_collision_resolution():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Existing target files
        (tmp_path / "Target.jpg").touch()
        (tmp_path / "Target_1.jpg").touch()

        # Input to rename that would collide
        new_input = tmp_path / "photo.jpg"
        img = Image.new("RGB", (50, 50))
        img.save(new_input, "JPEG")

        res = rename_image_by_metadata(
            input_path=new_input,
            pattern="Target.{ext}"
        )
        assert res.success is True
        assert res.output_paths[0].name == "Target_2.jpg"
        assert (tmp_path / "Target_2.jpg").exists()
