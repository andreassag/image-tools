import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from PIL import Image, ImageDraw, ImageFont

from image_tools.converter import ConversionResult, prepare_image_for_export

try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    pypdf = None
    PYPDF_AVAILABLE = False


def create_pdf_from_images(
    image_paths: List[Path],
    output_path: Path,
    title: Optional[str] = None,
    author: Optional[str] = None,
    dry_run: bool = False
) -> ConversionResult:
    """
    Combine multiple images into a single multi-page PDF document.
    """
    output_path = Path(output_path).resolve()
    if not image_paths:
        return ConversionResult(
            input_path=output_path,
            success=False,
            error_message="No input images provided for PDF creation."
        )

    valid_imgs: List[Image.Image] = []

    try:
        for p in image_paths:
            p = Path(p).resolve()
            if p.exists():
                with Image.open(p) as img:
                    # Convert to RGB canvas for PDF compatibility
                    rgb_img = prepare_image_for_export(img, "JPEG")
                    valid_imgs.append(rgb_img)

        if not valid_imgs:
            return ConversionResult(
                input_path=output_path,
                success=False,
                error_message="None of the specified image files could be opened."
            )

        if not dry_run:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            first_img = valid_imgs[0]
            rest_imgs = valid_imgs[1:]
            first_img.save(output_path, "PDF", save_all=True, append_images=rest_imgs)

            # Apply PDF metadata via pypdf if available
            if PYPDF_AVAILABLE and (title or author):
                try:
                    reader = pypdf.PdfReader(str(output_path))
                    writer = pypdf.PdfWriter()
                    writer.append(reader)

                    metadata: Dict[str, str] = {}
                    if title:
                        metadata["/Title"] = title
                    if author:
                        metadata["/Author"] = author
                    metadata["/Producer"] = "image-tools"

                    writer.add_metadata(metadata)
                    with open(output_path, "wb") as f:
                        writer.write(f)
                except Exception:
                    pass

        # Close canvas handles
        for img in valid_imgs:
            img.close()

        return ConversionResult(
            input_path=output_path,
            output_paths=[output_path],
            success=True,
            frames_processed=len(valid_imgs)
        )

    except Exception as e:
        for img in valid_imgs:
            try:
                img.close()
            except Exception:
                pass
        return ConversionResult(
            input_path=output_path,
            success=False,
            error_message=str(e)
        )


def extract_images_from_pdf(
    pdf_path: Path,
    output_dir: Path,
    format: str = "PNG",
    dry_run: bool = False
) -> ConversionResult:
    """
    Unpack images embedded in a PDF document.
    Utilizes `pypdf` if available; otherwise attempts Pillow fallback.
    """
    pdf_path = Path(pdf_path).resolve()
    if not pdf_path.exists():
        return ConversionResult(
            input_path=pdf_path,
            success=False,
            error_message=f"PDF file not found: {pdf_path}"
        )

    output_dir = Path(output_dir).resolve()
    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    result = ConversionResult(input_path=pdf_path)
    target_ext = f".{format.lower()}"

    if PYPDF_AVAILABLE:
        try:
            reader = pypdf.PdfReader(str(pdf_path))
            img_count = 0

            for page_idx, page in enumerate(reader.pages):
                for img_file in page.images:
                    img_count += 1
                    out_name = f"{pdf_path.stem}_p{page_idx + 1}_img{img_count}{target_ext}"
                    out_p = output_dir / out_name

                    if not dry_run:
                        with open(out_p, "wb") as f:
                            f.write(img_file.data)

                    result.output_paths.append(out_p)
                    result.frames_processed += 1

            if img_count == 0:
                result.success = False
                result.error_message = f"No images found in PDF '{pdf_path.name}'."
            return result

        except Exception as e:
            result.success = False
            result.error_message = f"Error extracting images with pypdf: {e}"
            return result
    else:
        # Fallback to Pillow if pypdf is missing
        try:
            with Image.open(pdf_path) as img:
                n_frames = getattr(img, "n_frames", 1)
                for frame_idx in range(n_frames):
                    img.seek(frame_idx)
                    out_name = f"{pdf_path.stem}_p{frame_idx + 1}{target_ext}"
                    out_p = output_dir / out_name
                    if not dry_run:
                        export_img = prepare_image_for_export(img, format)
                        export_img.save(out_p, format)
                    result.output_paths.append(out_p)
                    result.frames_processed += 1
            return result
        except Exception:
            return ConversionResult(
                input_path=pdf_path,
                success=False,
                error_message=(
                    "Optional dependency 'pypdf' is required for PDF image extraction. "
                    "Install it via 'uv sync --extra pdf' or 'pip install pypdf'."
                )
            )


def create_contact_sheet(
    image_paths: List[Path],
    output_path: Path,
    cols: int = 4,
    rows: int = 4,
    cell_width: int = 200,
    cell_height: int = 200,
    padding: int = 15,
    annotate: bool = True,
    bg_color: Tuple[int, int, int] = (240, 240, 240),
    dry_run: bool = False
) -> ConversionResult:
    """
    Generate a thumbnail contact sheet composite from a list of images.
    """
    output_path = Path(output_path).resolve()
    if not image_paths:
        return ConversionResult(
            input_path=output_path,
            success=False,
            error_message="No images specified for contact sheet creation."
        )

    text_height = 25 if annotate else 0
    cell_total_w = cell_width + padding * 2
    cell_total_h = cell_height + text_height + padding * 2

    canvas_w = cols * cell_total_w
    canvas_h = rows * cell_total_h

    canvas = Image.new("RGB", (canvas_w, canvas_h), bg_color)
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    processed_count = 0

    try:
        for idx, p in enumerate(image_paths[: cols * rows]):
            p = Path(p).resolve()
            if not p.exists():
                continue

            r = idx // cols
            c = idx % cols

            x0 = c * cell_total_w + padding
            y0 = r * cell_total_h + padding

            with Image.open(p) as img:
                orig_w, orig_h = img.size
                ratio = min(cell_width / orig_w, cell_height / orig_h)
                thumb_w = max(1, int(orig_w * ratio))
                thumb_h = max(1, int(orig_h * ratio))

                thumb = img.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
                thumb_rgb = prepare_image_for_export(thumb, "JPEG")

                offset_x = x0 + (cell_width - thumb_w) // 2
                offset_y = y0 + (cell_height - thumb_h) // 2

                canvas.paste(thumb_rgb, (offset_x, offset_y))

                if annotate:
                    label = f"{p.name[:20]}\n{orig_w}x{orig_h}"
                    draw.text((x0, y0 + cell_height + 2), label, fill=(50, 50, 50), font=font)

                processed_count += 1

        if not dry_run:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            canvas.save(output_path, "PNG")

        return ConversionResult(
            input_path=output_path,
            output_paths=[output_path],
            success=True,
            frames_processed=processed_count
        )

    except Exception as e:
        return ConversionResult(
            input_path=output_path,
            success=False,
            error_message=str(e)
        )
