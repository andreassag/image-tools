import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from PIL import Image, ImageDraw, ImageFont, ImageColor

from image_tools.common import resolve_target_format_and_ext, save_processed_image
from image_tools.converter import ConversionResult, prepare_image_for_export
from image_tools.metadata import build_exif, extract_datetime


def parse_color_rgba(color_str: str, opacity: float = 0.5) -> Tuple[int, int, int, int]:
    """Parse color string (hex or name) and opacity (0.0 - 1.0) into RGBA tuple."""
    try:
        rgb = ImageColor.getrgb(color_str)
    except Exception:
        rgb = (255, 255, 255)
    alpha = max(0, min(255, int(opacity * 255)))
    return (rgb[0], rgb[1], rgb[2], alpha)


def calculate_position(
    base_w: int,
    base_h: int,
    wm_w: int,
    wm_h: int,
    position: str = "bottom-right",
    margin: int = 20
) -> Tuple[int, int]:
    """Calculate (x, y) top-left placement coordinates for watermark."""
    pos = position.lower()
    if pos == "top-left":
        return (margin, margin)
    elif pos == "top-center":
        return ((base_w - wm_w) // 2, margin)
    elif pos == "top-right":
        return (base_w - wm_w - margin, margin)
    elif pos == "center-left":
        return (margin, (base_h - wm_h) // 2)
    elif pos == "center":
        return ((base_w - wm_w) // 2, (base_h - wm_h) // 2)
    elif pos == "center-right":
        return (base_w - wm_w - margin, (base_h - wm_h) // 2)
    elif pos == "bottom-left":
        return (margin, base_h - wm_h - margin)
    elif pos == "bottom-center":
        return ((base_w - wm_w) // 2, base_h - wm_h - margin)
    else:  # bottom-right (default)
        return (base_w - wm_w - margin, base_h - wm_h - margin)


def apply_watermark(
    input_path: Path,
    output_dir: Optional[Path] = None,
    text: Optional[str] = None,
    image_logo: Optional[Path] = None,
    position: str = "bottom-right",
    opacity: float = 0.5,
    color: str = "white",
    font_size: Optional[int] = None,
    font_scale: float = 0.04,
    font_path: Optional[Path] = None,
    logo_scale: float = 0.2,
    margin: int = 20,
    format: Optional[str] = None,
    quality: int = 95,
    touch_mtime: bool = False,
    bg_color: Tuple[int, int, int] = (255, 255, 255),
    dry_run: bool = False
) -> ConversionResult:
    """
    Apply text or image logo watermarks to an image.
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

            for frame_idx in range(n_frames):
                img.seek(frame_idx)
                frame_img = img.copy()
                base_w, base_h = frame_img.size

                out_filename = (
                    f"{input_path.stem}_p{frame_idx + 1}{target_ext}"
                    if n_frames > 1 else f"{input_path.stem}{target_ext}"
                )
                out_path = target_dir / out_filename

                exif_obj = build_exif(
                    img=frame_img,
                    file_path=input_path,
                    metadata_mode="preserve",
                    dpi=dpi
                )

                watermarked = frame_img.convert("RGBA")
                overlay = Image.new("RGBA", (base_w, base_h), (0, 0, 0, 0))

                # 1. Text Watermark
                if text:
                    date_str = extract_datetime(frame_img, input_path)
                    formatted_text = text.format(
                        date=date_str,
                        stem=input_path.stem,
                        filename=input_path.name
                    )

                    calc_font_size = font_size or max(12, int(min(base_w, base_h) * font_scale))
                    if font_path and Path(font_path).exists():
                        try:
                            font = ImageFont.truetype(str(font_path), calc_font_size)
                        except Exception:
                            font = ImageFont.load_default()
                    else:
                        try:
                            font = ImageFont.load_default(size=calc_font_size)
                        except Exception:
                            font = ImageFont.load_default()

                    draw = ImageDraw.Draw(overlay)
                    rgba_color = parse_color_rgba(color, opacity)

                    bbox = draw.textbbox((0, 0), formatted_text, font=font)
                    wm_w = bbox[2] - bbox[0]
                    wm_h = bbox[3] - bbox[1]

                    if position.lower() == "tiled":
                        step_x = max(1, wm_w + margin * 2)
                        step_y = max(1, wm_h + margin * 2)
                        for y in range(margin, base_h, step_y):
                            for x in range(margin, base_w, step_x):
                                draw.text((x, y), formatted_text, font=font, fill=rgba_color)
                    else:
                        x, y = calculate_position(base_w, base_h, wm_w, wm_h, position, margin)
                        draw.text((x, y), formatted_text, font=font, fill=rgba_color)

                # 2. Image Logo Watermark
                if image_logo:
                    logo_path = Path(image_logo).resolve()
                    if logo_path.exists():
                        with Image.open(logo_path) as logo_img:
                            logo_rgba = logo_img.convert("RGBA")
                            target_logo_w = max(1, int(base_w * logo_scale))
                            target_logo_h = max(1, int(logo_rgba.height * (target_logo_w / logo_rgba.width)))
                            scaled_logo = logo_rgba.resize((target_logo_w, target_logo_h), Image.Resampling.LANCZOS)

                            r, g, b, a = scaled_logo.split()
                            a = a.point(lambda p: int(p * opacity))
                            scaled_logo.putalpha(a)

                            wm_w, wm_h = scaled_logo.size
                            if position.lower() == "tiled":
                                step_x = max(1, wm_w + margin * 2)
                                step_y = max(1, wm_h + margin * 2)
                                for y in range(margin, base_h, step_y):
                                    for x in range(margin, base_w, step_x):
                                        overlay.alpha_composite(scaled_logo, (x, y))
                            else:
                                x, y = calculate_position(base_w, base_h, wm_w, wm_h, position, margin)
                                overlay.alpha_composite(scaled_logo, (x, y))

                composite_img = Image.alpha_composite(watermarked, overlay)
                export_img = prepare_image_for_export(composite_img, target_fmt, bg_color=bg_color)

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
