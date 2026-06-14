from PIL import Image, ImageOps, ImageEnhance, ImageDraw
import pytesseract
import subprocess
import re
import asyncio
import edge_tts
import tempfile
import os


# ==============================
# SETTINGS
# ==============================

IMG_PATH = "image.png"

# Manga is usually right-to-left.
READING_DIRECTION = "rtl"

# Lower = catches more text but more garbage.
# Higher = cleaner but may miss tiny words like "SO?"
MIN_CONF = 25

# Edge neural voice settings.
# Try:
# en-US-AriaNeural
# en-US-GuyNeural
# en-US-JennyNeural
# en-US-DavisNeural
VOICE = "en-US-AriaNeural"
RATE = "-8%"
VOLUME = "+0%"

# If True, saves debug image with detected text boxes.
SAVE_DEBUG_IMAGE = True

# If True, speaks text out loud.
SPEAK_OUT_LOUD = True

# If True, prints the text that is sent to TTS after pronunciation fixes.
PRINT_TTS_TEXT = False


VALID_SHORT_WORDS = {
    "I", "A", "MY", "ME", "SO", "DO", "NO", "TO", "OF", "IN", "IS", "IT",
    "HE", "WE", "US", "UP", "GO", "ON", "OR", "AS", "IF", "AM", "BE"
}

BAD_WORDS = {
    "ee", "ig", "|g", "nsa", "aas", "wal", "las", "td",
    "ar", "tn", "ali", "kas", "wee", "wey", "asa", "re",
    "f3", "ns", "aw", "gegeous"
}


# ==============================
# PRONUNCIATION FIXES
# ==============================

def fix_pronunciation(text):
    fixes = {
        "Rize-san": "Ree-zay sahn",
        "RIZE-SAN": "Ree-zay sahn",
        "Rize": "Ree-zay",
        "RIZE": "Ree-zay",
        "Kaneki": "Kah-neh-kee",
        "KANEKI": "Kah-neh-kee",
        "Touka": "Toh-kah",
        "TOUKA": "Toh-kah",
        "Aogiri": "Ah-oh-gee-ree",
        "AOGIRI": "Ah-oh-gee-ree",
    }

    for wrong, fixed in sorted(fixes.items(), key=lambda item: len(item[0]), reverse=True):
        text = text.replace(wrong, fixed)

    # Context fixes for "live"
    # TTS often reads all-caps LIVE like "live on YouTube".
    # Use \s+ so it still works when OCR text has line breaks like REALLY\nLIVE.
    live_context_patterns = [
        r"\bREALLY\s+LIVE\b",
        r"\bDO\s+YOU\s+LIVE\b",
        r"\bYOU\s+LIVE\b",
        r"\bI\s+LIVE\b",
        r"\bTO\s+LIVE\b",
        r"\bWANT\s+TO\s+LIVE\b",
        r"\bLIVE\s+THINKING\b",
    ]

    for pattern in live_context_patterns:
        text = re.sub(
            pattern,
            lambda m: re.sub(r"\bLIVE\b", "liv", m.group(0), flags=re.IGNORECASE),
            text,
            flags=re.IGNORECASE,
        )

    return text


# ==============================
# IMAGE PREPROCESSING
# ==============================

def preprocess(img):
    """
    Makes manga text easier for OCR:
    - grayscale
    - increase contrast
    - upscale small text
    """
    img = ImageOps.grayscale(img)
    img = ImageEnhance.Contrast(img).enhance(2.5)

    scale = 2
    img = img.resize((img.width * scale, img.height * scale))

    return img


# ==============================
# OCR CLEANING
# ==============================

def normalize_token(raw):
    """
    Cleans individual OCR words/tokens.
    """
    raw = raw.strip()

    # Tesseract often reads capital I as a vertical bar.
    if raw in {"|", "l", "I"}:
        return "I"

    token = raw.strip(".,!?\"'“”‘’()[]{}\\/—-_~")

    if not token:
        return ""

    lower = token.lower()

    if lower in BAD_WORDS:
        return ""

    replacements = {
        "S07": "SO?",
        "S0?": "SO?",
        "$0?": "SO?",
        "507": "SO?",
        "YOu": "YOU",
        "you": "YOU",
    }

    if token in replacements:
        return replacements[token]

    # Restore punctuation if it was stripped.
    if raw.endswith("?") and not token.endswith("?"):
        token += "?"

    if raw.endswith(",") and not token.endswith(","):
        token += ","

    if raw.endswith("...") and not token.endswith("..."):
        token += "..."

    return token


