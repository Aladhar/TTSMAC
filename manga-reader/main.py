import argparse

from manga_reader.cache import ensure_cache_dirs
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
        help="Page index to process. Starts at 0."
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
        help="Save a debug overlay with OCR boxes, bubble boxes, and reading-order numbers."
    )

    args = parser.parse_args()
    ensure_cache_dirs()
    pdf_path = require_existing_file(args.pdf)

    print(f"Rendering page {args.page}...")
    page_data = render_page(str(pdf_path), args.page, args.zoom)

    print(f"Saved page image: {page_data['image_path']}")

    print("Running OCR...")
    ocr_items = run_ocr(page_data["image_path"], args.page)

    print(f"Detected OCR lines: {len(ocr_items)}")

    print("Grouping text into bubbles...")
    bubbles = group_text_lines_into_bubbles(ocr_items)

    print(f"Grouped bubbles: {len(bubbles)}")

    print("Sorting bubbles in manga reading order...")
    ordered_bubbles = sort_bubbles_manga_order(bubbles)

    if args.debug:
        debug_path = save_debug_overlay(
            page_data["image_path"],
            ocr_items,
            ordered_bubbles,
            args.page,
        )
        print(f"Saved debug image: {debug_path}")

    print_bubbles(ordered_bubbles)


if __name__ == "__main__":
    main()
