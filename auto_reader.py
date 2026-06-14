from PIL import Image, ImageOps, ImageEnhance, ImageDraw
import pytesseract
import subprocess
import re
import asyncio
import edge_tts
import tempfile
import os
import time
import mss
import cv2
import numpy as np

try:
    from pynput import keyboard
except ImportError:
    keyboard = None


# ==============================
# SETTINGS
# ==============================

IMG_PATH = "image.png"

# INPUT_MODE options:
# "image" = read IMG_PATH once
# "screen" = capture a fixed region of your live screen
INPUT_MODE = "screen"

# Capture a broad browser/manga area. Auto-crop will find the manga page inside it.
CAPTURE_REGION = {
    "left": 300,
    "top": 120,
    "width": 900,
    "height": 1200,
}

# If True, tries to crop the manga page out of the broader screen capture.
AUTO_CROP_MANGA_PAGE = True
SAVE_AUTO_CROP_DEBUG = False

# Seconds between captures if auto-scan mode is used.
CAPTURE_INTERVAL_SECONDS = 0.8

# Saves live capture as live_capture.png for debugging.
SAVE_LIVE_CAPTURE = False

# If True, run mouse-position helper instead of OCR.
CALIBRATE_REGION = False

# Global hotkey mode works even when Terminal is not focused.
# Requires: python -m pip install pynput
# macOS also requires Accessibility permission for Terminal/VS Code.
USE_GLOBAL_HOTKEY = True
READ_HOTKEY = "r"

# Fallback mode: press Enter in Terminal to read once.
READ_ON_ENTER_ONLY = False

# Pressing r while speaking stops current audio and restarts with current screen.
INTERRUPT_AND_RESTART_ON_HOTKEY = True

# Manga is usually right-to-left.
READING_DIRECTION = "rtl"

# Lower = catches more text but more garbage.
# Higher = cleaner but may miss tiny words like "SO?"
MIN_CONF = 25

# Edge neural voice settings.
# Good voices:
# en-US-AriaNeural
# en-US-GuyNeural
# en-US-JennyNeural
# en-US-DavisNeural
VOICE = "en-US-AriaNeural"
RATE = "+8%"
VOLUME = "+0%"

# Saves debug image with detected OCR boxes.
SAVE_DEBUG_IMAGE = False

# Speaks text out loud.
SPEAK_OUT_LOUD = True

# True = one TTS call for whole page.
# False = bubble-by-bubble; starts faster and interrupts cleaner.
SPEAK_COMBINED_TEXT = False

# Prints final TTS text after pronunciation fixes.
PRINT_TTS_TEXT = False

# Avoid repeating same screen/dialogue.
SKIP_REPEATED_TEXT = True

# If True, live mode exits after one read.
EXIT_AFTER_ONE_READ = False


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
        "Rize-san": "Ree zay sawn",
        "RIZE-SAN": "Ree zay sawn",
        "RIZE SAN": "Ree zay sawn",
        "RIZE, SAN": "Ree zay sawn",
        "Rize": "Ree zay",
        "RIZE": "Ree zay",
        "Kaneki": "Kah neh kee",
        "KANEKI": "Kah neh kee",
        "Touka": "Toh kah",
        "TOUKA": "Toh kah",
        "Aogiri": "Ah oh gee ree",
        "AOGIRI": "Ah oh gee ree",
    }

    for wrong, fixed in sorted(fixes.items(), key=lambda item: len(item[0]), reverse=True):
        text = text.replace(wrong, fixed)

    text = re.sub(
        r"\bRIZE\s*[-,]?\s*SAN\b",
        "Ree zay sawn",
        text,
        flags=re.IGNORECASE,
    )

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
# IMAGE / CROP
# ==============================

