# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.0] - 2026-10-16

### Added
- **Batch Image Resizing** (`image-resize`): Support for fit, fill, pad, and stretch aspect ratio modes, percentage scaling, and resampling filters.
- **Intelligent Compression** (`image-compress`): Binary search target size optimization (`--target-size`), quality presets, and metadata/GPS sanitization (`--strip-gps`, `--strip-exif`).
- **Spatial Transformations & Auto-Rotation** (`image-orient`): Automatic EXIF Orientation tag rotation (`--auto-rotate`), 90°/180°/270° clockwise manual rotations, and horizontal/vertical flips.
- **EXIF Metadata Editing & JSON Export/Import** (`edit-exif`): Direct tag setting, deletion, and JSON export/import.
- **Metadata-Driven File Renaming** (`image-rename`): Pattern-based batch renaming with collision resolution (`_1`, `_2`).
- **Batch Watermarking & Branding** (`image-watermark`): Text and image logo overlays with 9-point grid alignment, tiled patterns, and opacity control.
- **PDF Document Tools** (`image-pdf`): Multi-page PDF assembly, image extraction, and contact sheet grid generation.
- **Device Presets**: Preset profiles (`canon_lide_400`, `generic_scanner`) for scanner metadata emulation.
- **Color Profile Retention**: Automatic preservation of embedded ICC color profiles across conversions.
- **PEP 561 Type Support**: Included `py.typed` marker for IDEs and type checkers.
- **CI/CD Matrix**: Automated GitHub Actions testing across Ubuntu, macOS, and Windows on Python 3.12 and 3.13.

### Fixed
- Fixed compounding suffix bug in metadata-based filename collision resolution (`photo_1_2.jpg` -> `photo_2.jpg`).
- Fixed unclosed image file descriptors during PDF document assembly.
- Corrected rotation angle validation and EXIF orientation synchronization.
- Automatic integer/float casting for numeric EXIF tags during editing.
- Added fault tolerance to parallel `ProcessPoolExecutor` batch tasks against worker exceptions.
