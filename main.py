import os

IMAGES_DIR = "images"
SUPPORTED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif")


def count_images(directory: str) -> list[str]:
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

    images = count_images(IMAGES_DIR)

    if not images:
        print(f"Aucune image trouvée dans le dossier '{IMAGES_DIR}/'.")
        print(f"Formats supportés : {', '.join(SUPPORTED_EXTENSIONS)}")
    else:
        print(f"{len(images)} image(s) trouvée(s) dans '{IMAGES_DIR}/' :\n")
        for i, img in enumerate(images, 1):
            print(f"  {i}. {img}")


if __name__ == "__main__":
    main()
