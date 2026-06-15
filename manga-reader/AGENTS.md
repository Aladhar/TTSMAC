# manga-reader Agent Notes

- Use a normal local Python virtual environment named `.venv`.
- Do not use Docker for setup or execution.
- Keep OCR, debug overlay, and future viewer boxes in rendered image coordinates.
- Do not modify the source PDF.
- Keep `main.py` as CLI orchestration only; put logic in `manga_reader/`.
- Phase 1 and Phase 2 are CLI-first: render, OCR, clean, group, sort, print, and save debug overlays.
- PaddleOCR is the preferred OCR engine. EasyOCR can be used later as a fallback if PaddleOCR is difficult on macOS.
