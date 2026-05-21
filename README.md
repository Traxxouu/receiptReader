# Receipt Reader

Outil d'extraction automatique d'adresses depuis des photos de tickets de caisse.

---

## Installation Windows (à faire une seule fois)

### 1. Installer Python 3.13
Telecharger et installer : https://www.python.org/ftp/python/3.13.3/python-3.13.3-amd64.exe

**Important** : cocher la case **"Add Python to PATH"** pendant l'installation.

### 2. Installer Ollama (moteur IA)
Telecharger et installer : https://ollama.com/download/windows

### 3. Telecharger le modele IA
Ouvrir un terminal (cmd ou PowerShell) et taper :
```
ollama pull llama3.2
```

### 4. Telecharger Receipt Reader
Telecharger le projet : https://github.com/Traxxouu/receiptReader/archive/refs/heads/main.zip

Extraire le zip ou vous voulez.

### 5. Installer les dependances Python
Dans le dossier du projet, ouvrir un terminal et taper :
```
pip install easyocr opencv-python requests PyQt6 openpyxl
```

---

## Lancer l'application

Dans le dossier du projet :
```
python app.py
```

---

## Utilisation

1. Saisir l'adresse du laboratoire dans le champ a gauche
2. Glisser-deposer les photos de tickets dans la zone de drop
3. Cliquer sur **Extraire les adresses**
4. Si une adresse est incorrecte : cliquer sur **Voir** pour afficher le ticket, puis **Corriger** pour la modifier
5. Cliquer sur **Exporter en Excel** pour obtenir le fichier .xlsx

---

## Problemes courants

**"No module named easyocr"** → relancer `pip install easyocr`

**"Ollama n'est pas lance"** → ouvrir un terminal et taper `ollama serve`

**L'application est lente au premier lancement** → normal, EasyOCR telecharge ses modeles (~500MB) une seule fois
