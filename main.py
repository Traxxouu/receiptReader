import os
from preprocessor import preprocess_image
from extractor import extract_lines, parse_receipt

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

    for img_file in images:
        img_path = os.path.join(IMAGES_DIR, img_file)
        print(f"\n📄 {img_file}")

        try:
            img = preprocess_image(img_path)
            lines = extract_lines(img)
            data = parse_receipt(lines)

            if not data["est_ticket"]:
                print("   ⏭  Pas un ticket, ignore.")
                continue

            if data["adresse"]:
                print(f"   ✅ {data['adresse']}")
            else:
                print("   ❌ Adresse non trouvee")

        except Exception as e:
            print(f"   [ERREUR] {e}")

    print("\n" + "-" * 60)
    print("Termine.")


if __name__ == "__main__":
    main()
