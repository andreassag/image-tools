import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

from PIL import Image
from PIL.ExifTags import TAGS

from image_tools.common import find_image_files, add_common_batch_args, run_batch
from image_tools.converter import convert_image, ConversionResult
from image_tools.compressor import compress_image
from image_tools.metadata import PRESETS
from image_tools.metadata_editor import (
    set_exif_tags,
    export_exif_json,
    rename_image_by_metadata
)
from image_tools.pdf_tools import (
    create_pdf_from_images,
    extract_images_from_pdf,
    create_contact_sheet
)
from image_tools.resizer import resize_image, RESAMPLE_FILTERS
from image_tools.transformer import transform_image
from image_tools.watermark import apply_watermark


# --- image-convert CLI ---

def parse_convert_args(args: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="image-convert",
        description="Convert images with EXIF metadata preservation and customizable presets."
    )
    add_common_batch_args(parser)

    parser.add_argument(
        "-f", "--format",
        type=str,
        default="JPEG",
        choices=["JPEG", "JPG", "PNG", "WEBP", "TIFF"],
        help="Target output image format (default: JPEG)."
    )
    parser.add_argument(
        "-q", "--quality",
        type=int,
        default=95,
        help="Output image quality from 1 to 100 (default: 95)."
    )
    parser.add_argument(
        "--preset",
        type=str,
        choices=list(PRESETS.keys()),
        default=None,
        help="Apply a metadata preset (e.g. canon_lide_400, generic_scanner)."
    )
    parser.add_argument(
        "--no-preserve-metadata",
        action="store_true",
        help="Do not copy original EXIF metadata from source image."
    )
    parser.add_argument(
        "--date-source",
        type=str,
        choices=["auto", "exif", "filename", "mtime"],
        default="auto",
        help="Strategy for extracting date/time metadata (default: auto)."
    )
    parser.add_argument(
        "--pages",
        type=str,
        choices=["all", "first"],
        default="all",
        help="Multi-page TIFF handling: 'all' exports indexed files, 'first' exports page 1 only (default: all)."
    )
    parser.add_argument(
        "--touch-mtime",
        action="store_true",
        help="Update output file modification time (mtime) to match EXIF date."
    )

    meta_group = parser.add_argument_group("Custom EXIF Metadata Overrides")
    meta_group.add_argument("--make", type=str, help="Override EXIF Make tag (271).")
    meta_group.add_argument("--model", type=str, help="Override EXIF Model tag (272).")
    meta_group.add_argument("--software", type=str, help="Override EXIF Software tag (305).")

    return parser.parse_args(args)


def run_convert_task(kwargs: Dict[str, Any]) -> ConversionResult:
    return convert_image(**kwargs)


def main(sys_args: Optional[List[str]] = None) -> int:
    args = parse_convert_args(sys_args if sys_args is not None else sys.argv[1:])

    logging_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=logging_level, format="%(message)s")

    input_path = Path(args.input_path).resolve()
    image_files = find_image_files(input_path, recursive=args.recursive)

    if not image_files:
        print(f"No matching image files found at '{args.input_path}'.")
        return 1

    custom_exif: Dict[int, Any] = {}
    if args.make:
        custom_exif[271] = args.make
    if args.model:
        custom_exif[272] = args.model
    if args.software:
        custom_exif[305] = args.software

    metadata_mode = "strip" if args.no_preserve_metadata else "preserve"
    output_dir = Path(args.output_dir) if args.output_dir else None

    tasks = [
        {
            "input_path": file,
            "output_dir": output_dir,
            "format": args.format,
            "quality": args.quality,
            "metadata_mode": metadata_mode,
            "preset": args.preset,
            "date_strategy": args.date_source,
            "custom_exif": custom_exif,
            "pages": args.pages,
            "touch_mtime": args.touch_mtime,
            "dry_run": args.dry_run
        }
        for file in image_files
    ]

    succ, fail = run_batch(tasks, run_convert_task, jobs=args.jobs, dry_run=args.dry_run)
    return 0 if fail == 0 else 1


# --- image-resize CLI ---

