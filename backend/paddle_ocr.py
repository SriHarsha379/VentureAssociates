import pytesseract
import cv2
import numpy as np
import io
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = "/opt/homebrew/bin/tesseract"

def extract_text(file_bytes):

    image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    img = np.array(image)

    # upscale
    img = cv2.resize(img, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    th = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31, 2
    )

    config = "--oem 3 --psm 6"

    text = pytesseract.image_to_string(th, config=config)

    return text
