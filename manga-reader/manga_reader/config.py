from pathlib import Path

CACHE_DIR = Path("cache")
PAGE_CACHE_DIR = CACHE_DIR / "pages"
DETECTION_CACHE_DIR = CACHE_DIR / "detections"
DEBUG_DIR = Path("debug")

DEFAULT_RENDER_ZOOM = 2.5
MIN_OCR_CONFIDENCE = 0.55

# Manga usually reads right-to-left.
READING_MODE = "manga_rtl"

# Used for grouping OCR text lines into bubbles.
BUBBLE_VERTICAL_GAP_THRESHOLD = 55
BUBBLE_HORIZONTAL_PADDING = 120

# Used for row grouping in manga reading order.
ROW_Y_THRESHOLD = 90