def parse_resize_args(args: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="image-resize",
        description="Batch resize and scale images with aspect ratio control and EXIF metadata retention."
    )
    add_common_batch_args(parser)

    parser.add_argument(
        "-w", "--width",
        type=int,
        default=None,
        help="Target output width in pixels."
    )
    parser.add_argument(
        "-H", "--height",
        type=int,
        default=None,
        help="Target output height in pixels."
    )
    parser.add_argument(
        "-m", "--max-dim",
        type=int,
        default=None,
        help="Target maximum dimension (bounding box) in pixels."
    )
    parser.add_argument(
        "-s", "--scale",
        type=float,
        default=None,
        help="Percentage scale factor (e.g. 50 for 50%%)."
    )
    parser.add_argument(
        "--aspect-ratio",
        type=str,
        choices=["fit", "fill", "pad", "stretch"],
        default="fit",
        help="Aspect ratio behavior when both width & height are specified (default: fit)."
    )
    parser.add_argument(
        "--filter",
        type=str,
        choices=list(RESAMPLE_FILTERS.keys()),
        default="lanczos",
        help="Resampling filter method (default: lanczos)."
    )
    parser.add_argument(
        "-f", "--format",
        type=str,
        default=None,
        choices=["JPEG", "JPG", "PNG", "WEBP", "TIFF"],
        help="Target output format (default: same as input format)."
    )
    parser.add_argument(
        "-q", "--quality",
        type=int,
        default=95,
        help="Quality setting from 1 to 100 (default: 95)."
    )
    parser.add_argument(
        "--no-preserve-metadata",
        action="store_true",
        help="Do not copy EXIF metadata to resized output."
    )
    parser.add_argument(
        "--touch-mtime",
        action="store_true",
        help="Update output file modification time (mtime) to match EXIF date."
    )

    return parser.parse_args(args)


def run_resize_task(kwargs: Dict[str, Any]) -> ConversionResult:
    return resize_image(**kwargs)


def resize_main(sys_args: Optional[List[str]] = None) -> int:
    args = parse_resize_args(sys_args if sys_args is not None else sys.argv[1:])

    if args.width is None and args.height is None and args.max_dim is None and args.scale is None:
        print("Error: Must specify at least one sizing option: -w/--width, -H/--height, -m/--max-dim, or -s/--scale.")
        return 1

    logging_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=logging_level, format="%(message)s")

    input_path = Path(args.input_path).resolve()
    image_files = find_image_files(input_path, recursive=args.recursive)

    if not image_files:
        print(f"No matching image files found at '{args.input_path}'.")
        return 1

    metadata_mode = "strip" if args.no_preserve_metadata else "preserve"
    output_dir = Path(args.output_dir) if args.output_dir else None

    tasks = [
        {
            "input_path": file,
            "output_dir": output_dir,
            "width": args.width,
            "height": args.height,
            "max_dim": args.max_dim,
            "scale": args.scale,
            "aspect_ratio_mode": args.aspect_ratio,
            "resample_filter": args.filter,
            "format": args.format,
            "quality": args.quality,
            "metadata_mode": metadata_mode,
            "touch_mtime": args.touch_mtime,
            "dry_run": args.dry_run
        }
        for file in image_files
    ]

    succ, fail = run_batch(tasks, run_resize_task, jobs=args.jobs, dry_run=args.dry_run)
    return 0 if fail == 0 else 1


# --- image-compress CLI ---

def parse_compress_args(args: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="image-compress",
        description="Batch compress images to target quality or maximum file size."
    )
    add_common_batch_args(parser)

    parser.add_argument(
        "-t", "--target-size",
        type=str,
        default=None,
        help="Target maximum file size (e.g. '500KB', '2MB')."
    )
    parser.add_argument(
        "-q", "--quality",
        type=int,
        default=85,
        help="Target image quality from 1 to 100 (default: 85)."
    )
    parser.add_argument(
        "-f", "--format",
        type=str,
        default=None,
        choices=["JPEG", "JPG", "PNG", "WEBP", "TIFF"],
        help="Target output format (default: same as input format)."
    )
    parser.add_argument(
        "--strip-exif",
        action="store_true",
        help="Strip all EXIF metadata for maximum privacy and minimal size."
    )
    parser.add_argument(
        "--strip-gps",
        action="store_true",
        help="Strip GPS location tags while preserving camera and date tags."
    )
    parser.add_argument(
        "--touch-mtime",
        action="store_true",
        help="Update output file modification time (mtime) to match EXIF date."
    )

    return parser.parse_args(args)


