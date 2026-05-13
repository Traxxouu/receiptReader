import csv
import os
from datetime import datetime

OUTPUT_DIR = "output"


def export_csv(results: list[dict]) -> str:
    """
    Exporte les résultats dans un fichier CSV dans le dossier output/.
    Retourne le chemin du fichier créé.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"notes_de_frais_{timestamp}.csv"
    filepath = os.path.join(OUTPUT_DIR, filename)

    fieldnames = [
        "fichier",
        "adresse_complete",
        "adresse_brute",
        "code_postal",
        "ville",
        "adresse_validee",
        "confiance",
        "mode",
        "statut",
    ]

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        for row in results:
            writer.writerow({
                "fichier": row.get("fichier", ""),
                "adresse_complete": row.get("adresse_complete", ""),
                "adresse_brute": row.get("adresse_brute", ""),
                "code_postal": row.get("code_postal", ""),
                "ville": row.get("ville", ""),
                "adresse_validee": row.get("adresse_validee", ""),
                "confiance": row.get("confiance", ""),
                "mode": row.get("mode", ""),
                "statut": row.get("statut", ""),
            })

    return filepath
