from pathlib import Path
import fitz

from manga_reader.config import PAGE_CACHE_DIR, DEFAULT_RENDER_ZOOM


def render_page(pdf_path: str, page_index: int, zoom: float = DEFAULT_RENDER_ZOOM) -> dict:
    """
    Renders one PDF page into a PNG image.

    Returns metadata containing image path and zoom.
    OCR boxes will be in IMAGE coordinates, not PDF coordinates.
    """

    PAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    doc = fitz.open(str(pdf_path))

    if page_index < 0 or page_index >= len(doc):
        raise ValueError(f"Page index {page_index} is out of range. PDF has {len(doc)} pages.")

    page = doc[page_index]

    matrix = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=matrix, alpha=False)

    image_path = PAGE_CACHE_DIR / f"page_{page_index:04d}.png"
    pix.save(str(image_path))

    page_data = {
        "pdf_path": str(pdf_path),
        "page_index": page_index,
        "image_path": str(image_path),
        "pdf_width": float(page.rect.width),
        "pdf_height": float(page.rect.height),
        "image_width": pix.width,
        "image_height": pix.height,
        "zoom": zoom,
    }

    doc.close()
    return page_data