def run_compress_task(kwargs: Dict[str, Any]) -> ConversionResult:
    return compress_image(**kwargs)


def compress_main(sys_args: Optional[List[str]] = None) -> int:
    args = parse_compress_args(sys_args if sys_args is not None else sys.argv[1:])

    logging_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=logging_level, format="%(message)s")

    input_path = Path(args.input_path).resolve()
    image_files = find_image_files(input_path, recursive=args.recursive)

    if not image_files:
        print(f"No matching image files found at '{args.input_path}'.")
        return 1

    output_dir = Path(args.output_dir) if args.output_dir else None

    tasks = [
        {
            "input_path": file,
            "output_dir": output_dir,
            "target_size": args.target_size,
            "quality": args.quality,
            "format": args.format,
            "strip_exif": args.strip_exif,
            "strip_gps": args.strip_gps,
            "touch_mtime": args.touch_mtime,
            "dry_run": args.dry_run
        }
        for file in image_files
    ]

    succ, fail = run_batch(tasks, run_compress_task, jobs=args.jobs, dry_run=args.dry_run)
    return 0 if fail == 0 else 1


# --- image-orient CLI ---

def parse_orient_args(args: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="image-orient",
        description="Spatial image transformation tool: EXIF auto-rotation, manual rotation, and flips."
    )
    add_common_batch_args(parser)

    parser.add_argument(
        "--auto-rotate",
        action="store_true",
        help="Automatically rotate image according to EXIF Orientation tag."
    )
    parser.add_argument(
        "--rotate",
        type=int,
        choices=[90, 180, 270],
        default=None,
        help="Rotate image clockwise by 90, 180, or 270 degrees."
    )
    parser.add_argument(
        "--flip-h",
        action="store_true",
        help="Flip image horizontally (left-right mirror)."
    )
    parser.add_argument(
        "--flip-v",
        action="store_true",
        help="Flip image vertically (top-bottom mirror)."
    )
    parser.add_argument(
        "-f", "--format",
        type=str,
        default=None,
        choices=["JPEG", "JPG", "PNG", "WEBP", "TIFF"],
        help="Target output format (default: same as input format)."
    )
    parser.add_argument(
        "-q", "--quality",
        type=int,
        default=95,
        help="Quality setting from 1 to 100 (default: 95)."
    )
    parser.add_argument(
        "--touch-mtime",
        action="store_true",
        help="Update output file modification time (mtime) to match EXIF date."
    )

    return parser.parse_args(args)


def run_orient_task(kwargs: Dict[str, Any]) -> ConversionResult:
    return transform_image(**kwargs)


def orient_main(sys_args: Optional[List[str]] = None) -> int:
    args = parse_orient_args(sys_args if sys_args is not None else sys.argv[1:])

    if not args.auto_rotate and args.rotate is None and not args.flip_h and not args.flip_v:
        print("Error: Must specify at least one transformation option: --auto-rotate, --rotate, --flip-h, or --flip-v.")
        return 1

    logging_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=logging_level, format="%(message)s")

    input_path = Path(args.input_path).resolve()
    image_files = find_image_files(input_path, recursive=args.recursive)

    if not image_files:
        print(f"No matching image files found at '{args.input_path}'.")
        return 1

    output_dir = Path(args.output_dir) if args.output_dir else None

    tasks = [
        {
            "input_path": file,
            "output_dir": output_dir,
            "auto_rotate": args.auto_rotate,
            "rotate": args.rotate,
            "flip_h": args.flip_h,
            "flip_v": args.flip_v,
            "format": args.format,
            "quality": args.quality,
            "touch_mtime": args.touch_mtime,
            "dry_run": args.dry_run
        }
        for file in image_files
    ]

    succ, fail = run_batch(tasks, run_orient_task, jobs=args.jobs, dry_run=args.dry_run)
    return 0 if fail == 0 else 1


# --- edit-exif CLI ---

