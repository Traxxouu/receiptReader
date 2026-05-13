import re
import numpy as np
import cv2
from typing import Iterable

# Préférence pour PaddleOCR si disponible, sinon fallback sur EasyOCR
try:
    from paddleocr import PaddleOCR
    PADDLE_AVAILABLE = True
except Exception:
    PADDLE_AVAILABLE = False

try:
    import easyocr
    EASY_AVAILABLE = True
except Exception:
    EASY_AVAILABLE = False

_reader = None
_engine = None


def _get_paddle_reader():
    global _reader
    if _reader is None:
        # use_angle_cls helps with rotated text
        try:
            _reader = PaddleOCR(use_angle_cls=True, lang="fr", use_gpu=False)
        except Exception:
            # Certaines versions de PaddleOCR n'acceptent pas use_gpu en kwarg
            _reader = PaddleOCR(use_angle_cls=True, lang="fr")
    return _reader


def _get_easy_reader():
    global _reader
    if _reader is None:
        _reader = easyocr.Reader(["fr", "en"], gpu=False)
    return _reader


def get_reader():
    """Retourne l'instance OCR et fixe le moteur utilisé."""
    global _engine
    if PADDLE_AVAILABLE:
        _engine = "paddle"
        return _get_paddle_reader()
    if EASY_AVAILABLE:
        _engine = "easy"
        return _get_easy_reader()
    raise RuntimeError("Aucun moteur OCR disponible (PaddleOCR ou EasyOCR).")


def extract_text(img: np.ndarray) -> list[tuple]:
    """
    Retourne une liste standardisée de tuples: [(bbox, text, conf), ...]
    Utilise PaddleOCR si présent, sinon EasyOCR.
    """
    reader = get_reader()

    if _engine == "paddle":
        try:
            best = _extract_text_paddle(reader, img)
            # Si l'image est très pauvre, tester des rotations explicites
            if is_mostly_empty(best):
                candidates = [best]

                # deskew candidate
                desk = _deskew_image(img)
                if desk is not None:
                    candidates.append(_extract_text_paddle(reader, desk))

                # rotations
                candidates.append(_extract_text_paddle(reader, cv2.rotate(img, cv2.ROTATE_180)))
                candidates.append(_extract_text_paddle(reader, cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)))
                candidates.append(_extract_text_paddle(reader, cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)))

                # flips
                candidates.append(_extract_text_paddle(reader, cv2.flip(img, 1)))
                candidates.append(_extract_text_paddle(reader, cv2.flip(img, 0)))

                best = max(candidates, key=_score_results)
            return best
        except Exception as e:
            # fallback vers EasyOCR si disponible
            try:
                if EASY_AVAILABLE:
                    easy_reader = _get_easy_reader()
                else:
                    import easyocr as _easy_mod
                    easy_reader = _easy_mod.Reader(["fr", "en"], gpu=False)
                results = easy_reader.readtext(img, detail=1, paragraph=False, rotation_info=[90, 180, 270])
                return results or []
            except Exception:
                raise RuntimeError(f"PaddleOCR failed and EasyOCR fallback also failed: {e}") from e

    # fallback EasyOCR
    results = reader.readtext(
        img,
        detail=1,
        paragraph=False,
        rotation_info=[90, 180, 270]
    )
    return results or []


def _extract_text_paddle(reader, img: np.ndarray) -> list[tuple]:
    """Extrait et normalise les résultats PaddleOCR multi-versions."""
    raw = None

    # PaddleOCR v3
    try:
        raw = reader.predict(img, use_textline_orientation=True, return_word_box=True)
    except TypeError:
        try:
            raw = reader.predict(img)
        except Exception:
            raw = None

    # PaddleOCR v2/v1
    if raw is None:
        try:
            raw = reader.ocr(img)
        except TypeError:
            raw = reader.ocr(img, cls=True)

    return _normalize_paddle_output(raw)


def _deskew_image(img: np.ndarray) -> np.ndarray | None:
    """Estimate skew angle and return a rotated image if angle significant.

    Uses minAreaRect on the binary text mask. Returns None if deskewing not needed.
    """
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # invert so text is white
        _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        # find non-zero points
        coords = cv2.findNonZero(255 - th)
        if coords is None:
            return None
        rect = cv2.minAreaRect(coords)
        angle = rect[-1]
        if angle < -45:
            angle = 90 + angle
        else:
            angle = angle

        # normalize angle to rotate in correct direction
        if abs(angle) < 1.0:
            return None

        # rotate image to deskew
        (h, w) = img.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        return rotated
    except Exception:
        return None


