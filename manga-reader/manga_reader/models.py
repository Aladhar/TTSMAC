from __future__ import annotations

from dataclasses import dataclass, field
from typing import Union


BBox = list[float]


@dataclass
class OCRLine:
    page: int
    text: str
    bbox: BBox
    confidence: float
    source: str = "paddleocr"


@dataclass
class Bubble:
    page: int
    index: int
    text_display: str
    text_tts: str
    bbox: BBox
    items: list[OCRLine] = field(default_factory=list)
    confidence: float = 0.0

    @property
    def center_x(self) -> float:
        return (self.bbox[0] + self.bbox[2]) / 2

    @property
    def center_y(self) -> float:
        return (self.bbox[1] + self.bbox[3]) / 2


def as_ocr_line(item: Union[OCRLine, dict]) -> OCRLine:
    if isinstance(item, OCRLine):
        return item

    return OCRLine(
        page=int(item["page"]),
        text=str(item["text"]),
        bbox=[float(value) for value in item["bbox"]],
        confidence=float(item.get("confidence", 0.0)),
        source=str(item.get("source", "unknown")),
    )


def as_bubble(item: Union[Bubble, dict]) -> Bubble:
    if isinstance(item, Bubble):
        return item

    return Bubble(
        page=int(item["page"]),
        index=int(item.get("index", 0)),
        text_display=str(item["text_display"]),
        text_tts=str(item.get("text_tts", item["text_display"])),
        bbox=[float(value) for value in item["bbox"]],
        items=[as_ocr_line(line) for line in item.get("items", [])],
        confidence=float(item.get("confidence", 0.0)),
    )