def parse_edit_exif_args(args: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="edit-exif",
        description="Edit, dump, or restore EXIF metadata in image files."
    )
    add_common_batch_args(parser)

    parser.add_argument(
        "--set-tag",
        action="append",
        metavar="KEY=VALUE",
        help="Set EXIF tag key-value pair (e.g. Make=Canon, Artist='Jane Doe'). Can be specified multiple times."
    )
    parser.add_argument(
        "--delete-tag",
        action="append",
        metavar="KEY",
        help="Delete specific EXIF tag by name or ID. Can be specified multiple times."
    )
    parser.add_argument(
        "--dump-json",
        type=str,
        default=None,
        metavar="JSON_FILE",
        help="Export EXIF metadata of input image to a JSON file."
    )
    parser.add_argument(
        "--from-json",
        type=str,
        default=None,
        metavar="JSON_FILE",
        help="Import and apply EXIF metadata from a JSON file."
    )

    return parser.parse_args(args)


def run_edit_exif_task(kwargs: Dict[str, Any]) -> ConversionResult:
    return set_exif_tags(**kwargs)


def edit_exif_main(sys_args: Optional[List[str]] = None) -> int:
    args = parse_edit_exif_args(sys_args if sys_args is not None else sys.argv[1:])

    input_path = Path(args.input_path).resolve()

    if args.dump_json:
        if not input_path.is_file():
            print(f"Error: --dump-json requires a single input image file, got '{args.input_path}'.")
            return 1

        exif_dict = export_exif_json(input_path)
        out_json = Path(args.dump_json)
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(exif_dict, f, indent=2)
        print(f"Exported EXIF metadata from '{input_path.name}' to '{out_json}'.")
        return 0

    image_files = find_image_files(input_path, recursive=args.recursive)
    if not image_files:
        print(f"No matching image files found at '{args.input_path}'.")
        return 1

    set_tags: Dict[str, Any] = {}
    if args.from_json:
        json_path = Path(args.from_json)
        if not json_path.exists():
            print(f"Error: JSON file '{json_path}' not found.")
            return 1
        with open(json_path, "r", encoding="utf-8") as f:
            set_tags.update(json.load(f))

    if args.set_tag:
        for pair in args.set_tag:
            if "=" in pair:
                k, v = pair.split("=", 1)
                set_tags[k.strip()] = v.strip()

    if not set_tags and not args.delete_tag:
        print("Error: Must specify at least one metadata edit option: --set-tag, --delete-tag, --dump-json, or --from-json.")
        return 1

    output_dir = Path(args.output_dir) if args.output_dir else None

    tasks = [
        {
            "input_path": file,
            "output_dir": output_dir,
            "set_tags": set_tags if set_tags else None,
            "delete_tags": args.delete_tag,
            "dry_run": args.dry_run
        }
        for file in image_files
    ]

    succ, fail = run_batch(tasks, run_edit_exif_task, jobs=args.jobs, dry_run=args.dry_run)
    return 0 if fail == 0 else 1


# --- image-rename CLI ---

def parse_rename_args(args: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="image-rename",
        description="Batch rename images using metadata pattern templates."
    )
    add_common_batch_args(parser)

    parser.add_argument(
        "-p", "--pattern",
        type=str,
        default="{date}_{make}_{model}_{stem}.{ext}",
        help="Filename template pattern (placeholders: {date}, {make}, {model}, {software}, {stem}, {ext})."
    )

    return parser.parse_args(args)


def run_rename_task(kwargs: Dict[str, Any]) -> ConversionResult:
    return rename_image_by_metadata(**kwargs)


def rename_main(sys_args: Optional[List[str]] = None) -> int:
    args = parse_rename_args(sys_args if sys_args is not None else sys.argv[1:])

    input_path = Path(args.input_path).resolve()
    image_files = find_image_files(input_path, recursive=args.recursive)

    if not image_files:
        print(f"No matching image files found at '{args.input_path}'.")
        return 1

    output_dir = Path(args.output_dir) if args.output_dir else None

    tasks = [
        {
            "input_path": file,
            "pattern": args.pattern,
            "output_dir": output_dir,
            "dry_run": args.dry_run
        }
        for file in image_files
    ]

    succ, fail = run_batch(tasks, run_rename_task, jobs=args.jobs, dry_run=args.dry_run)
    return 0 if fail == 0 else 1


# --- image-watermark CLI ---

