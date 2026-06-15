from paddleocr import PaddleOCR

from manga_reader.config import MIN_OCR_CONFIDENCE


_ocr_instance = None


def get_ocr():
    """
    Creates PaddleOCR once and reuses it.
    This is slower the first time because it loads the model.
    """
    global _ocr_instance

    if _ocr_instance is None:
        _ocr_instance = PaddleOCR(
            use_angle_cls=True,
            lang="en"
        )

    return _ocr_instance


def run_ocr(image_path: str, page_index: int) -> list[dict]:
    """
    Runs OCR on an image and returns OCR items with bounding boxes.

    Output bbox format:
    [x1, y1, x2, y2] in image coordinates.
    """

    ocr = get_ocr()
    result = ocr.ocr(image_path, cls=True)

    items = []

    if not result or not result[0]:
        return items

    for line in result[0]:
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

        items.append({
            "page": page_index,
            "text": text,
            "bbox": bbox,
            "confidence": confidence,
            "source": "paddleocr",
        })

    return items