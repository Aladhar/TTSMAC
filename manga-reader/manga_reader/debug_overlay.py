from __future__ import annotations

import cv2
from typing import Union

from manga_reader.config import DEBUG_DIR
from manga_reader.models import Bubble, OCRLine, as_bubble, as_ocr_line


def _draw_label(image, text: str, x: int, y: int, color: tuple[int, int, int]) -> None:
    cv2.putText(
        image,
        text,
        (x, y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        color,
        2,
        cv2.LINE_AA,
    )


def save_debug_overlay(
    image_path: str,
    ocr_items: list[Union[OCRLine, dict]],
    bubbles: list[Union[Bubble, dict]],
    page_index: int,
) -> str:
    """
    Saves a visual debug image with raw OCR boxes and final bubble order.

    Green boxes are raw OCR lines.
    Blue boxes are grouped bubbles.
    Red numbers are manga reading-order bubble indexes.
    """

    DEBUG_DIR.mkdir(parents=True, exist_ok=True)

    image = cv2.imread(str(image_path))
    if image is None:
        raise FileNotFoundError(f"Could not read rendered page image: {image_path}")

    for item in ocr_items:
        line = as_ocr_line(item)
        x1, y1, x2, y2 = [int(round(value)) for value in line.bbox]
        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 180, 0), 2)

    for item in bubbles:
        bubble = as_bubble(item)
        x1, y1, x2, y2 = [int(round(value)) for value in bubble.bbox]
        cv2.rectangle(image, (x1, y1), (x2, y2), (255, 80, 0), 4)
        _draw_label(image, str(bubble.index), x1, max(30, y1 - 10), (0, 0, 255))

    output_path = DEBUG_DIR / f"page_{page_index:04d}_debug.png"
    cv2.imwrite(str(output_path), image)
    return str(output_path)