def parse_watermark_args(args: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="image-watermark",
        description="Batch apply text or image logo watermarks to images."
    )
    add_common_batch_args(parser)

    parser.add_argument(
        "-t", "--text",
        type=str,
        default=None,
        help="Watermark text string (supports {date}, {stem}, {filename} placeholders)."
    )
    parser.add_argument(
        "-l", "--image-logo",
        type=str,
        default=None,
        help="Path to watermark logo image file (PNG/JPEG)."
    )
    parser.add_argument(
        "-p", "--position",
        type=str,
        default="bottom-right",
        choices=[
            "top-left", "top-center", "top-right",
            "center-left", "center", "center-right",
            "bottom-left", "bottom-center", "bottom-right",
            "tiled"
        ],
        help="Watermark placement position (default: bottom-right)."
    )
    parser.add_argument(
        "--opacity",
        type=float,
        default=0.5,
        help="Watermark opacity transparency from 0.0 to 1.0 (default: 0.5)."
    )
    parser.add_argument(
        "--color",
        type=str,
        default="white",
        help="Watermark text color name or hex code (default: white)."
    )
    parser.add_argument(
        "--font-size",
        type=int,
        default=None,
        help="Watermark text font size in points."
    )
    parser.add_argument(
        "--font-path",
        type=str,
        default=None,
        help="Path to custom TrueType (.ttf) or OpenType (.otf) font file."
    )
    parser.add_argument(
        "--logo-scale",
        type=float,
        default=0.2,
        help="Image logo scale ratio relative to base image width (default: 0.2)."
    )
    parser.add_argument(
        "--margin",
        type=int,
        default=20,
        help="Margin padding offset in pixels from edge (default: 20)."
    )
    parser.add_argument(
        "-f", "--format",
        type=str,
        default=None,
        choices=["JPEG", "JPG", "PNG", "WEBP", "TIFF"],
        help="Target output format (default: same as input format)."
    )
    parser.add_argument(
        "-q", "--quality",
        type=int,
        default=95,
        help="Quality setting from 1 to 100 (default: 95)."
    )
    parser.add_argument(
        "--touch-mtime",
        action="store_true",
        help="Update output file modification time (mtime) to match EXIF date."
    )

    return parser.parse_args(args)


def run_watermark_task(kwargs: Dict[str, Any]) -> ConversionResult:
    return apply_watermark(**kwargs)


def watermark_main(sys_args: Optional[List[str]] = None) -> int:
    args = parse_watermark_args(sys_args if sys_args is not None else sys.argv[1:])

    if not args.text and not args.image_logo:
        print("Error: Must specify at least one watermark source: -t/--text or -l/--image-logo.")
        return 1

    logging_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=logging_level, format="%(message)s")

    input_path = Path(args.input_path).resolve()
    image_files = find_image_files(input_path, recursive=args.recursive)

    if not image_files:
        print(f"No matching image files found at '{args.input_path}'.")
        return 1

    output_dir = Path(args.output_dir) if args.output_dir else None
    logo_path = Path(args.image_logo) if args.image_logo else None
    font_p = Path(args.font_path) if args.font_path else None

    tasks = [
        {
            "input_path": file,
            "output_dir": output_dir,
            "text": args.text,
            "image_logo": logo_path,
            "position": args.position,
            "opacity": args.opacity,
            "color": args.color,
            "font_size": args.font_size,
            "font_path": font_p,
            "logo_scale": args.logo_scale,
            "margin": args.margin,
            "format": args.format,
            "quality": args.quality,
            "touch_mtime": args.touch_mtime,
            "dry_run": args.dry_run
        }
        for file in image_files
    ]

    succ, fail = run_batch(tasks, run_watermark_task, jobs=args.jobs, dry_run=args.dry_run)
    return 0 if fail == 0 else 1


# --- image-pdf CLI ---

