import os
from preprocessor import preprocess_image
from extractor import extract_text, parse_receipt
from exporter import export_csv

IMAGES_DIR = "images"
SUPPORTED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif")


def get_images(directory: str) -> list[str]:
    """Retourne la liste des fichiers image dans le dossier."""
    if not os.path.exists(directory):
        print(f"[ERREUR] Le dossier '{directory}' n'existe pas.")
        return []

    images = [
        f for f in os.listdir(directory)
        if f.lower().endswith(SUPPORTED_EXTENSIONS)
    ]
    return images


def main():
    print("=== OCR Expense Tracker ===\n")

    images = get_images(IMAGES_DIR)

    if not images:
        print(f"Aucune image trouvée dans '{IMAGES_DIR}/'.")
        print(f"Formats supportés : {', '.join(SUPPORTED_EXTENSIONS)}")
        return

    print(f"{len(images)} image(s) trouvée(s) :\n")

    results = []

    for img_file in images:
        img_path = os.path.join(IMAGES_DIR, img_file)
        print(f"  Traitement : {img_file} ...")

        try:
            processed = preprocess_image(img_path)
            text = extract_text(processed)
            data = parse_receipt(text)
            data["fichier"] = img_file
            results.append(data)

            print(f"    Prix TTC : {data['prix_ttc'] or 'non trouvé'}")
            print(f"    TVA      : {data['tva'] or 'non trouvée'}")
            print(f"    Adresse  : {data['adresse'] or 'non trouvée'}")

        except Exception as e:
            print(f"    [ERREUR] {e}")
            results.append({
                "fichier": img_file,
                "prix_ttc": None,
                "tva": None,
                "adresse": None,
            })

        print()

    # Export CSV
    if results:
        filepath = export_csv(results)
        print(f"✅ CSV généré : {filepath}")
    else:
        print("Aucun résultat à exporter.")


if __name__ == "__main__":
    main()
