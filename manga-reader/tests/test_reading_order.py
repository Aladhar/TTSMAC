from manga_reader.models import Bubble
from manga_reader.reading_order import sort_bubbles_manga_order


def make_bubble(label, bbox):
    return Bubble(
        page=0,
        index=0,
        text_display=label,
        text_tts=label,
        bbox=bbox,
        items=[],
        confidence=1.0,
    )


def test_manga_order_top_to_bottom_then_right_to_left():
    bubbles = [
        make_bubble("left top", [50, 100, 150, 200]),
        make_bubble("right top", [300, 100, 400, 200]),
        make_bubble("lower", [200, 400, 300, 500]),
    ]

    ordered = sort_bubbles_manga_order(bubbles)

    assert [bubble.text_display for bubble in ordered] == ["right top", "left top", "lower"]
    assert [bubble.index for bubble in ordered] == [1, 2, 3]