def parse_pdf_args(args: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="image-pdf",
        description="PDF document assembly, image extraction, and contact sheet composite generator."
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="PDF task subcommand.")

    # Subcommand: build
    build_parser = subparsers.add_parser("build", help="Combine images into a multi-page PDF document.")
    build_parser.add_argument("inputs", nargs="+", help="Input image file paths.")
    build_parser.add_argument("-o", "--output", type=str, required=True, help="Output PDF file path.")
    build_parser.add_argument("--title", type=str, default=None, help="PDF document title.")
    build_parser.add_argument("--author", type=str, default=None, help="PDF document author.")
    build_parser.add_argument("--dry-run", action="store_true", help="Perform a dry run.")

    # Subcommand: extract
    extract_parser = subparsers.add_parser("extract", help="Unpack images from a PDF file.")
    extract_parser.add_argument("pdf_path", help="Path to input PDF file.")
    extract_parser.add_argument("-o", "--output-dir", type=str, default=".", help="Directory to save extracted images.")
    extract_parser.add_argument("-f", "--format", type=str, default="PNG", choices=["PNG", "JPEG", "JPG"], help="Export image format.")
    extract_parser.add_argument("--dry-run", action="store_true", help="Perform a dry run.")

    # Subcommand: contact
    contact_parser = subparsers.add_parser("contact", help="Generate thumbnail contact sheet composite.")
    contact_parser.add_argument("input_path", help="Path to image file or directory.")
    contact_parser.add_argument("-o", "--output", type=str, required=True, help="Output contact sheet image file path.")
    contact_parser.add_argument("--cols", type=int, default=4, help="Number of columns in grid (default: 4).")
    contact_parser.add_argument("--rows", type=int, default=4, help="Number of rows in grid (default: 4).")
    contact_parser.add_argument("-r", "--recursive", action="store_true", help="Recursively search subdirectories.")
    contact_parser.add_argument("--no-annotate", action="store_true", help="Do not draw filename labels under thumbnails.")
    contact_parser.add_argument("--dry-run", action="store_true", help="Perform a dry run.")

    return parser.parse_args(args)


def pdf_main(sys_args: Optional[List[str]] = None) -> int:
    args = parse_pdf_args(sys_args if sys_args is not None else sys.argv[1:])

    if not args.subcommand:
        print("Error: Must specify a subcommand: 'build', 'extract', or 'contact'.")
        return 1

    if args.subcommand == "build":
        image_paths = [Path(p) for p in args.inputs]
        res = create_pdf_from_images(
            image_paths=image_paths,
            output_path=Path(args.output),
            title=args.title,
            author=args.author,
            dry_run=args.dry_run
        )
        if res.success:
            print(f"Created PDF document with {res.frames_processed} page(s) -> '{res.output_paths[0]}'.")
            return 0
        else:
            print(f"Error creating PDF: {res.error_message}")
            return 1

    elif args.subcommand == "extract":
        res = extract_images_from_pdf(
            pdf_path=Path(args.pdf_path),
            output_dir=Path(args.output_dir),
            format=args.format,
            dry_run=args.dry_run
        )
        if res.success:
            print(f"Extracted {res.frames_processed} image(s) from '{args.pdf_path}'.")
            return 0
        else:
            print(f"Error extracting PDF: {res.error_message}")
            return 1

    elif args.subcommand == "contact":
        input_p = Path(args.input_path).resolve()
        image_files = find_image_files(input_p, recursive=args.recursive)
        if not image_files:
            print(f"No matching image files found at '{args.input_path}'.")
            return 1

        res = create_contact_sheet(
            image_paths=image_files,
            output_path=Path(args.output),
            cols=args.cols,
            rows=args.rows,
            annotate=not args.no_annotate,
            dry_run=args.dry_run
        )
        if res.success:
            print(f"Generated contact sheet composite ({res.frames_processed} thumbnails) -> '{res.output_paths[0]}'.")
            return 0
        else:
            print(f"Error creating contact sheet: {res.error_message}")
            return 1

    return 0


# --- inspect-exif CLI ---

def inspect_main(sys_args: Optional[List[str]] = None) -> int:
    """CLI utility for inspecting EXIF tags in images."""
    parser = argparse.ArgumentParser(
        prog="inspect-exif",
        description="Inspect EXIF metadata of an image file."
    )
    parser.add_argument("image_path", help="Path to image file.")
    args = parser.parse_args(sys_args if sys_args is not None else sys.argv[1:])

    path = Path(args.image_path)
    if not path.exists():
        print(f"Error: File '{path}' not found.")
        return 1

    try:
        image = Image.open(path)
        exif_data = image.getexif()

        if not exif_data:
            print(f"No EXIF metadata found in '{path}'.")
            return 0

        print(f"\n--- EXIF Metadata for: {path} ---")
        for tag_id, value in exif_data.items():
            tag_name = TAGS.get(tag_id, f"Unknown ({tag_id})")
            if isinstance(value, bytes):
                try:
                    value = value.decode("utf-8", errors="ignore").strip()
                except Exception:
                    value = str(value)
            print(f"{tag_id:<6} {tag_name:<25}: {value}")

    except Exception as e:
        print(f"Error reading EXIF from '{path}': {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
