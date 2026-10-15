import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from PIL import Image

from image_tools.common import resolve_target_format_and_ext, save_processed_image
from image_tools.converter import ConversionResult, prepare_image_for_export
from image_tools.metadata import build_exif

RESAMPLE_FILTERS: Dict[str, Image.Resampling] = {
    "lanczos": Image.Resampling.LANCZOS,
    "bicubic": Image.Resampling.BICUBIC,
    "bilinear": Image.Resampling.BILINEAR,
    "nearest": Image.Resampling.NEAREST,
}


def calculate_target_dimensions(
    orig_w: int,
    orig_h: int,
    width: Optional[int] = None,
    height: Optional[int] = None,
    max_dim: Optional[int] = None,
    scale: Optional[float] = None,
    aspect_ratio_mode: str = "fit"
) -> Tuple[int, int]:
    """
    Calculate target image dimensions based on arguments.
    Modes:
    - 'fit': Scale inside bounding box (width, height) preserving aspect ratio.
    - 'fill': Scale to cover bounding box (width, height) preserving aspect ratio.
    - 'pad': Scale inside bounding box (width, height), center on canvas.
    - 'stretch': Ignore aspect ratio, force exact width and height.
    """
    if orig_w <= 0 or orig_h <= 0:
        return (max(1, orig_w), max(1, orig_h))

    # 1. Percentage scale
    if scale is not None and scale > 0:
        factor = scale / 100.0
        new_w = max(1, round(orig_w * factor))
        new_h = max(1, round(orig_h * factor))
        return (new_w, new_h)

    # 2. Max dimension (bounding box)
    if max_dim is not None and max_dim > 0:
        ratio = min(max_dim / orig_w, max_dim / orig_h)
        new_w = max(1, round(orig_w * ratio))
        new_h = max(1, round(orig_h * ratio))
        return (new_w, new_h)

    # 3. Explicit Width and/or Height
    if width is not None and height is not None:
        if aspect_ratio_mode == "stretch":
            return (width, height)

        aspect_orig = orig_w / orig_h
        aspect_target = width / height

        if aspect_ratio_mode in ("fit", "pad"):
            if aspect_orig > aspect_target:
                # Constrained by width
                return (width, max(1, round(width / aspect_orig)))
            else:
                # Constrained by height
                return (max(1, round(height * aspect_orig)), height)

        elif aspect_ratio_mode == "fill":
            if aspect_orig > aspect_target:
                # Scale by height to cover target width
                return (max(1, round(height * aspect_orig)), height)
            else:
                # Scale by width to cover target height
                return (width, max(1, round(width / aspect_orig)))

    if width is not None:
        return (width, max(1, round(width * orig_h / orig_w)))

    if height is not None:
        return (max(1, round(height * orig_w / orig_h)), height)

    return (orig_w, orig_h)


def resize_image(
    input_path: Path,
    output_dir: Optional[Path] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    max_dim: Optional[int] = None,
    scale: Optional[float] = None,
    aspect_ratio_mode: str = "fit",
    resample_filter: str = "lanczos",
    bg_color: Tuple[int, int, int] = (255, 255, 255),
    format: Optional[str] = None,
    quality: int = 95,
    metadata_mode: str = "preserve",
    preset: Optional[str] = None,
    date_strategy: str = "auto",
    custom_exif: Optional[Dict[int, Any]] = None,
    touch_mtime: bool = False,
    dry_run: bool = False
) -> ConversionResult:
    """
    Resize an image file with aspect ratio control, filter choices, and EXIF metadata preservation.
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
    resample = RESAMPLE_FILTERS.get(resample_filter.lower(), Image.Resampling.LANCZOS)

    try:
        with Image.open(input_path) as img:
            dpi = img.info.get("dpi", (300.0, 300.0))
            icc_profile = img.info.get("icc_profile")
            n_frames = getattr(img, "n_frames", 1)

            for frame_idx in range(n_frames):
                img.seek(frame_idx)
                frame_img = img.copy()
                orig_w, orig_h = frame_img.size

                new_w, new_h = calculate_target_dimensions(
                    orig_w=orig_w,
                    orig_h=orig_h,
                    width=width,
                    height=height,
                    max_dim=max_dim,
                    scale=scale,
                    aspect_ratio_mode=aspect_ratio_mode
                )

                resized = frame_img.resize((new_w, new_h), resample=resample)

                final_img = resized
                if width is not None and height is not None:
                    if aspect_ratio_mode == "fill":
                        left = (new_w - width) // 2
                        top = (new_h - height) // 2
                        final_img = resized.crop((left, top, left + width, top + height))
                    elif aspect_ratio_mode == "pad":
                        mode = "RGBA" if resized.mode in ("RGBA", "LA") else "RGB"
                        canvas = Image.new(mode, (width, height), bg_color)
                        left = (width - new_w) // 2
                        top = (height - new_h) // 2
                        canvas.paste(resized, (left, top))
                        final_img = canvas

                if n_frames > 1:
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

                export_img = prepare_image_for_export(final_img, target_fmt, bg_color=bg_color)

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