def _normalize_paddle_output(raw) -> list[tuple]:
    """
    Normalise vers [(bbox, text, conf), ...].
    Supporte:
    - format legacy: [[ [box, (text, score)], ... ]]
    - format v3: [ {dt_polys, rec_texts, rec_scores, ...}, ... ]
    """
    out: list[tuple] = []

    if not isinstance(raw, list):
        return out

    for item in raw:
        # PaddleOCR v3
        if isinstance(item, dict):
            polys = item.get("dt_polys") or []
            texts = item.get("rec_texts") or []
            scores = item.get("rec_scores") or []
            n = min(len(polys), len(texts), len(scores))
            for i in range(n):
                box = np.array(polys[i]).tolist()
                text = str(texts[i])
                try:
                    conf = float(scores[i])
                except Exception:
                    conf = 0.0
                out.append((box, text, conf))
            continue

        # PaddleOCR legacy
        entries = item if isinstance(item, list) else [item]
        for entry in entries:
            try:
                box, (text, score) = entry
                out.append((box, str(text), float(score)))
            except Exception:
                continue

    return out


def _score_results(results: list[tuple]) -> float:
    """Score simple pour choisir la meilleure orientation OCR."""
    if not results:
        return 0.0

    total_conf = sum(float(c) for _, _, c in results)
    text = " ".join(t for _, t, c in results if c > 0.1)
    alnum_len = len(re.sub(r"[^A-Za-z0-9]", "", text))
    has_postal = 1.0 if re.search(r"\b\d{5}\b", text) else 0.0
    return total_conf + (0.03 * alnum_len) + (2.0 * has_postal)


def _normalize_ocr_text(s: str) -> str:
    """Nettoyage simple pour corriger confusions OCR fréquentes.

    - Remplace caractères similaires quand il s'agit de chiffres
    - Supprime espaces indésirables dans séquences numériques
    - Normalise les espaces et casse
    """
    if not s:
        return s
    t = s.strip()
    # remplacer glyphes fréquents
    replacements = {
        '\\u2019': "'",
        '\\u2018': "'",
    }
    for k, v in replacements.items():
        t = t.replace(k, v)

    # Corrige confusions dans séquences numériques (codes postaux, numéros)
    def fix_digits(tok: str) -> str:
        # if token contains mostly digits or digits+confusable letters
        if re.search(r"\d", tok):
            tok = tok.replace('O', '0').replace('o', '0')
            tok = tok.replace('I', '1').replace('l', '1').replace('|', '1')
            tok = tok.replace('S', '5') if re.search(r"\d[S]", tok) else tok
            tok = re.sub(r"[^0-9]", "", tok)
        return tok

    parts = re.split(r"(\s+)", t)
    parts = [fix_digits(p) if re.search(r"\d|O|I|l|\|", p) else p for p in parts]
    t = ''.join(parts)

    # collapse whitespace
    t = re.sub(r"\s+", ' ', t)
    return t.strip()


def _clean_postal_candidate(tok: str) -> str:
    """Try to coerce a token into a 5-digit postal candidate.

    Replace common letter-digit confusions and strip non-digits.
    """
    if not tok:
        return tok
    s = tok.upper()
    s = s.replace('O', '0').replace('I', '1').replace('L', '1').replace('|', '1')
    s = s.replace(' ', '')
    s = re.sub(r"[^0-9]", '', s)
    return s


def is_mostly_empty(results: list[tuple]) -> bool:
    text = " ".join(t for (_, t, c) in results if c > 0.1)
    return len(re.sub(r'\s+', '', text)) < 12


