from PIL import Image, ImageOps, ImageEnhance
import pytesseract
import subprocess
import re
import os

img_path = "image.png"

VALID_SHORT_WORDS = {
    "I", "A", "MY", "ME", "SO", "DO", "NO", "TO", "OF", "IN", "IS", "IT",
    "HE", "WE", "US", "UP", "GO", "ON", "OR", "AS", "IF", "AM", "BE"
}

BAD_WORDS = {
    "ee", "ig", "|g", "nsa", "aas", "wal", "las", "td", "ar", "tn"
}

# These chunks are based on your current full manga-page screenshot.
# Format: name, left %, top %, right %, bottom %
CHUNKS = [
    # top panel, manga right-to-left
    ("top_right_rize",      0.78, 0.09, 1.00, 0.40),
    ("top_middle_quote",   0.60, 0.09, 0.82, 0.40),
    ("top_left_question",  0.08, 0.09, 0.35, 0.40),

    # middle row, manga right-to-left
    ("middle_right_kaneki", 0.50, 0.40, 1.00, 0.82),
    ("middle_center_rize", 0.38, 0.40, 0.58, 0.82),
    ("middle_left_funeral",0.02, 0.40, 0.44, 0.82),

    # keep bottom skipped for now
]

def preprocess(img):
    img = ImageOps.grayscale(img)
    img = ImageEnhance.Contrast(img).enhance(2.5)

    scale = 2
    img = img.resize((img.width * scale, img.height * scale))

    return img

def clean_word(word):
    return word.strip(".,!?\"'“”‘’()[]{}|\\/—-_~")

def ocr_image(img):
    img = preprocess(img)

    config = "--oem 3 --psm 11"

    data = pytesseract.image_to_data(
        img,
        lang="eng",
        config=config,
        output_type=pytesseract.Output.DICT
    )

    words_by_line = {}

    for i, word in enumerate(data["text"]):
        word = word.strip()
        if not word:
            continue

        try:
            conf = float(data["conf"][i])
        except:
            continue

        if conf < 45:
            continue

        fixed = clean_word(word)
        lower = fixed.lower()

        if lower in BAD_WORDS:
            continue

        letters = sum(c.isalpha() for c in fixed)
        if letters == 0:
            continue

        if len(fixed) <= 2 and fixed.upper() not in VALID_SHORT_WORDS:
            continue

        key = (
            data["block_num"][i],
            data["par_num"][i],
            data["line_num"][i],
        )

        if key not in words_by_line:
            words_by_line[key] = []

        words_by_line[key].append(word)

    lines = []

    for key in sorted(words_by_line.keys()):
        line = " ".join(words_by_line[key])
        line = re.sub(r"\s+", " ", line).strip()

        lower = line.lower()

        if "tokyo" in lower or "ghoul" in lower:
            continue

        alpha_count = sum(c.isalpha() for c in line)
        if alpha_count < 2:
            continue

        lines.append(line)

    return "\n".join(lines).strip()

def speak(text):
    if text:
        subprocess.run(["say", "-v", "Samantha", text])

def main():
    page = Image.open(img_path)
    w, h = page.size

    os.makedirs("debug_chunks", exist_ok=True)

    full_text = []

    for name, lx, ty, rx, by in CHUNKS:
        box = (
            int(w * lx),
            int(h * ty),
            int(w * rx),
            int(h * by),
        )

        chunk = page.crop(box)
        chunk.save(f"debug_chunks/{name}.png")

        text = ocr_image(chunk)

        print("\n==============================")
        print(name)
        print("==============================")
        print(text)

        if text:
            full_text.append(text)
            speak(text)

    print("\n\nFINAL COMBINED TEXT:")
    print("==============================")
    print("\n\n".join(full_text))

if __name__ == "__main__":
    main()