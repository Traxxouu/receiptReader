import os
from preprocessor import preprocess_image
from extractor import extract_raw_text
from ia import extraire_adresse_ia
from exporter import export_csv

IMAGES_DIR = "images"
SUPPORTED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif")


def get_images(directory: str) -> list[str]:
    if not os.path.exists(directory):
        print(f"[ERREUR] Le dossier '{directory}' n'existe pas.")
        return []
    return sorted([
        f for f in os.listdir(directory)
        if f.lower().endswith(SUPPORTED_EXTENSIONS)
    ])


def main():
    print("=== Receipt Reader ===\n")

    images = get_images(IMAGES_DIR)
    if not images:
        print(f"Aucune image trouvee dans '{IMAGES_DIR}/'.")
        return

    print(f"{len(images)} image(s) trouvee(s)\n")
    print("-" * 60)

    results = []

    for img_file in images:
        img_path = os.path.join(IMAGES_DIR, img_file)
        print(f"\n📄 {img_file}")

        entry = {"fichier": img_file, "adresse": ""}

        try:
            # Etape 1 : preprocessing
            img = preprocess_image(img_path)

            # Etape 2 : OCR → texte brut
            texte = extract_raw_text(img)

            if not texte.strip():
                print("   ⏭  Aucun texte detecte, image ignoree.")
                results.append(entry)
                continue

            # Etape 3 : IA locale → extraction adresse
            print("   🔍 OCR terminé, envoi a l'IA...")
            adresse = extraire_adresse_ia(texte)

            if adresse:
                print(f"   ✅ {adresse}")
                entry["adresse"] = adresse
            else:
                print("   ❌ Adresse non trouvee")

        except RuntimeError as e:
            print(f"   [ERREUR] {e}")
            break  # Si Ollama est pas lance, on arrete tout
        except Exception as e:
            print(f"   [ERREUR] {e}")

        results.append(entry)

    # Export CSV
    if results:
        csv_path = export_csv(results)
        print(f"\n✅ CSV genere : {csv_path}")

    print("-" * 60)


if __name__ == "__main__":
    main()
