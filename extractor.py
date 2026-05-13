import re
import cv2
import numpy as np
import easyocr

_reader = None


def get_reader() -> easyocr.Reader:
    global _reader
    if _reader is None:
        print("   [OCR] Chargement du modele...")
        _reader = easyocr.Reader(["fr", "en"], gpu=False)
    return _reader


def extract_raw_text(img: np.ndarray) -> str:
    """
    Extrait tout le texte brut de l'image.
    Teste 4 orientations et garde la meilleure.
    Retourne le texte brut en une seule string.
    """
    reader = get_reader()

    best_text = ""
    best_score = -1

    for angle in [0, 90, 180, 270]:
        if angle == 0:
            rotated = img
        elif angle == 90:
            rotated = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        elif angle == 180:
            rotated = cv2.rotate(img, cv2.ROTATE_180)
        else:
            rotated = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)

        results = reader.readtext(rotated, detail=1, paragraph=False)
        if not results:
            continue

        # Trier par position verticale
        results.sort(key=lambda r: r[0][0][1])
        lines = [text for (_, text, conf) in results if conf > 0.15]
        text = "\n".join(lines)

        score = _score(text)
        if score > best_score:
            best_score = score
            best_text = text

    return best_text


def _score(text: str) -> float:
    """Score le texte pour choisir la meilleure orientation."""
    clean = re.sub(r'[^A-Za-zÀ-ÿ0-9]', '', text)
    score = len(clean) * 0.1
    if re.search(r'\b\d{5}\b', text):
        score += 50
    if re.search(r'\b(rue|avenue|boulevard|route|place|chemin|impasse)\b', text, re.IGNORECASE):
        score += 30
    return score
