import re
import cv2
import numpy as np
import easyocr

_reader = None


def get_reader() -> easyocr.Reader:
    global _reader
    if _reader is None:
        print("   [OCR] Chargement du modele...")
        _reader = easyocr.Reader(["fr"], gpu=False)  # fr seul = chargement + inference plus rapides
    return _reader


def _ocr_pass(reader, img) -> str:
    results = reader.readtext(img, detail=1, paragraph=False)
    if not results:
        return ""
    results.sort(key=lambda r: r[0][0][1])  # tri vertical
    lines = [text for (_, text, conf) in results if conf > 0.15]
    return "\n".join(lines)


def extract_raw_text(img: np.ndarray) -> str:
    """
    OCR a 0 d'abord (cas normal d'un ticket a l'endroit).
    On ne teste les autres orientations QUE si le resultat a 0 est mauvais.
    """
    reader = get_reader()

    text = _ocr_pass(reader, img)
    if _score(text) >= 15:        # ticket lisible a l'endroit -> on s'arrete la
        return text

    # Fallback : l'image est peut-etre tournee
    best_text, best_score = text, _score(text)
    for flag in (cv2.ROTATE_90_CLOCKWISE, cv2.ROTATE_180, cv2.ROTATE_90_COUNTERCLOCKWISE):
        t = _ocr_pass(reader, cv2.rotate(img, flag))
        s = _score(t)
        if s > best_score:
            best_text, best_score = t, s
    return best_text


def _score(text: str) -> float:
    clean = re.sub(r'[^A-Za-zÀ-ÿ0-9]', '', text)
    score = len(clean) * 0.1
    if re.search(r'\b\d{5}\b', text):
        score += 50
    if re.search(r'\b(rue|avenue|boulevard|route|place|chemin|impasse)\b', text, re.IGNORECASE):
        score += 30
    return score