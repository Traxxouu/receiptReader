import re
import easyocr
import numpy as np

_reader = None


def get_reader() -> easyocr.Reader:
    global _reader
    if _reader is None:
        _reader = easyocr.Reader(["fr", "en"], gpu=False)
    return _reader


def extract_text(img: np.ndarray) -> list[tuple]:
    """
    Retourne la liste brute EasyOCR : [(bbox, text, conf), ...]
    Teste 0°, 90°, 180°, 270°.
    """
    reader = get_reader()
    results = reader.readtext(
        img,
        detail=1,
        paragraph=False,
        rotation_info=[90, 180, 270]
    )
    return results or []


def is_mostly_empty(results: list[tuple]) -> bool:
    text = " ".join(t for (_, t, c) in results if c > 0.1)
    return len(re.sub(r'\s+', '', text)) < 30


def parse_receipt(results: list[tuple]) -> dict:
    """
    Nouvelle logique simplifiée et robuste :
    1. Extrait le code postal (5 chiffres) → fiable pour l'OCR
    2. Extrait numéro + nom de rue → ce que l'OCR lit bien
    3. Laisse Nominatim déduire la ville depuis le code postal
    """
    result = {
        "numero_rue": None,
        "nom_rue": None,
        "code_postal": None,
        "est_ticket": True,
    }

    if is_mostly_empty(results):
        result["est_ticket"] = False
        return result

    # Reconstituer les lignes triées par position verticale
    results_sorted = sorted(results, key=lambda r: r[0][0][1])
    lines = [text for (_, text, conf) in results_sorted if conf > 0.1]

    result["code_postal"] = _extract_code_postal(lines)
    numero, rue = _extract_rue(lines)
    result["numero_rue"] = numero
    result["nom_rue"] = rue

    return result


def _extract_code_postal(lines: list[str]) -> str | None:
    """Cherche un code postal français (5 chiffres commençant par 0-9)."""
    pattern = re.compile(r"\b([013-9]\d{4})\b")
    mots_a_ignorer = ["siret", "tva", "naf", "siren", "rcs", "iban", "bic"]

    for line in lines:
        if any(kw in line.lower() for kw in mots_a_ignorer):
            continue
        # Ignore les lignes avec trop de chiffres (SIRET = 14 chiffres)
        if len(re.sub(r'\D', '', line)) > 10:
            continue
        match = pattern.search(line)
        if match:
            return match.group(1)
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
        match = rue_pattern.match(line)
        if match:
            return match.group(1), match.group(2).strip()

    return None, None
