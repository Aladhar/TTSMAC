import argparse

from manga_reader.pdf_renderer import render_page
from manga_reader.ocr_engine import run_ocr
from manga_reader.bubble_grouping import group_text_lines_into_bubbles
from manga_reader.reading_order import sort_bubbles_manga_order


def print_bubbles(bubbles: list[dict]):
    if not bubbles:
        print("No readable text bubbles detected.")
        return

    for bubble in bubbles:
        page_num = bubble["page"] + 1
        index = bubble["index"]

        print()
        print(f"[Page {page_num} - Bubble {index}]")
        print(bubble["text_display"])


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

    args = parser.parse_args()

    print(f"Rendering page {args.page}...")
    page_data = render_page(args.pdf, args.page, args.zoom)

    print(f"Saved page image: {page_data['image_path']}")

    print("Running OCR...")
    ocr_items = run_ocr(page_data["image_path"], args.page)

    print(f"Detected OCR lines: {len(ocr_items)}")

    print("Grouping text into bubbles...")
    bubbles = group_text_lines_into_bubbles(ocr_items)

    print(f"Grouped bubbles: {len(bubbles)}")

    print("Sorting bubbles in manga reading order...")
    ordered_bubbles = sort_bubbles_manga_order(bubbles)

    print_bubbles(ordered_bubbles)


if __name__ == "__main__":
    main()