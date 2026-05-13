import cv2
import numpy as np


def preprocess_image(image_path: str) -> np.ndarray:
    """
    Charge et prepare l'image pour EasyOCR.
    """
    img = cv2.imread(image_path)

    if img is None:
        raise ValueError(f"Impossible de lire l'image : {image_path}")

    # Redimensionnement si trop grande
    h, w = img.shape[:2]
    if max(h, w) > 2000:
        scale = 2000 / max(h, w)
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    elif max(h, w) < 640:
        scale = 640 / max(h, w)
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    return img
