import pytesseract
from PIL import Image
import io
import cv2
import numpy as np

pytesseract.pytesseract.tesseract_cmd = "/opt/homebrew/bin/tesseract"


def preprocess(img):

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Remove shadows
    dilated = cv2.dilate(gray, np.ones((7,7), np.uint8))
    bg = cv2.medianBlur(dilated, 21)
    diff = 255 - cv2.absdiff(gray, bg)

    # Sharpen
    kernel = np.array([[0,-1,0],[-1,5,-1],[0,-1,0]])
    sharp = cv2.filter2D(diff, -1, kernel)

    # Threshold
    _, th = cv2.threshold(sharp, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)

    return th


def extract_text(file_bytes):
    """Enhanced OCR with better preprocessing"""

    image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    img = np.array(image)

    # Aggressive upscaling for better character recognition
    img = cv2.resize(img, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Remove noise with bilateral filter (preserves edges)
    denoised = cv2.bilateralFilter(gray, 9, 75, 75)

    # Adaptive thresholding works better for varied lighting
    thresh = cv2.adaptiveThreshold(
        denoised, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        21, 10
    )

    # Morphological operations to clean up
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
    cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    # Use PSM 4 for single column of text with varying formats
    config = "--oem 3 --psm 4 -c preserve_interword_spaces=1"

    text = pytesseract.image_to_string(cleaned, config=config)

    return text