def clean_bubble_text(text):
    """
    Cleans full speech bubble text after OCR grouping.
    """
    replacements = {
        "YOu": "YOU",
        "S07": "SO?",
        "S0?": "SO?",
        "$0?": "SO?",
        "507": "SO?",
        "INSTRUC-\nTIONS?": "INSTRUCTIONS?",
        "INSTRUC\nTIONS?": "INSTRUCTIONS?",
        "INSTRUC- TIONS?": "INSTRUCTIONS?",
        "INSTRUC TIONS?": "INSTRUCTIONS?",
    }

    for bad, good in replacements.items():
        text = text.replace(bad, good)

    # Join hyphenated line breaks.
    text = text.replace("-\n", "")

    # Clean repeated spaces/newlines.
    text = re.sub(r"\n+", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)

    # If OCR missed the capital I in "I WONDER".
    text = re.sub(r"(?m)^WONDER$", "I WONDER", text)

    return text.strip()


def is_good_bubble(text):
    """
    Rejects garbage OCR bubbles before speaking.
    """
    if not text:
        return False

    words = re.sub(r"[^A-Za-z ]", " ", text).upper().split()

    if not words:
        return False

    junk_only = {
        "I", "IT", "AS", "RE", "NS", "EE", "KAS", "ASA", "WEY", "WEE"
    }

    if set(words).issubset(junk_only):
        return False

    letters = sum(c.isalpha() for c in text)

    if letters < 4:
        return False

    symbols = sum(
        not c.isalnum() and not c.isspace() and c not in "?!.',\"“”"
        for c in text
    )

    if symbols > letters * 0.4:
        return False

    lower = text.lower()
    banned_phrases = [
        "tokyo ghoul",
        "tokyoghoul",
        "chapter",
        "manga online",
    ]

    if any(phrase in lower for phrase in banned_phrases):
        return False

    # Reject incomplete page-title / character-label OCR near the bottom of pages.
    compact = re.sub(r"[^A-Za-z0-9]", "", text).upper()
    bad_fragments = {
        "KANEK",
        "KANEKI",
        "062",
        "0062",
    }

    if compact in bad_fragments:
        return False

    return True


# ==============================
# OCR LINE DETECTION
# ==============================

def get_ocr_lines(img):
    """
    Runs OCR and returns detected lines with bounding boxes.
    """
    config = "--oem 3 --psm 11"

    data = pytesseract.image_to_data(
        img,
        lang="eng",
        config=config,
        output_type=pytesseract.Output.DICT
    )

    grouped = {}

    for i, raw_word in enumerate(data["text"]):
        raw_word = raw_word.strip()

        if not raw_word:
            continue

        try:
            conf = float(data["conf"][i])
        except Exception:
            continue

        if conf < MIN_CONF:
            continue

        word = normalize_token(raw_word)

        if not word:
            continue

        plain_word = word.strip(".,!?\"'“”‘’()[]{}\\/—-_~")
        letters = sum(c.isalpha() for c in plain_word)

        if letters == 0:
            continue

        if len(plain_word) <= 2 and plain_word.upper() not in VALID_SHORT_WORDS:
            continue

        key = (
            data["block_num"][i],
            data["par_num"][i],
            data["line_num"][i],
        )

        if key not in grouped:
            grouped[key] = []

        grouped[key].append({
            "text": word,
            "x": data["left"][i],
            "y": data["top"][i],
            "w": data["width"][i],
            "h": data["height"][i],
        })

    lines = []

    for words in grouped.values():
        words = sorted(words, key=lambda w: w["x"])

        text = " ".join(w["text"] for w in words)
        text = re.sub(r"\s+", " ", text).strip()

        if not text:
            continue

        x1 = min(w["x"] for w in words)
        y1 = min(w["y"] for w in words)
        x2 = max(w["x"] + w["w"] for w in words)
        y2 = max(w["y"] + w["h"] for w in words)

        if sum(c.isalpha() for c in text) < 2:
            continue

        lines.append({
            "text": text,
            "x1": x1,
            "y1": y1,
            "x2": x2,
            "y2": y2,
            "cx": (x1 + x2) / 2,
            "cy": (y1 + y2) / 2,
        })

    return lines


# ==============================
# GROUP LINES INTO BUBBLES
# ==============================

