import csv
import os
from datetime import datetime

OUTPUT_DIR = "output"


def export_csv(results: list[dict]) -> str:
    """
    Exporte les resultats dans un fichier CSV horodate.
    Retourne le chemin du fichier cree.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"adresses_{timestamp}.csv"
    filepath = os.path.join(OUTPUT_DIR, filename)

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["fichier", "adresse"], delimiter=";")
        writer.writeheader()
        for row in results:
            writer.writerow({
                "fichier": row.get("fichier", ""),
                "adresse": row.get("adresse", ""),
            })

    return filepath
