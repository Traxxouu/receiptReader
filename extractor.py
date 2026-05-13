import re
import numpy as np
import cv2

try:
    import easyocr
    EASY_AVAILABLE = True
except Exception:
    EASY_AVAILABLE = False

_reader = None


def get_reader():
    global _reader
    if _reader is None:
        if not EASY_AVAILABLE:
            raise RuntimeError("EasyOCR non disponible. Installe-le avec: pip install easyocr")
        print("   [OCR] Chargement du modele EasyOCR...")
        _reader = easyocr.Reader(["fr", "en"], gpu=False)
    return _reader


def extract_lines(img: np.ndarray) -> list[str]:
    """
    Extrait les lignes de texte de l'image.
    Teste 4 orientations et garde la meilleure.
    Retourne une liste de strings triee de haut en bas.
    """
    reader = get_reader()

    best_results = []
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

        score = _score(results)
        if score > best_score:
            best_score = score
            best_results = results

    # Trier par position verticale et filtrer confiance basse
    best_results.sort(key=lambda r: r[0][0][1])
    return [text for (_, text, conf) in best_results if conf > 0.15]


def _score(results: list) -> float:
    """Score une liste de resultats OCR pour choisir la meilleure orientation."""
    text = " ".join(t for (_, t, c) in results if c > 0.1)
    clean = re.sub(r'[^A-Za-zÀ-ÿ0-9]', '', text)

    score = len(clean) * 0.1
    # Bonus si on trouve un code postal francais
    if re.search(r'\b\d{5}\b', text):
        score += 50
    # Bonus si on trouve un type de voie
    if re.search(r'\b(rue|avenue|boulevard|route|place|chemin|impasse)\b', text, re.IGNORECASE):
        score += 30
    return score


def is_mostly_empty(lines: list[str]) -> bool:
    text = " ".join(lines)
    return len(re.sub(r'\s+', '', text)) < 30


def parse_receipt(lines: list[str]) -> dict:
    """
    Extrait l'adresse complete telle qu'elle est ecrite sur le ticket.
    Strategie :
      1. Cherche une ligne avec numero + type de voie (rue, avenue, etc.)
      2. Cherche le code postal sur les lignes proches
      3. La ville est sur la meme ligne que le CP ou juste apres
      4. Assemble le tout : rue + CP + ville
    """
    result = {
        "adresse": None,
        "est_ticket": True,
    }

    if is_mostly_empty(lines):
        result["est_ticket"] = False
        return result

    mots_a_ignorer = [
        "siret", "tva", "naf", "siren", "rcs", "iban", "bic",
        "total", "ticket", "facture", "vente", "merci", "article",
        "promotion", "carte", "tel", "tél", "www", "http", "mail",
        "code", "naf", "ape"
    ]

    rue_pattern = re.compile(
        r"(\d{1,4})\s+((?:rue|avenue|av\.?|boulevard|bd\.?|place|impasse|"
        r"allée|allee|route|rte\.?|chemin|voie|passage|square|sentier)\b.+)",
        re.IGNORECASE
    )
    cp_pattern = re.compile(r'\b(\d{5})\b')

    # Etape 1 : trouver la ligne avec la rue
    rue_line_idx = None
    rue_text = None
    for i, line in enumerate(lines):
        if any(kw in line.lower() for kw in mots_a_ignorer):
            continue
        match = rue_pattern.search(line)
        if match:
            rue_text = line.strip()
            rue_line_idx = i
            break

    # Etape 2 : chercher le code postal (dans les 5 lignes autour de la rue)
    cp = None
    cp_line_idx = None
    search_range = range(len(lines))
    if rue_line_idx is not None:
        start = max(0, rue_line_idx - 2)
        end = min(len(lines), rue_line_idx + 6)
        search_range = range(start, end)

    for i in search_range:
        line = lines[i]
        if any(kw in line.lower() for kw in ["siret", "tva", "siren", "rcs", "iban"]):
            continue
        # Ignorer les lignes avec trop de chiffres (SIRET etc.)
        if len(re.sub(r'\D', '', line)) > 10:
            continue
        match = cp_pattern.search(line)
        if match:
            cp = match.group(1)
            cp_line_idx = i
            break

    # Etape 3 : extraire la ville depuis la ligne du CP
    ville = None
    if cp is not None and cp_line_idx is not None:
        line = lines[cp_line_idx]
        # La ville = tout ce qui suit le CP sur la meme ligne
        after_cp = line.split(cp, 1)[1].strip()
        # Nettoyer : garder lettres, espaces, tirets, apostrophes
        after_cp = re.sub(r"[^A-Za-zÀ-ÿ\s'\-]", "", after_cp).strip()
        if len(after_cp) >= 2:
            ville = after_cp
        # Si rien apres le CP, regarder la ligne suivante
        elif cp_line_idx + 1 < len(lines):
            next_line = lines[cp_line_idx + 1]
            if not any(kw in next_line.lower() for kw in mots_a_ignorer):
                candidate = re.sub(r"[^A-Za-zÀ-ÿ\s'\-]", "", next_line).strip()
                if len(candidate) >= 2:
                    ville = candidate

    # Etape 4 : assembler l'adresse complete
    parts = []
    if rue_text:
        parts.append(rue_text)
    if cp and ville:
        parts.append(f"{cp} {ville}")
    elif cp:
        parts.append(cp)
    elif ville:
        parts.append(ville)

    if parts:
        result["adresse"] = ", ".join(parts)

    return result
