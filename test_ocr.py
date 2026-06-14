from PIL import Image, ImageOps, ImageEnhance
import pytesseract
import subprocess
import re

img_path = "image.png"

VALID_SHORT_WORDS = {
    "I", "A", "MY", "ME", "SO", "DO", "NO", "TO", "OF", "IN", "IS", "IT",
    "HE", "WE", "US", "UP", "GO", "ON", "OR", "AS", "IF", "AM", "BE"
}

BAD_WORDS = {
    "ee", "ig", "|g", "nsa", "aas", "wal", "las", "td"
}

img = Image.open(img_path)

img = ImageOps.grayscale(img)
img = ImageEnhance.Contrast(img).enhance(2.5)

scale = 2
img = img.resize((img.width * scale, img.height * scale))

config = "--oem 3 --psm 11"

data = pytesseract.image_to_data(
    img,
    lang="eng",
    config=config,
    output_type=pytesseract.Output.DICT
)

lines = {}

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

    clean_word = word.strip(".,!?\"'“”‘’()[]{}|\\/—-_~")
    clean_lower = clean_word.lower()

    if clean_lower in BAD_WORDS:
        continue

    letters = sum(c.isalpha() for c in clean_word)

    if letters == 0:
        continue

    if len(clean_word) <= 2 and clean_word.upper() not in VALID_SHORT_WORDS:
        continue

    line_key = (
        data["block_num"][i],
        data["par_num"][i],
        data["line_num"][i],
    )

    if line_key not in lines:
        lines[line_key] = []

    lines[line_key].append(word)

clean_lines = []

for key in sorted(lines.keys()):
    line = " ".join(lines[key])
    line = re.sub(r"\s+", " ", line).strip()

    lower = line.lower()
    if "tokyo" in lower or "ghoul" in lower or "kaneki" in lower and "# 0" in lower:
        continue

    alpha_count = sum(c.isalpha() for c in line)
    if alpha_count < 2:
        continue

    clean_lines.append(line)

clean_text = "\n".join(clean_lines)

print("OCR RESULT:")
print(clean_text)

if clean_text:
    subprocess.run(["say", "-v", "Samantha", clean_text])