def group_lines_into_bubbles(lines):
    """
    Groups nearby OCR lines into speech bubbles.
    """
    lines = sorted(lines, key=lambda l: (l["y1"], l["x1"]))

    bubbles = []

    for line in lines:
        best_bubble = None
        best_score = float("inf")

        for bubble in bubbles:
            bx1 = min(l["x1"] for l in bubble)
            by1 = min(l["y1"] for l in bubble)
            bx2 = max(l["x2"] for l in bubble)
            by2 = max(l["y2"] for l in bubble)
            bcx = (bx1 + bx2) / 2

            vertical_gap = line["y1"] - by2
            x_distance = abs(line["cx"] - bcx)

            # Same speech bubble usually has similar center x
            # and the next line appears below the previous line.
            if -25 <= vertical_gap <= 90 and x_distance <= 170:
                score = abs(vertical_gap) + x_distance

                if score < best_score:
                    best_score = score
                    best_bubble = bubble

        if best_bubble is None:
            bubbles.append([line])
        else:
            best_bubble.append(line)

    bubble_objs = []

    for bubble in bubbles:
        bubble = sorted(bubble, key=lambda l: l["y1"])

        text = "\n".join(l["text"] for l in bubble)
        text = clean_bubble_text(text)

        x1 = min(l["x1"] for l in bubble)
        y1 = min(l["y1"] for l in bubble)
        x2 = max(l["x2"] for l in bubble)
        y2 = max(l["y2"] for l in bubble)

        if not is_good_bubble(text):
            continue

        bubble_objs.append({
            "text": text,
            "x1": x1,
            "y1": y1,
            "x2": x2,
            "y2": y2,
            "cx": (x1 + x2) / 2,
            "cy": (y1 + y2) / 2,
        })

    return bubble_objs


# ==============================
# SORT BUBBLES IN MANGA ORDER
# ==============================

def sort_bubbles_reading_order(bubbles, page_height):
    """
    Sorts detected speech bubbles:
    - row by row
    - right-to-left inside each row for manga
    """
    if not bubbles:
        return []

    row_tolerance = page_height * 0.08

    rows = []

    for bubble in sorted(bubbles, key=lambda b: b["y1"]):
        placed = False

        for row in rows:
            row_y = min(b["y1"] for b in row)

            if abs(bubble["y1"] - row_y) <= row_tolerance:
                row.append(bubble)
                placed = True
                break

        if not placed:
            rows.append([bubble])

    sorted_bubbles = []

    for row in rows:
        if READING_DIRECTION == "rtl":
            row = sorted(row, key=lambda b: b["x1"], reverse=True)
        else:
            row = sorted(row, key=lambda b: b["x1"])

        sorted_bubbles.extend(row)

    return sorted_bubbles


# ==============================
# DEBUG IMAGE
# ==============================

def draw_debug(img, bubbles):
    """
    Saves image with red boxes around detected bubbles.
    """
    debug = img.convert("RGB")
    draw = ImageDraw.Draw(debug)

    for idx, bubble in enumerate(bubbles, start=1):
        box = (bubble["x1"], bubble["y1"], bubble["x2"], bubble["y2"])
        draw.rectangle(box, outline="red", width=4)
        draw.text(
            (bubble["x1"], max(0, bubble["y1"] - 30)),
            str(idx),
            fill="red"
        )

    debug.save("debug_detected_bubbles.png")


# ==============================
# SPEECH
# ==============================

async def edge_speak_async(text):
    """
    Speaks text using Microsoft Edge neural voices.
    """
    tts_text = fix_pronunciation(text)

    if PRINT_TTS_TEXT:
        print("\nTTS TEXT:")
        print(tts_text)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
        audio_path = f.name

    communicate = edge_tts.Communicate(
        text=tts_text,
        voice=VOICE,
        rate=RATE,
        volume=VOLUME
    )

    await communicate.save(audio_path)

    subprocess.run(["afplay", audio_path])
    os.remove(audio_path)


def speak(text):
    """
    Wrapper so the rest of the code can just call speak(text).
    """
    if not SPEAK_OUT_LOUD:
        return

    if text.strip():
        asyncio.run(edge_speak_async(text))


# ==============================
# MAIN
# ==============================

def main():
    if not os.path.exists(IMG_PATH):
        print(f"Could not find {IMG_PATH}")
        print("Put your manga screenshot in this folder and name it image.png")
        return

    original = Image.open(IMG_PATH)
    img = preprocess(original)

    lines = get_ocr_lines(img)
    bubbles = group_lines_into_bubbles(lines)
    bubbles = sort_bubbles_reading_order(bubbles, img.height)

    if SAVE_DEBUG_IMAGE:
        draw_debug(img, bubbles)
        print("Saved debug image: debug_detected_bubbles.png")

    print("\nDETECTED TEXT IN READING ORDER:")
    print("================================")

    final_text = []

    for i, bubble in enumerate(bubbles, start=1):
        text = clean_bubble_text(bubble["text"])

        if not is_good_bubble(text):
            continue

        final_text.append(text)

        print(f"\n[{i}]")
        print(text)

        speak(text)

    print("\n\nFINAL COMBINED TEXT:")
    print("================================")
    print("\n\n".join(final_text))


if __name__ == "__main__":
    main()