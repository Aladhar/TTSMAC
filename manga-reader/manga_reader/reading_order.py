from manga_reader.config import ROW_Y_THRESHOLD


def center_y(bubble: dict) -> float:
    x1, y1, x2, y2 = bubble["bbox"]
    return (y1 + y2) / 2


def center_x(bubble: dict) -> float:
    x1, y1, x2, y2 = bubble["bbox"]
    return (x1 + x2) / 2


def sort_bubbles_manga_order(bubbles: list[dict]) -> list[dict]:
    """
    Sort bubbles in manga order:
    rows top-to-bottom, then bubbles inside each row right-to-left.
    """

    if not bubbles:
        return []

    # First sort by vertical position.
    bubbles = sorted(bubbles, key=center_y)

    rows = []

    for bubble in bubbles:
        cy = center_y(bubble)

        placed = False

        for row in rows:
            if abs(cy - row["cy"]) <= ROW_Y_THRESHOLD:
                row["bubbles"].append(bubble)

                # Update row center average.
                row["cy"] = sum(center_y(b) for b in row["bubbles"]) / len(row["bubbles"])

                placed = True
                break

        if not placed:
            rows.append({
                "cy": cy,
                "bubbles": [bubble],
            })

    # Rows go top-to-bottom.
    rows.sort(key=lambda row: row["cy"])

    ordered = []

    for row in rows:
        # Manga reads right-to-left inside the row.
        row["bubbles"].sort(key=center_x, reverse=True)
        ordered.extend(row["bubbles"])

    # Re-index final reading order.
    for i, bubble in enumerate(ordered, start=1):
        bubble["index"] = i

    return ordered