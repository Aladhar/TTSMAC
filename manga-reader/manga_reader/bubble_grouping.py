from manga_reader.config import (
    BUBBLE_VERTICAL_GAP_THRESHOLD,
    BUBBLE_HORIZONTAL_PADDING,
    BUBBLE_VERTICAL_OVERLAP_TOLERANCE,
)
from manga_reader.cleanup import clean_ocr_text, clean_tts_text
from manga_reader.models import Bubble, OCRLine, as_ocr_line
from typing import Union


def boxes_have_horizontal_overlap_or_close(bbox_a, bbox_b, padding: float) -> bool:
    ax1, ay1, ax2, ay2 = bbox_a
    bx1, by1, bx2, by2 = bbox_b

    return not (ax2 < bx1 - padding or ax1 > bx2 + padding)


def merge_bboxes(bbox_a, bbox_b):
    ax1, ay1, ax2, ay2 = bbox_a
    bx1, by1, bx2, by2 = bbox_b

    return [
        min(ax1, bx1),
        min(ay1, by1),
        max(ax2, bx2),
        max(ay2, by2),
    ]


def group_text_lines_into_bubbles(ocr_items: list[Union[OCRLine, dict]]) -> list[Bubble]:
    """
    Groups OCR text lines into rough speech bubbles / readable text blocks.

    This is not perfect yet. It is a practical first version.
    Later we can improve it using bubble shape detection and panel detection.
    """

    cleaned_items: list[OCRLine] = []

    for item in ocr_items:
        line = as_ocr_line(item)
        text = clean_ocr_text(line.text)
        if not text:
            continue

        cleaned_items.append(OCRLine(
            page=line.page,
            text=text,
            bbox=line.bbox,
            confidence=line.confidence,
            source=line.source,
        ))

    # Sort by top y position first.
    cleaned_items.sort(key=lambda item: item.bbox[1])

    groups = []

    for item in cleaned_items:
        bbox = item.bbox
        x1, y1, x2, y2 = bbox

        placed = False

        for group in groups:
            gx1, gy1, gx2, gy2 = group["bbox"]

            vertical_gap = y1 - gy2

            vertical_close = (
                -BUBBLE_VERTICAL_OVERLAP_TOLERANCE
                <= vertical_gap
                <= BUBBLE_VERTICAL_GAP_THRESHOLD
            )
            horizontal_close = boxes_have_horizontal_overlap_or_close(
                bbox,
                group["bbox"],
                BUBBLE_HORIZONTAL_PADDING,
            )

            if vertical_close and horizontal_close:
                group["items"].append(item)
                group["bbox"] = merge_bboxes(group["bbox"], bbox)
                placed = True
                break

        if not placed:
            groups.append({
                "bbox": bbox,
                "items": [item],
            })

    bubbles = []

    for index, group in enumerate(groups):
        # Inside one bubble, lines should read top-to-bottom.
        lines = sorted(group["items"], key=lambda item: item.bbox[1])

        text_display = "\n".join(line.text for line in lines)
        text_tts = clean_tts_text(text_display)

        if not text_tts:
            continue

        avg_confidence = sum(line.confidence for line in lines) / len(lines)

        bubbles.append(Bubble(
            page=lines[0].page,
            index=index,
            text_display=text_display,
            text_tts=text_tts,
            bbox=group["bbox"],
            items=lines,
            confidence=avg_confidence,
        ))

    return bubbles
