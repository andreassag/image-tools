import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from PIL import Image, ImageOps

from image_tools.common import resolve_target_format_and_ext, save_processed_image
from image_tools.converter import ConversionResult, prepare_image_for_export
from image_tools.metadata import build_exif


def transform_image(
    input_path: Path,
    output_dir: Optional[Path] = None,
    auto_rotate: bool = False,
    rotate: Optional[int] = None,
    flip_h: bool = False,
    flip_v: bool = False,
    format: Optional[str] = None,
    quality: int = 95,
    touch_mtime: bool = False,
    bg_color: Tuple[int, int, int] = (255, 255, 255),
    dry_run: bool = False
) -> ConversionResult:
    """
    Perform spatial transformations (EXIF auto-rotation, manual rotation, horizontal/vertical flips) on an image.
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

                current_img = frame_img

                # 1. EXIF Auto-Rotation
                if auto_rotate:
                    try:
                        transposed = ImageOps.exif_transpose(current_img)
                        if transposed is not None:
                            current_img = transposed
                            exif_obj[274] = 1
                    except Exception:
                        pass

                # 2. Manual Rotation (Clockwise)
                if rotate is not None:
                    deg = rotate % 360
                    if deg == 90:
                        current_img = current_img.transpose(Image.Transpose.ROTATE_270)
                        exif_obj[274] = 1
                    elif deg == 180:
                        current_img = current_img.transpose(Image.Transpose.ROTATE_180)
                        exif_obj[274] = 1
                    elif deg == 270:
                        current_img = current_img.transpose(Image.Transpose.ROTATE_90)
                        exif_obj[274] = 1
                    elif deg != 0:
                        # Arbitrary degree rotation clockwise
                        current_img = current_img.rotate(-deg, expand=True)
                        exif_obj[274] = 1

                # 3. Flips
                if flip_h:
                    current_img = current_img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                    exif_obj[274] = 1
                if flip_v:
                    current_img = current_img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
                    exif_obj[274] = 1

                export_img = prepare_image_for_export(current_img, target_fmt, bg_color=bg_color)

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
