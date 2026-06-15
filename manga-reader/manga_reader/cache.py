from manga_reader.config import DEBUG_DIR, DETECTION_CACHE_DIR, PADDLE_CACHE_DIR, PAGE_CACHE_DIR


def ensure_cache_dirs() -> None:
    PAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    DETECTION_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    PADDLE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
