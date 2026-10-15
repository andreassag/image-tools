import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from PIL import Image

from image_tools.common import resolve_target_format_and_ext, save_processed_image
from image_tools.metadata import build_exif


@dataclass
class ConversionResult:
    input_path: Path
    output_paths: List[Path] = field(default_factory=list)
    success: bool = True
    error_message: Optional[str] = None
    frames_processed: int = 0


def prepare_image_for_export(
    img: Image.Image,
    target_format: str,
    bg_color: Tuple[int, int, int] = (255, 255, 255)
) -> Image.Image:
    """
    Prepare PIL Image for export based on target format requirements.
    - Handles alpha channels (RGBA/LA) for JPEG by compositing onto background color.
    - Converts CMYK, Palette (P), Grayscale (1/I) to RGB where necessary.
    """
    fmt = target_format.upper()
    if fmt in ("JPEG", "JPG"):
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            canvas = Image.new("RGB", img.size, bg_color)
            rgba_img = img.convert("RGBA")
            canvas.paste(rgba_img, mask=rgba_img.split()[3])
            return canvas
        elif img.mode != "RGB":
            return img.convert("RGB")
    elif fmt == "PNG":
        if img.mode not in ("RGB", "RGBA", "L", "LA"):
            return img.convert("RGBA" if "transparency" in img.info else "RGB")
    elif fmt == "WEBP":
        if img.mode not in ("RGB", "RGBA"):
            return img.convert("RGBA" if "transparency" in img.info else "RGB")
    elif img.mode not in ("RGB", "RGBA"):
        return img.convert("RGB")

    return img.copy()


def convert_image(
    input_path: Path,
    output_dir: Optional[Path] = None,
    format: str = "JPEG",
    quality: int = 95,
    metadata_mode: str = "preserve",
    preset: Optional[str] = None,
    date_strategy: str = "auto",
    custom_exif: Optional[Dict[int, Any]] = None,
    pages: str = "all",
    touch_mtime: bool = False,
    bg_color: Tuple[int, int, int] = (255, 255, 255),
    dry_run: bool = False
) -> ConversionResult:
    """
    Convert a TIFF or image file to target format with EXIF metadata preservation.
    """
    input_path = Path(input_path).resolve()
    if not input_path.exists():
        return ConversionResult(
            input_path=input_path,
            success=False,
            error_message=f"File not found: {input_path}"
        )

    target_fmt, target_ext = resolve_target_format_and_ext(format, input_path)

    target_dir = Path(output_dir).resolve() if output_dir else input_path.parent
    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)

    result = ConversionResult(input_path=input_path)

    try:
        with Image.open(input_path) as img:
            dpi = img.info.get("dpi", (300.0, 300.0))
            icc_profile = img.info.get("icc_profile")

            n_frames = getattr(img, "n_frames", 1)
            frames_to_process = range(n_frames) if pages == "all" else range(min(1, n_frames))

            for frame_idx in frames_to_process:
                img.seek(frame_idx)
                frame_img = img.copy()

                if n_frames > 1 and pages == "all":
                    out_filename = f"{input_path.stem}_p{frame_idx + 1}{target_ext}"
                else:
                    out_filename = f"{input_path.stem}{target_ext}"

                out_path = target_dir / out_filename

                exif_obj = build_exif(
                    img=frame_img,
                    file_path=input_path,
                    metadata_mode=metadata_mode,
                    preset_name=preset,
                    date_strategy=date_strategy,
                    custom_exif=custom_exif,
                    dpi=dpi
                )

                export_img = prepare_image_for_export(frame_img, target_fmt, bg_color=bg_color)

                if not dry_run:
                    save_processed_image(
                        img=export_img,
                        out_path=out_path,
                        target_format=target_fmt,
                        quality=quality,
                        exif=exif_obj,
                        dpi=dpi,
                        icc_profile=icc_profile,
                        touch_mtime=touch_mtime
                    )

                result.output_paths.append(out_path)
                result.frames_processed += 1

    except Exception as e:
        result.success = False
        result.error_message = str(e)

    return result
