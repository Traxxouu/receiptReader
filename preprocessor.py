import cv2
import numpy as np


def preprocess_image(image_path: str) -> np.ndarray:
    """
    Charge et prépare l'image pour EasyOCR.
    EasyOCR gère la rotation nativement donc on touche le moins possible.
    On fait juste un redimensionnement si l'image est trop grande.
    """
    img = cv2.imread(image_path)

    if img is None:
        raise ValueError(f"Impossible de lire l'image : {image_path}")

    # Redimensionnement si trop grande (EasyOCR est lent sur les très grandes images)
    h, w = img.shape[:2]
    max_dim = 2000
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

    return img
