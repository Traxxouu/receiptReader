import cv2
import numpy as np


def preprocess_image(image_path: str) -> np.ndarray:
    """
    Charge et prépare l'image pour l'OCR.
    Stratégie simple et efficace : on touche le moins possible à l'image,
    juste ce qu'il faut pour que Tesseract lise bien.
    """
    img = cv2.imread(image_path)

    if img is None:
        raise ValueError(f"Impossible de lire l'image : {image_path}")

    # Redressement automatique
    img = auto_rotate(img)

    # Agrandissement x2 (Tesseract lit mieux les grandes images)
    img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

    # Conversion en niveaux de gris
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Légère netteté
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharpened = cv2.filter2D(gray, -1, kernel)

    # Binarisation simple d'Otsu (bien meilleure que l'adaptative pour les tickets)
    _, binary = cv2.threshold(sharpened, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return binary


def auto_rotate(img: np.ndarray) -> np.ndarray:
    """
    Détecte l'orientation du texte et redresse l'image automatiquement.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 100, minLineLength=100, maxLineGap=10)

    if lines is None:
        return img

    angles = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        if x2 - x1 != 0:
            angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            # On garde seulement les angles proches de l'horizontal
            if abs(angle) < 45:
                angles.append(angle)

    if not angles:
        return img

    median_angle = np.median(angles)

    if abs(median_angle) < 0.5:
        return img

    h, w = img.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)
    rotated = cv2.warpAffine(img, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    return rotated
