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

    # Redimensionnement si trop grande
    h, w = img.shape[:2]
    max_dim = 2000
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

    # Convertir en niveaux de gris
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Amélioration locale du contraste
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    # Denoising
    denoised = cv2.fastNlMeansDenoising(enhanced, None, h=10, templateWindowSize=7, searchWindowSize=21)

    # Seuil adaptatif pour renforcer le texte
    th = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                               cv2.THRESH_BINARY, 15, 8)

    # Retourner une image 3-canaux (beaucoup d'APIs OCR attendent BGR)
    processed = cv2.cvtColor(th, cv2.COLOR_GRAY2BGR)

    return processed
