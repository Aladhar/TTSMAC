import re


def clean_ocr_text(text: str) -> str:
    """
    Cleans raw OCR text lightly.
    Do not overcorrect here because manga names/dialogue can be weird.
    """

    if not text:
        return ""

    text = text.strip()

    fixes = {
        "|": "I",
        "ﬁ": "fi",
        "ﬂ": "fl",
    }

    for wrong, right in fixes.items():
        text = text.replace(wrong, right)

    # Remove weird repeated whitespace.
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def clean_tts_text(text: str) -> str:
    """
    Converts display text into text that sounds better in TTS.
    """

    if not text:
        return ""

    text = text.replace("\n", " ")
    text = text.replace("…", "...")
    text = re.sub(r"\s+", " ", text)

    return text.strip()