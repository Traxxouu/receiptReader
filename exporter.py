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

    fieldnames = ["fichier", "prix_ttc", "tva", "adresse"]

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        for row in results:
            writer.writerow({
                "fichier": row.get("fichier", ""),
                "prix_ttc": row.get("prix_ttc", ""),
                "tva": row.get("tva", ""),
                "adresse": row.get("adresse", ""),
            })

    return filepath
