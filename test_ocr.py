from PIL import Image, ImageOps, ImageEnhance
import pytesseract

img_path = "image.png"

img = Image.open(img_path)

# Basic cleanup helps manga text a lot
img = ImageOps.grayscale(img)
img = ImageEnhance.Contrast(img).enhance(2.0)

text = pytesseract.image_to_string(img, lang="eng")

print("OCR RESULT:")
print(text)