# Receipt Reader

Outil d'extraction automatique d'adresses depuis des photos de tickets de caisse.

## Installation rapide

### Linux: Ubuntu, Debian, Arch, Hyprland, Hyde

Le plus simple est de cloner le depot puis de lancer l'installateur local:

```bash
git clone https://github.com/Traxxouu/receiptReader.git
cd receiptReader
bash install.sh
```

Le script detecte automatiquement `apt` ou `pacman`, installe Python, Git et curl, cree un environnement virtuel, installe les dependances Python, installe Ollama si besoin, telecharge le modele `llama3.2`, puis cree `start.sh`.

Pour lancer ensuite l'application:

```bash
bash start.sh
```

### Windows

Le plus simple pour les utilisateurs Windows est de distribuer un installeur `ReceiptReaderSetup.exe` base sur `installer.nsi`.

Si vous travaillez depuis la source, l'installation manuelle minimale est:

```powershell
py -3 -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt
ollama pull llama3.2
py app.py
```

## Utilisation

1. Saisir l'adresse du laboratoire dans le champ a gauche
2. Glisser-deposer les photos de tickets dans la zone de drop
3. Cliquer sur **Extraire les adresses**
4. Si une adresse est incorrecte, cliquer sur **Corriger** pour voir les suggestions puis valider
5. Cliquer sur **Exporter CSV** ou **Exporter Excel** pour recuperer le fichier final

## Problemes courants

`No module named easyocr` : relancer l'installation des dependances dans le venv.

`Ollama n'est pas lance` : demarrer Ollama avec `ollama serve`.

Premier lancement plus lent : normal, EasyOCR et Ollama peuvent telecharger leurs modeles la premiere fois.