def parse_receipt(results: list[tuple]) -> dict:
    """
    Extrait les briques d'adresse et reconstruit une adresse complète quand c'est possible.
    """
    result = {
        "numero_rue": None,
        "nom_rue": None,
        "code_postal": None,
        "ville": None,
        "adresse_complete": None,
        "adresse_brute": None,
        "est_ticket": True,
    }

    if is_mostly_empty(results):
        result["est_ticket"] = False
        return result

    # Reconstituer les lignes triées par position verticale
    results_sorted = sorted(results, key=lambda r: r[0][0][1])
    lines = [text for (_, text, conf) in results_sorted if conf > 0.1]

    # Nettoyage post-OCR: corriger confusions communes et normaliser
    lines = [_normalize_ocr_text(l) for l in lines]

    result["code_postal"] = _extract_code_postal(lines)
    numero, rue = _extract_rue(lines)
    result["numero_rue"] = numero
    result["nom_rue"] = rue
    ville = _extract_ville(lines, result["code_postal"]) if result["code_postal"] else None
    result["ville"] = ville or None

    # Construire une adresse brute si possible
    if numero and rue:
        result["adresse_brute"] = f"{numero} {rue}"
    elif rue:
        result["adresse_brute"] = rue
    else:
        result["adresse_brute"] = None

    # Construire une adresse complète exploitable pour la validation/export
    complete_parts = [part for part in [numero, rue, result["code_postal"], result["ville"]] if part]
    if complete_parts:
        result["adresse_complete"] = ", ".join(complete_parts)

    return result


def _normalize_city_candidate(text: str) -> str | None:
    if not text:
        return None
    tokens = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ'-]+", text)
    if not tokens:
        return None
    city = " ".join(tokens).strip()
    if len(city) < 2:
        return None
    blacklist = {
        "FRANCE", "RESTAURANT", "BAR", "CAFE", "CAFÉ", "TOTAL", "TICKET",
        "FACTURE", "MERCI", "SIRET", "TVA", "AVENUE", "RUE", "ROUTE",
        "PLACE", "IMPASSE", "BOULEVARD", "CHEMIN", "ALLEE", "ALLÉE",
    }
    if city.upper() in blacklist:
        return None
    return city


def _extract_ville(lines: list[str], code_postal: str) -> str | None:
    """Cherche une ville sur la même ligne que le code postal ou sur la ligne suivante."""
    for i, line in enumerate(lines):
        if code_postal in line:
            # enlever le code postal et garder le reste
            after = line.split(code_postal, 1)[1].strip()
            if after:
                city = _normalize_city_candidate(after)
                if city:
                    return city
            # sinon regarder la ligne suivante
            if i + 1 < len(lines):
                city = _normalize_city_candidate(lines[i + 1])
                if city:
                    return city
    return None


def _extract_code_postal(lines: list[str]) -> str | None:
    """Cherche un code postal français (5 chiffres commençant par 0-9)."""
    pattern = re.compile(r"\b(\d{5})\b")
    mots_a_ignorer = ["siret", "tva", "naf", "siren", "rcs", "iban", "bic"]

    for line in lines:
        if any(kw in line.lower() for kw in mots_a_ignorer):
            continue
        # Ignore les lignes avec trop de chiffres (SIRET = 14 chiffres)
        if len(re.sub(r'\D', '', line)) > 10:
            continue
        # Chercher d'abord un match propre
        match = pattern.search(line)
        if match:
            return match.group(1)

        # Si rien trouvé, nettoyer les tokens pour corriger confusions OCR
        for token in re.split(r"\s+|[^0-9A-Za-z]", line):
            if not token:
                continue
            cleaned = _clean_postal_candidate(token)
            m = pattern.search(cleaned)
            if m:
                return m.group(1)
    return None


def _extract_rue(lines: list[str]) -> tuple[str | None, str | None]:
    """
    Cherche une ligne contenant un numéro + type de voie + nom.
    Retourne (numero, nom_de_rue).
    """
    rue_pattern = re.compile(
        r"^(\d{1,4})\s+((?:rue|avenue|av\.?|boulevard|bd\.?|place|impasse|allée|allee|route|rte\.?|chemin|voie|passage|square)\s+.+)",
        re.IGNORECASE
    )
    mots_a_ignorer = ["siret", "tva", "total", "ticket", "facture", "vente",
                      "merci", "article", "promotion", "carte"]

    for line in lines:
        if any(kw in line.lower() for kw in mots_a_ignorer):
            continue
        # essayer sur la ligne brute puis sur la version nettoyée
        match = rue_pattern.match(line)
        if not match:
            cleaned = _normalize_ocr_text(line)
            match = rue_pattern.match(cleaned)
        if match:
            return match.group(1), match.group(2).strip()

    return None, None
