import json
from dataclasses import asdict, is_dataclass

from manga_reader.config import DEBUG_DIR, DETECTION_CACHE_DIR, PADDLE_CACHE_DIR, PAGE_CACHE_DIR


def ensure_cache_dirs() -> None:
    PAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    DETECTION_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    PADDLE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)


def _to_plain(value):
    """
    Convert dataclasses/lists/dicts into JSON-safe values.
    This makes OCR runs replayable so false positives, false negatives,
    grouping errors, and reading-order errors can be manually audited later.
    """
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, list):
        return [_to_plain(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_plain(item) for key, item in value.items()}
    return value


def save_detection_cache(page_index: int, page_data: dict, ocr_items: list, bubbles: list) -> str:
    """
    Save one page's rendered-page metadata, raw OCR lines, and final ordered bubbles.
    """
    DETECTION_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    output_path = DETECTION_CACHE_DIR / f"page_{page_index:04d}.json"
    payload = {
        "page_data": _to_plain(page_data),
        "ocr_items": _to_plain(ocr_items),
        "bubbles": _to_plain(bubbles),
    }
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(output_path)