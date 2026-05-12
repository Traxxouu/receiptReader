import os
from preprocessor import preprocess_image
from extractor import extract_text, parse_receipt
from validator import valider_adresse

IMAGES_DIR = "images"
SUPPORTED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif")


def get_images(directory: str) -> list[str]:
    if not os.path.exists(directory):
        print(f"[ERREUR] Le dossier '{directory}' n'existe pas.")
        return []
    return [
        f for f in os.listdir(directory)
        if f.lower().endswith(SUPPORTED_EXTENSIONS)
    ]


def main():
    print("=== Receipt Reader — Extraction d'adresses ===\n")

    images = get_images(IMAGES_DIR)
    if not images:
        print(f"Aucune image trouvée dans '{IMAGES_DIR}/'.")
        return

    print(f"{len(images)} image(s) trouvée(s)\n")
    print("-" * 60)

    for img_file in images:
        img_path = os.path.join(IMAGES_DIR, img_file)
        print(f"\n📄 {img_file}")

        try:
            img = preprocess_image(img_path)
            text = extract_text(img)
            data = parse_receipt(text)

            if not data["est_ticket"]:
                print("   ⏭  Pas un ticket, image ignorée.")
                continue

            adresse_brute = data["adresse_brute"]
            cp = data["code_postal"]
            ville = data["ville"]

            if not adresse_brute and not cp:
                print("   ❌ Aucune adresse ou code postal trouvé.")
                continue

            if adresse_brute:
                print(f"   🔍 Adresse brute  : {adresse_brute}")
            else:
                print(f"   🔍 Code postal    : {cp} {ville or ''}")

            validation = valider_adresse(adresse_brute, cp, ville)

            if validation["adresse_validee"]:
                mode = f" ({validation['mode']})" if validation["mode"] else ""
                print(f"   ✅ Adresse validée : {validation['adresse_validee']}{mode}")
                print(f"   📊 Confiance       : {validation['confiance']}")
            else:
                print(f"   ⚠️  Non trouvée sur OpenStreetMap")
                if adresse_brute:
                    print(f"      (adresse brute conservée : {adresse_brute})")

        except Exception as e:
            print(f"   [ERREUR] {e}")

    print("\n" + "-" * 60)
    print("Terminé.")


if __name__ == "__main__":
    main()
