from manga_reader.bubble_grouping import group_text_lines_into_bubbles
from manga_reader.models import OCRLine


def test_groups_nearby_lines_into_one_bubble():
    lines = [
        OCRLine(page=0, text="HELLO", bbox=[100, 100, 200, 130], confidence=0.9),
        OCRLine(page=0, text="THERE", bbox=[105, 145, 210, 175], confidence=0.9),
    ]

    bubbles = group_text_lines_into_bubbles(lines)

    assert len(bubbles) == 1
    assert bubbles[0].text_display == "HELLO\nTHERE"


def test_separates_far_apart_lines():
    lines = [
        OCRLine(page=0, text="TOP", bbox=[100, 100, 200, 130], confidence=0.9),
        OCRLine(page=0, text="BOTTOM", bbox=[100, 500, 220, 530], confidence=0.9),
    ]

    bubbles = group_text_lines_into_bubbles(lines)

    assert len(bubbles) == 2


def test_separates_side_by_side_same_row_text():
    lines = [
        OCRLine(page=0, text="RIGHT", bbox=[300, 100, 380, 130], confidence=0.9),
        OCRLine(page=0, text="LEFT", bbox=[100, 100, 180, 130], confidence=0.9),
    ]

    bubbles = group_text_lines_into_bubbles(lines)

    assert len(bubbles) == 2
