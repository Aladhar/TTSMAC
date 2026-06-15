# manga-reader

CLI-first manga PDF reader prototype.

Phase 1 renders a manga PDF page as an image, runs OCR, lightly cleans text,
groups OCR lines into speech-bubble-like blocks, sorts them in manga reading
order, and prints the bubbles.

Phase 2 adds a debug overlay image showing raw OCR boxes, grouped bubble boxes,
and reading-order numbers.

Docker is intentionally not used. Use a local Python virtual environment.

## Setup on macOS

```bash
cd manga-reader
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

## Run Phase 1

```bash
python main.py "YOUR_MANGA.pdf" --page 0
```

## Run Phase 2 With Debug Overlay

```bash
python main.py "YOUR_MANGA.pdf" --page 0 --debug
```

Expected output:

```text
Rendering page 0...
Saved page image: cache/pages/page_0000.png
Running OCR...
Detected OCR lines: 20
Grouping text into bubbles...
Grouped bubbles: 7
Sorting bubbles in manga reading order...
Saved debug image: debug/page_0000_debug.png

[Page 1 - Bubble 1]
TEXT HERE
```

## Test

```bash
pytest
```

## Output Folders

- `cache/pages/`: rendered PDF pages as PNG files
- `cache/detections/`: reserved for later OCR/cache JSON
- `debug/`: debug overlay images

## Common macOS Errors And Fixes

If `paddlepaddle` or `paddleocr` fails to install, first upgrade packaging tools:

```bash
python -m pip install --upgrade pip setuptools wheel
```

If install still fails, confirm you are using Python 3.10 or 3.11:

```bash
python --version
```

If OpenCV import fails on macOS, reinstall it inside the active venv:

```bash
pip uninstall -y opencv-python
pip install opencv-python
```

If PaddleOCR remains problematic on macOS, the fallback plan is:

```bash
pip install easyocr
```

Then add an `easyocr_engine.py` module later that returns the same `OCRLine`
objects as `ocr_engine.py`. PaddleOCR remains the preferred first attempt.
