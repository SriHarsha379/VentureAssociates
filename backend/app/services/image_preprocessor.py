import cv2
import numpy as np

def enhance_image(image_bytes: bytes) -> bytes:
    # Convert bytes → numpy array
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        return image_bytes  # fallback

    # 1. Grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 2. Contrast enhancement (CLAHE)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    contrast = clahe.apply(gray)

    # 3. Slight brightness boost
    bright = cv2.convertScaleAbs(contrast, alpha=1.2, beta=15)

    # 4. Adaptive threshold (handles faded text)
    thresh = cv2.adaptiveThreshold(
        bright,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        10
    )

    # Encode back to bytes
    _, encoded = cv2.imencode(".jpg", thresh)
    return encoded.tobytes()
