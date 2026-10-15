# image-tools

[![CI](https://github.com/andreassag/image-tools/actions/workflows/ci.yml/badge.svg)](https://github.com/andreassag/image-tools/actions/workflows/ci.yml)
![Python Version](https://img.shields.io/badge/python-%3E%3D3.12-blue)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A high-performance Python package and CLI suite for image format conversion, batch resizing, intelligent compression, EXIF auto-rotation & spatial transformation, EXIF metadata editing & JSON export/import, metadata-driven file renaming, batch text & image logo watermarking, PDF document assembly & extraction, grid contact sheet generation, device presets, and parallel batch processing.

---

## Key Features

- **EXIF Metadata Preservation & Privacy**: Preserves original EXIF & TIFF metadata tags by default across conversion and resizing, or sanitize sensitive tags (`--strip-gps`, `--strip-exif`).
- **Batch Image Resizing**: `image-resize` tool with aspect ratio modes (`fit`, `fill`, `pad`, `stretch`), max bounding box scaling (`--max-dim`), percentage scaling (`--scale`), and high-quality resampling filters (`lanczos`, `bicubic`, etc.).
- **Smart Image Compression**: `image-compress` tool targeting specific file sizes (e.g. `--target-size 500KB`), custom quality levels, and metadata sanitization.
- **Spatial Transformations & Auto-Rotation**: `image-orient` tool for EXIF Orientation auto-rotation (`--auto-rotate`), manual rotation (90°, 180°, 270°), and horizontal/vertical mirroring (`--flip-h`, `--flip-v`).
- **EXIF Metadata Editing & JSON Dump/Apply**: `edit-exif` tool to set/delete specific tags, export metadata to JSON, or import/apply EXIF settings from JSON files.
- **Metadata-Driven Renaming**: `image-rename` tool to batch rename images based on metadata patterns (e.g. `{date}_{make}_{model}_{stem}.{ext}`).
- **Batch Watermarking & Branding**: `image-watermark` tool for text and image logo overlays with 9-point grid alignment, tiled pattern mode, opacity, and EXIF retention.
- **PDF & Multi-Page Tools**: `image-pdf` tool for combining image sets into multi-page PDF documents (`build`), extracting embedded image streams (`extract`), and rendering thumbnail contact sheets (`contact`).
- **Device Presets**: Apply pre-configured metadata profiles (e.g. `canon_lide_400`, `generic_scanner`) or custom Make/Model/Software overrides.
- **Multi-page TIFF Support**: Unpacks multi-page TIFFs into indexed files (`image_p1.jpg`, `image_p2.jpg`) or single-page exports.
- **Multi-Format Export**: Convert/resize to `JPEG`, `PNG`, `WEBP`, `TIFF` with custom quality settings.
- **Parallel Processing**: Speed up batch operations using multi-core worker processes (`-j / --jobs`).
- **EXIF Inspector**: Built-in `inspect-exif` tool to view EXIF tags on any image file.

---

## Installation & Setup

Using `uv` (recommended):
```bash
uv sync
```

With optional PDF dependencies:
```bash
uv sync --extra pdf
```

Or install in editable mode:
```bash
pip install -e .
```

---

## CLI Usage

### Format Conversion (`image-convert`)

Convert a single file or directory to JPEG:
```bash
# Convert a single file
uv run image-convert scan.tif

# Convert all images in a directory
uv run image-convert /path/to/scans/
```

Save output to a specific folder in WebP or PNG format:
```bash
uv run image-convert /path/to/scans/ -o /path/to/output/ -f WEBP -q 90
```

Recursively convert all images using 8 worker processes:
```bash
uv run image-convert /path/to/scans/ -r -j 8 -o /path/to/output/
```

Apply metadata presets or custom overrides:
```bash
# Apply Canon LiDE 400 preset
uv run image-convert scan.tif --preset canon_lide_400

# Custom metadata override
uv run image-convert scan.tif --make "Epson" --model "V600" --software "Epson Scan 2"
```

Sync output file modification time (`mtime`) to EXIF timestamp:
```bash
uv run image-convert scan.tif --touch-mtime
```

---

### Batch Resizing (`image-resize`)

Scale by max bounding box (e.g., maximum width/height 1200px):
```bash
uv run image-resize /path/to/photos/ -m 1200 -o /path/to/resized/
```

Scale by specific width and height with `pad` mode (centered with canvas padding):
```bash
uv run image-resize photo.jpg -w 1920 -H 1080 --aspect-ratio pad -o /path/to/output/
```

Scale by percentage (e.g., 50% scale):
```bash
uv run image-resize /path/to/photos/ -s 50
```

---

### Intelligent Compression (`image-compress`)

Compress images to a target file size (e.g. maximum 500KB):
```bash
uv run image-compress /path/to/photos/ -t 500KB -o /path/to/compressed/
```

Compress images with explicit quality setting and GPS metadata stripping for privacy:
```bash
uv run image-compress photo.jpg -q 75 --strip-gps
```

Strip all EXIF metadata for minimal file size and web export:
```bash
uv run image-compress /path/to/photos/ --strip-exif -f WEBP
```

---

### Spatial Transformations & Auto-Rotation (`image-orient`)

Automatically rotate camera/phone portrait photos based on EXIF tag 274:
```bash
uv run image-orient /path/to/photos/ --auto-rotate -o /path/to/rotated/
```

Rotate images by 90 degrees clockwise and flip horizontally:
```bash
uv run image-orient photo.jpg --rotate 90 --flip-h
```

---

### Metadata Editing & JSON Export (`edit-exif`)

Set or delete EXIF tags:
```bash
uv run edit-exif photo.jpg --set-tag Make="Canon" --set-tag Artist="Jane Doe" --delete-tag Software
```

Export image EXIF metadata to a JSON file:
```bash
uv run edit-exif photo.jpg --dump-json metadata.json
```

Import and apply EXIF metadata from a JSON file:
```bash
uv run edit-exif photo.jpg --from-json metadata.json
```

---

### Metadata-Driven File Renaming (`image-rename`)

Batch rename files using EXIF date, camera make, model, and original filename patterns:
```bash
uv run image-rename /path/to/photos/ --pattern "{date}_{make}_{model}_{stem}.{ext}"
```

---

### Batch Watermarking & Branding (`image-watermark`)

Apply a text watermark to photos with semi-transparent placement:
```bash
uv run image-watermark /path/to/photos/ -t "CONFIDENTIAL" -p center --opacity 0.6 --color white
```

Apply an image logo watermark aligned to the bottom-right corner:
```bash
uv run image-watermark photo.jpg -l logo.png -p bottom-right --logo-scale 0.2
```

Apply a tiled text pattern across the image:
```bash
uv run image-watermark /path/to/photos/ -t "DRAFT {date}" -p tiled --opacity 0.3
```

---

### PDF & Multi-Page Document Tools (`image-pdf`)

Combine images into a multi-page PDF document:
```bash
uv run image-pdf build page1.jpg page2.png -o document.pdf --title "Report"
```

Extract images from a PDF file:
```bash
uv run image-pdf extract document.pdf -o /path/to/extracted/ -f PNG
```

Generate a thumbnail contact sheet grid:
```bash
uv run image-pdf contact /path/to/photos/ -o contact_sheet.png --cols 4 --rows 4
```

---

### Inspect EXIF Metadata (`inspect-exif`)

Inspect EXIF metadata of any image:
```bash
uv run inspect-exif image.jpg
```

---

## Running Tests

Run the full pytest suite:
```bash
uv run pytest
```

---

## Contributing & Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for local development instructions, test guidelines, and pull request procedures.

For a summary of release features and fixes, see [CHANGELOG.md](CHANGELOG.md).

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
