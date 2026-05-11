import re
import pytesseract
from PIL import Image
import numpy as np

# Si Tesseract n'est pas dans le PATH, décommente et adapte cette ligne :
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def extract_text(processed_img: np.ndarray) -> str:
    """Extrait le texte brut de l'image pré-traitée."""
    pil_img = Image.fromarray(processed_img)
    text = pytesseract.image_to_string(pil_img, lang="fra")
    return text


def parse_receipt(text: str) -> dict:
    """
    Analyse le texte brut du ticket et extrait :
    - prix TTC
    - TVA
    - adresse du commerce
    """
    result = {
        "prix_ttc": None,
        "tva": None,
        "adresse": None,
    }

    lines = text.splitlines()
    lines = [l.strip() for l in lines if l.strip()]

    result["prix_ttc"] = extract_total(lines)
    result["tva"] = extract_tva(lines)
    result["adresse"] = extract_adresse(lines)

    return result


def extract_montant(line: str) -> str | None:
    """
    Extrait un montant numérique d'une ligne.
    Gère les cas où Tesseract mange la virgule : '067' lu à la place de '0,67'
    """
    # Cas normal : 10,70 ou 173.22 ou 0,67
    match = re.search(r"\d+[.,]\d{2}", line)
    if match:
        return match.group().replace(",", ".")

    # Cas Tesseract mange la virgule/point : "067" ou "903" en fin de ligne
    # On cherche un nombre de 2-3 chiffres isolé en fin de ligne (probable montant < 10€)
    match = re.search(r"\b0(\d{2})\b\s*€?\s*$", line)
    if match:
        return f"0.{match.group(1)}"

    return None


def extract_total(lines: list[str]) -> str | None:
    """
    Cherche le montant total TTC.
    Gère les formats :
      - TOTAL TTC EUR   173.22
      - Total TTC       10,70 €
      - NET A PAYER     XX,XX
    """
    for line in lines:
        line_lower = line.lower()
        if "total" in line_lower and "ttc" in line_lower:
            montant = extract_montant(line)
            if montant:
                return montant

    for line in lines:
        line_lower = line.lower()
        if any(kw in line_lower for kw in ["net à payer", "net a payer", "à payer", "a payer"]):
            montant = extract_montant(line)
            if montant:
                return montant

    return None


def extract_tva(lines: list[str]) -> str | None:
    """
    Cherche le montant de la TVA.
    Gère les formats :
      - TVA    0,67 €         → ticket Marie Blachère
      - TVA 067 €             → Tesseract mange la virgule
      - Dont TVA (A) 5.50%  164.19 HT= 9.03  → ticket Grand Marché
      - ( K) 5.50K  AG4HONT=. 9.08           → version dégradée Tesseract du Grand Marché
    """
    for line in lines:
        line_lower = line.lower()

        # Ignore numéro TVA intracommunautaire
        if "tva int" in line_lower:
            continue
        # Ignore lignes avec numéro FR... (TVA intra)
        if re.search(r"fr\d{10,}", line_lower):
            continue

        if "tva" in line_lower:
            # Format "Dont TVA" ou ligne avec HT= → on prend le DERNIER montant (= montant TVA)
            if "dont" in line_lower or "ht=" in line_lower or "ht =" in line_lower:
                montants = re.findall(r"\d+[.,]\d{2}", line)
                if montants:
                    return montants[-1].replace(",", ".")

            # Format simple "TVA  0,67 €" ou "TVA 067 €"
            montant = extract_montant(line)
            if montant:
                return montant

        # Ticket Grand Marché : Tesseract déforme "Dont TVA" en quelque chose avec "hont" ou "ht="
        # On cherche les lignes avec un pattern de taux TVA (5.50% ou 10.00%) + montant final
        if re.search(r"\d+[.,]\d{2}\s*%", line):
            montants = re.findall(r"\d+[.,]\d{2}", line)
            # Dernier montant après le taux = montant TVA
            if len(montants) >= 2:
                return montants[-1].replace(",", ".")

    return None


def extract_adresse(lines: list[str]) -> str | None:
    """
    Cherche l'adresse du commerce.
    Stratégie :
      1. Ligne avec numéro + type de voie (rue, avenue, etc.) → colle le code postal si ligne suivante
      2. Fallback : ligne avec code postal français (5 chiffres)
    """
    adresse_pattern = re.compile(
        r"^\d{1,4}\s+(?:rue|avenue|av\.?|boulevard|bd\.?|place|impasse|allée|allee|route|chemin|voie|passage|square)\s+.+",
        re.IGNORECASE
    )
    code_postal_pattern = re.compile(r"\b\d{5}\b")

    for i, line in enumerate(lines):
        if adresse_pattern.match(line):
            if i + 1 < len(lines) and code_postal_pattern.search(lines[i + 1]):
                return f"{line}, {lines[i + 1]}"
            return line

    # Fallback code postal
    for i, line in enumerate(lines):
        if code_postal_pattern.search(line):
            if any(kw in line.lower() for kw in ["siret", "tva", "naf", "tel", "tél"]):
                continue
            if i > 0:
                return f"{lines[i - 1]}, {line}"
            return line

    return None