def auto_crop_manga_page(img):
    """
    Finds the main manga page inside a larger screen capture.
    This helps if the manga image moves around or page sizes change.
    """
    arr = np.array(img.convert("RGB"))
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)

    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 40, 120)

    kernel = np.ones((15, 15), np.uint8)
    dilated = cv2.dilate(edges, kernel, iterations=2)

    contours, _ = cv2.findContours(
        dilated,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    if not contours:
        return img

    h, w = gray.shape
    candidates = []

    for contour in contours:
        x, y, cw, ch = cv2.boundingRect(contour)
        area = cw * ch

        if area < (w * h * 0.05):
            continue

        aspect = ch / max(cw, 1)

        # Normal manga pages are tall-ish. This still allows wide-ish panels.
        if aspect < 0.75:
            continue

        if cw < w * 0.18 or ch < h * 0.25:
            continue

        # Avoid grabbing very thin UI bars.
        if cw < 250 or ch < 300:
            continue

        candidates.append((area, x, y, cw, ch))

    if not candidates:
        return img

    _, x, y, cw, ch = max(candidates, key=lambda c: c[0])

    pad = 20
    x1 = max(0, x - pad)
    y1 = max(0, y - pad)
    x2 = min(w, x + cw + pad)
    y2 = min(h, y + ch + pad)

    cropped = img.crop((x1, y1, x2, y2))

    if SAVE_AUTO_CROP_DEBUG:
        cropped.save("auto_cropped_manga.png")

        debug = arr.copy()
        cv2.rectangle(debug, (x1, y1), (x2, y2), (255, 0, 0), 4)
        Image.fromarray(debug).save("auto_crop_debug.png")

    return cropped


def preprocess(img):
    """
    Makes manga text easier for OCR.
    Keep scale=2 for accuracy. Lower scale is faster but worse.
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
    raw = raw.strip()

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

    if raw.endswith("?") and not token.endswith("?"):
        token += "?"

    if raw.endswith(",") and not token.endswith(","):
        token += ","

    if raw.endswith("...") and not token.endswith("..."):
        token += "..."

    return token


def clean_bubble_text(text):
    replacements = {
        "YOu": "YOU",
        "S07": "SO?",
        "S0?": "SO?",
        "$0?": "SO?",
        "507": "SO?",
        "YOU RE": "YOU'RE",
        "YOURE": "YOU'RE",
        "DONT": "DON'T",
        "CANT": "CAN'T",
        "WONT": "WON'T",
        "INSTRUC-\nTIONS?": "INSTRUCTIONS?",
        "INSTRUC\nTIONS?": "INSTRUCTIONS?",
        "INSTRUC- TIONS?": "INSTRUCTIONS?",
        "INSTRUC TIONS?": "INSTRUCTIONS?",
    }

    for bad, good in replacements.items():
        text = text.replace(bad, good)

    text = text.replace("-\n", "")
    text = re.sub(r"\n+", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"(?m)^WONDER$", "I WONDER", text)

    return text.strip()


def is_good_bubble(text):
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
# OCR DETECTION
# ==============================

def get_ocr_lines(img):
    config = "--oem 3 --psm 11"

    data = pytesseract.image_to_data(
        img,
        lang="eng",
        config=config,
        output_type=pytesseract.Output.DICT,
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


def group_lines_into_bubbles(lines):
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


def sort_bubbles_reading_order(bubbles, page_height):
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


def draw_debug(img, bubbles):
    debug = img.convert("RGB")
    draw = ImageDraw.Draw(debug)

    for idx, bubble in enumerate(bubbles, start=1):
        box = (bubble["x1"], bubble["y1"], bubble["x2"], bubble["y2"])
        draw.rectangle(box, outline="red", width=4)
        draw.text(
            (bubble["x1"], max(0, bubble["y1"] - 30)),
            str(idx),
            fill="red",
        )

    debug.save("debug_detected_bubbles.png")


# ==============================
# SPEECH
# ==============================

async def edge_speak_async(text, should_cancel=None, process_holder=None):
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
        volume=VOLUME,
    )

    await communicate.save(audio_path)

    if should_cancel is not None and should_cancel():
        if os.path.exists(audio_path):
            os.remove(audio_path)
        return

    proc = subprocess.Popen(["afplay", audio_path])

    if process_holder is not None:
        process_holder["process"] = proc

    try:
        while proc.poll() is None:
            if should_cancel is not None and should_cancel():
                try:
                    proc.terminate()
                    proc.wait(timeout=0.2)
                except subprocess.TimeoutExpired:
                    proc.kill()
                break

            await asyncio.sleep(0.05)

    finally:
        if process_holder is not None and process_holder.get("process") is proc:
            process_holder["process"] = None

        if os.path.exists(audio_path):
            os.remove(audio_path)


def speak(text, should_cancel=None, process_holder=None):
    if not SPEAK_OUT_LOUD:
        return

    if text.strip():
        asyncio.run(edge_speak_async(
            text,
            should_cancel=should_cancel,
            process_holder=process_holder,
        ))


# ==============================
# SCREEN CAPTURE / READING
# ==============================

def calibrate_region_helper():
    try:
        import pyautogui
    except ImportError:
        print("Install pyautogui first:")
        print("python -m pip install pyautogui")
        return

    print("Move your mouse to the TOP-LEFT of the manga/browser reading area, then wait.")
    time.sleep(4)
    x1, y1 = pyautogui.position()
    print(f"Top-left: x={x1}, y={y1}")

    print("Move your mouse to the BOTTOM-RIGHT of the manga/browser reading area, then wait.")
    time.sleep(4)
    x2, y2 = pyautogui.position()
    print(f"Bottom-right: x={x2}, y={y2}")

    left = min(x1, x2)
    top = min(y1, y2)
    width = abs(x2 - x1)
    height = abs(y2 - y1)

    print("\nUse this CAPTURE_REGION:")
    print("CAPTURE_REGION = {")
    print(f'    "left": {left},')
    print(f'    "top": {top},')
    print(f'    "width": {width},')
    print(f'    "height": {height},')
    print("}")


def capture_screen_region():
    with mss.MSS() as sct:
        shot = sct.grab(CAPTURE_REGION)
        img = Image.frombytes("RGB", shot.size, shot.rgb)

    if SAVE_LIVE_CAPTURE:
        img.save("live_capture.png")

    return img


def read_page_image(original):
    if AUTO_CROP_MANGA_PAGE:
        original = auto_crop_manga_page(original)

    img = preprocess(original)

    lines = get_ocr_lines(img)
    bubbles = group_lines_into_bubbles(lines)
    bubbles = sort_bubbles_reading_order(bubbles, img.height)

    if SAVE_DEBUG_IMAGE:
        draw_debug(img, bubbles)
        print("Saved debug image: debug_detected_bubbles.png")

    final_text = []

    for bubble in bubbles:
        text = clean_bubble_text(bubble["text"])

        if not is_good_bubble(text):
            continue

        final_text.append(text)

    return final_text


def run_image_mode():
    if not os.path.exists(IMG_PATH):
        print(f"Could not find {IMG_PATH}")
        print("Put your manga screenshot in this folder and name it image.png")
        return

    original = Image.open(IMG_PATH)
    final_text = read_page_image(original)

    print("\nDETECTED TEXT IN READING ORDER:")
    print("================================")

    for i, text in enumerate(final_text, start=1):
        print(f"\n[{i}]")
        print(text)

    combined_text = "\n\n".join(final_text)

    if SPEAK_COMBINED_TEXT:
        speak(combined_text)
    else:
        for text in final_text:
            speak(text)

    print("\n\nFINAL COMBINED TEXT:")
    print("================================")
    print(combined_text)


def run_screen_mode():
    print("Live screen mode started.")
    print("Press Ctrl+C to stop.")
    print("Current CAPTURE_REGION:", CAPTURE_REGION)

    use_global_hotkey = USE_GLOBAL_HOTKEY and keyboard is not None
    use_enter_mode = READ_ON_ENTER_ONLY or not use_global_hotkey

    if use_global_hotkey:
        print(f'Global hotkey mode: press "{READ_HOTKEY}" anywhere to capture/read.')
        print("Pressing the hotkey again interrupts current speech and restarts.")
        print("If the hotkey does not trigger, enable Accessibility permission for Terminal/VS Code.")
    elif use_enter_mode:
        print("Enter fallback mode: focus this terminal and press Enter to capture/read.")
        if USE_GLOBAL_HOTKEY and keyboard is None:
            print("pynput is not installed, so global hotkey mode is unavailable.")
    else:
        print("Auto-scan mode is on.")

    last_combined = ""
    read_requested = False
    latest_request_id = 0
    active_audio = {"process": None}

    def request_read():
        nonlocal read_requested, latest_request_id

        latest_request_id += 1
        read_requested = True

        if INTERRUPT_AND_RESTART_ON_HOTKEY:
            proc = active_audio.get("process")
            if proc is not None and proc.poll() is None:
                try:
                    proc.terminate()
                except Exception:
                    pass

    def on_press(key):
        try:
            if key.char and key.char.lower() == READ_HOTKEY.lower():
                request_read()
        except AttributeError:
            pass

    listener = None

    if use_global_hotkey:
        listener = keyboard.Listener(on_press=on_press)
        listener.start()

    try:
        while True:
            if use_global_hotkey:
                if not read_requested:
                    time.sleep(0.03)
                    continue

                read_requested = False
                current_request_id = latest_request_id

            elif use_enter_mode:
                print("\nFocus this terminal, then press Enter to read current page/region...", flush=True)
                input()
                latest_request_id += 1
                current_request_id = latest_request_id

            else:
                latest_request_id += 1
                current_request_id = latest_request_id

            print("\nCapturing current screen region...")
            original = capture_screen_region()

            print("Running OCR...")
            final_text = read_page_image(original)
            combined = "\n\n".join(final_text).strip()

            if INTERRUPT_AND_RESTART_ON_HOTKEY and current_request_id != latest_request_id:
                print("\nNew hotkey detected during OCR. Discarding old result and restarting.")
                continue

            if not combined:
                print("\nNo readable text detected in region.")

                if not use_global_hotkey and not use_enter_mode:
                    time.sleep(CAPTURE_INTERVAL_SECONDS)

                continue

            if SKIP_REPEATED_TEXT and combined == last_combined:
                print("\nSame text as last capture. Skipping speech.")

                if not use_global_hotkey and not use_enter_mode:
                    time.sleep(CAPTURE_INTERVAL_SECONDS)

                continue

            print("\nDETECTED LIVE TEXT:")
            print("================================")

            for i, text in enumerate(final_text, start=1):
                print(f"\n[{i}]")
                print(text)

            def should_cancel():
                return (
                    INTERRUPT_AND_RESTART_ON_HOTKEY
                    and current_request_id != latest_request_id
                )

            was_interrupted = False

            if SPEAK_COMBINED_TEXT:
                speak(
                    combined,
                    should_cancel=should_cancel,
                    process_holder=active_audio,
                )
                if should_cancel():
                    was_interrupted = True
            else:
                for text in final_text:
                    if should_cancel():
                        was_interrupted = True
                        break

                    speak(
                        text,
                        should_cancel=should_cancel,
                        process_holder=active_audio,
                    )

                    if should_cancel():
                        was_interrupted = True
                        break

            if was_interrupted:
                print("\nCurrent speech was interrupted. Restarting with newest screen.")
                continue

            last_combined = combined

            print("\nFinished speaking current screen. Press hotkey again for the next one.")

            if EXIT_AFTER_ONE_READ:
                print("\nFinished one read. Exiting.")
                break

            if not use_global_hotkey and not use_enter_mode:
                time.sleep(CAPTURE_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\nStopped live screen mode.")
    finally:
        proc = active_audio.get("process")
        if proc is not None and proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass

        if listener is not None:
            listener.stop()


# ==============================
# MAIN
# ==============================

def main():
    if CALIBRATE_REGION:
        calibrate_region_helper()
        return

    if INPUT_MODE == "image":
        run_image_mode()
    elif INPUT_MODE == "screen":
        run_screen_mode()
    else:
        print(f"Unknown INPUT_MODE: {INPUT_MODE}")
        print('Use INPUT_MODE = "image" or INPUT_MODE = "screen"')


if __name__ == "__main__":
    main()