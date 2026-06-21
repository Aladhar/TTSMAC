import argparse
from pathlib import Path

import fitz

from manga_reader.cache import ensure_cache_dirs, save_detection_cache
from manga_reader.debug_overlay import save_debug_overlay
from manga_reader.pdf_renderer import render_page
from manga_reader.ocr_engine import run_ocr
from manga_reader.bubble_grouping import group_text_lines_into_bubbles
from manga_reader.reading_order import sort_bubbles_manga_order
from manga_reader.utils import require_existing_file


def print_bubbles(bubbles):
    if not bubbles:
        print("No readable text bubbles detected.")
        return

    for bubble in bubbles:
        page_num = bubble.page + 1
        index = bubble.index

        print()
        print(f"[Page {page_num} - Bubble {index}]")
        print(bubble.text_display)


def get_pdf_page_count(pdf_path: Path) -> int:
    with fitz.open(str(pdf_path)) as doc:
        return len(doc)


def parse_page_list(pages_text: str) -> list[int]:
    """
    Parses --pages like:
      0,1,2
      0, 2, 5
    """
    pages = []

    for part in pages_text.split(","):
        part = part.strip()
        if not part:
            continue

        page = int(part)
        if page < 0:
            raise ValueError(f"Page index cannot be negative: {page}")

        pages.append(page)

    return pages


def resolve_pages(args, pdf_page_count: int) -> list[int]:
    """
    Figure out which pages to process.

    Priority:
    1. --all-pages
    2. --pages 0,2,5
    3. --start-page / --end-page
    4. --page
    """

    if args.all_pages:
        return list(range(pdf_page_count))

    if args.pages:
        pages = parse_page_list(args.pages)
    elif args.start_page is not None or args.end_page is not None:
        start_page = args.start_page if args.start_page is not None else 0
        end_page = args.end_page if args.end_page is not None else start_page

        if start_page < 0:
            raise ValueError("--start-page cannot be negative")

        if end_page < start_page:
            raise ValueError("--end-page must be >= --start-page")

        # Inclusive end page, so --start-page 0 --end-page 5 processes 0,1,2,3,4,5.
        pages = list(range(start_page, end_page + 1))
    else:
        pages = [args.page]

    bad_pages = [page for page in pages if page < 0 or page >= pdf_page_count]
    if bad_pages:
        raise ValueError(
            f"Page index out of range: {bad_pages}. "
            f"PDF has {pdf_page_count} pages, valid indexes are 0 to {pdf_page_count - 1}."
        )

    # Remove duplicates while keeping order.
    seen = set()
    unique_pages = []
    for page in pages:
        if page not in seen:
            unique_pages.append(page)
            seen.add(page)

    return unique_pages


def process_page(pdf_path: Path, page_index: int, zoom: float, debug: bool) -> None:
    print()
    print("=" * 60)
    print(f"Processing page index {page_index} / printed page {page_index + 1}")
    print("=" * 60)

    print(f"Rendering page {page_index}...")
    page_data = render_page(str(pdf_path), page_index, zoom)

    print(f"Saved page image: {page_data['image_path']}")

    print("Running OCR...")
    ocr_items = run_ocr(page_data["image_path"], page_index)

    print(f"Detected OCR lines: {len(ocr_items)}")

    print("Grouping text into bubbles...")
    bubbles = group_text_lines_into_bubbles(ocr_items)

    print(f"Grouped bubbles: {len(bubbles)}")

    print("Sorting bubbles in manga reading order...")
    ordered_bubbles = sort_bubbles_manga_order(bubbles)

    detection_path = save_detection_cache(
        page_index,
        page_data,
        ocr_items,
        ordered_bubbles,
    )
    print(f"Saved detection cache: {detection_path}")

    if debug:
        debug_path = save_debug_overlay(
            page_data["image_path"],
            ocr_items,
            ordered_bubbles,
            page_index,
        )
        print(f"Saved debug image: {debug_path}")

    print_bubbles(ordered_bubbles)


def main():
    parser = argparse.ArgumentParser(
        description="Manga PDF OCR reader prototype."
    )

    parser.add_argument(
        "pdf",
        help="Path to manga PDF file."
    )

    parser.add_argument(
        "--page",
        type=int,
        default=0,
        help="Single page index to process. Starts at 0. Default: 0."
    )

    parser.add_argument(
        "--pages",
        type=str,
        default=None,
        help='Specific page indexes to process, like "0,2,5,9".'
    )

    parser.add_argument(
        "--start-page",
        type=int,
        default=None,
        help="First page index to process for a page range. Starts at 0."
    )

    parser.add_argument(
        "--end-page",
        type=int,
        default=None,
        help="Last page index to process for a page range. Inclusive."
    )

    parser.add_argument(
        "--all-pages",
        action="store_true",
        help="Process every page in the PDF."
    )

    parser.add_argument(
        "--zoom",
        type=float,
        default=2.5,
        help="Render zoom for OCR. Higher is sharper but slower."
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Save debug overlays with OCR boxes, bubble boxes, and reading-order numbers."
    )

    args = parser.parse_args()

    ensure_cache_dirs()
    pdf_path = require_existing_file(args.pdf)
    pdf_page_count = get_pdf_page_count(pdf_path)

    pages_to_process = resolve_pages(args, pdf_page_count)

    print(f"PDF: {pdf_path}")
    print(f"Total PDF pages: {pdf_page_count}")
    print(f"Pages to process: {pages_to_process}")

    for page_index in pages_to_process:
        process_page(
            pdf_path=pdf_path,
            page_index=page_index,
            zoom=args.zoom,
            debug=args.debug,
        )

    print()
    print("Done.")
    print("Check these folders:")
    print("  cache/pages")
    print("  cache/detections")
    print("  debug")


if __name__ == "__main__":
    main()
    