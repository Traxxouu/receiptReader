import re
import easyocr
import numpy as np

_reader = None


def get_reader() -> easyocr.Reader:
    global _reader
    if _reader is None:
        print("   [EasyOCR] Chargement du modèle (première fois uniquement)...")
        _reader = easyocr.Reader(["fr", "en"], gpu=False)
    return _reader


def extract_text(img: np.ndarray) -> str:
    reader = get_reader()
    results = reader.readtext(
        img,
        detail=1,
        paragraph=False,
        rotation_info=[90, 180, 270]
    )
    if not results:
        return ""
    results.sort(key=lambda r: r[0][0][1])
    lines = [text for (_, text, conf) in results if conf > 0.1]
    return "\n".join(lines)


def is_mostly_empty(text: str) -> bool:
    clean = re.sub(r'\s+', '', text)
    return len(clean) < 30


def parse_receipt(text: str) -> dict:
    result = {
        "adresse_brute": None,
        "code_postal": None,
        "ville": None,
        "est_ticket": True,
    }

    if is_mostly_empty(text):
        result["est_ticket"] = False
        return result

    lines = text.splitlines()
    lines = [l.strip() for l in lines if l.strip()]

    result["adresse_brute"] = extract_adresse(lines)

    # Toujours extraire code postal + ville séparément pour le fallback Nominatim
    cp, ville = extract_code_postal_ville(lines)
    result["code_postal"] = cp
    result["ville"] = ville

    return result


def extract_adresse(lines: list[str]) -> str | None:
    adresse_pattern = re.compile(
        r"^\d{1,4}\s+(?:rue|avenue|av\.?|boulevard|bd\.?|place|impasse|allée|allee|route|rte\.?|chemin|voie|passage|square)\s+.+",
        re.IGNORECASE
    )
    # Pattern sans numéro : "Bois-d'Arcy - Versailles" style Leroy Merlin
    ville_composee_pattern = re.compile(
        r"^[A-ZÀ-Üa-zà-ü][a-zA-ZÀ-üà-ü\-\s']+\s*[-–]\s*[A-ZÀ-Üa-zà-ü][a-zA-ZÀ-üà-ü\s]+$"
    )
    code_postal_pattern = re.compile(r"\b\d{5}\b")
    mots_a_ignorer = ["siret", "tva", "naf", "tel", "tél", "www", "http",
                      "fax", "fidélité", "fidelite", "capital", "rcs", "siren",
                      "total", "ticket", "vente", "facture", "merci"]

    # Stratégie 1 : numéro + type de voie
    for i, line in enumerate(lines):
        if adresse_pattern.match(line):
            if i + 1 < len(lines) and code_postal_pattern.search(lines[i + 1]):
                return f"{line}, {lines[i + 1]}"
            return line

    # Stratégie 2 : "Ville - Ville" (Leroy Merlin style)
    for i, line in enumerate(lines):
        if ville_composee_pattern.match(line) and not any(kw in line.lower() for kw in mots_a_ignorer):
            if i > 0:
                return f"{lines[i - 1]}, {line}"
            return line

    # Stratégie 3 : code postal 5 chiffres
    for i, line in enumerate(lines):
        if code_postal_pattern.search(line):
            if any(kw in line.lower() for kw in mots_a_ignorer):
                continue
            if len(re.sub(r'\D', '', line)) > 8:
                continue
            if i > 0 and not any(kw in lines[i - 1].lower() for kw in mots_a_ignorer):
                return f"{lines[i - 1]}, {line}"
            return line

    return None


def extract_code_postal_ville(lines: list[str]) -> tuple[str | None, str | None]:
    """
    Extrait le code postal et la ville séparément.
    Utilisé comme fallback pour Nominatim si l'adresse complète échoue.
    """
    code_postal_pattern = re.compile(r"\b(\d{5})\b")
    mots_a_ignorer = ["siret", "tva", "naf", "tel", "tél", "www", "http",
                      "fax", "capital", "rcs", "siren"]

    for line in lines:
        if any(kw in line.lower() for kw in mots_a_ignorer):
            continue
        if len(re.sub(r'\D', '', line)) > 8:
            continue

        match = code_postal_pattern.search(line)
        if match:
            cp = match.group(1)
            # La ville = tout ce qui suit le code postal sur la même ligne
            ville_raw = line[match.end():].strip()
            ville = re.sub(r'[^a-zA-ZÀ-ü\s\-]', '', ville_raw).strip()
            if ville:
                return cp, ville
            return cp, None

    return None, None
