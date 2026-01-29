import pytesseract
from PIL import Image
import io
from pdf2image import convert_from_bytes
import cv2
import numpy as np


def preprocess_image(pil_img):
    """
    Robust OCR preprocessing:
    - Safe grayscale conversion
    - Contrast enhancement (CLAHE)
    - Adaptive thresholding
    """

    img = np.array(pil_img)

    # 1️⃣ Ensure grayscale safely
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img  # already grayscale

    # 2️⃣ Contrast enhancement (CLAHE)
    clahe = cv2.createCLAHE(
        clipLimit=3.0,
        tileGridSize=(8, 8)
    )
    gray = clahe.apply(gray)

    # 3️⃣ Adaptive threshold (better than fixed 150)
    thresh = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        2
    )

    return thresh


def ocr_image(pil_img):
    processed = preprocess_image(pil_img)

    return pytesseract.image_to_string(
        processed,
        lang="eng",
        config="--oem 3 --psm 6"
    )


def run_ocr(file_bytes, filename: str):
    text = ""

    if filename.lower().endswith(".pdf"):
        pages = convert_from_bytes(file_bytes, dpi=300)

        for i, page in enumerate(pages):
            page_text = ocr_image(page)
            text += f"\n--- PAGE {i+1} ---\n{page_text}"

    else:
        image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        text = ocr_image(image)

    return text
