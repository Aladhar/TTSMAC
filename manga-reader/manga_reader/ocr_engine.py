import os

from manga_reader.config import MIN_OCR_CONFIDENCE, PADDLE_CACHE_DIR
from manga_reader.models import OCRLine


_ocr_instance = None


def get_ocr():
    """
    Creates PaddleOCR once and reuses it.
    This is slower the first time because it loads the model.
    """
    global _ocr_instance

    if _ocr_instance is None:
        PADDLE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(PADDLE_CACHE_DIR.resolve()))

        from paddleocr import PaddleOCR

        _ocr_instance = PaddleOCR(
            use_angle_cls=True,
            lang="en",
            show_log=False,
        )

    return _ocr_instance


def _iter_paddle_lines(result):
    if not result:
        return

    page_lines = result[0] if len(result) == 1 and isinstance(result[0], list) else result

    for line in page_lines or []:
        if line and len(line) >= 2:
            yield line


def run_ocr(image_path: str, page_index: int) -> list[OCRLine]:
    """
    Runs OCR on an image and returns OCR items with bounding boxes.

    Output bbox format:
    [x1, y1, x2, y2] in image coordinates.
    """

    ocr = get_ocr()
    result = ocr.ocr(image_path, cls=True)

    items: list[OCRLine] = []

    for line in _iter_paddle_lines(result):
        points = line[0]
        text = line[1][0]
        confidence = float(line[1][1])

        if confidence < MIN_OCR_CONFIDENCE:
            continue

        xs = [p[0] for p in points]
        ys = [p[1] for p in points]

        bbox = [
            float(min(xs)),
            float(min(ys)),
            float(max(xs)),
            float(max(ys)),
        ]

        items.append(OCRLine(
            page=page_index,
            text=text,
            bbox=bbox,
            confidence=confidence,
            source="paddleocr",
        ))

    return items
