# Receipt Reader — Maison Asteria

Application de bureau qui lit automatiquement les **photos de tickets de caisse**, en extrait l'**adresse postale**, calcule la **distance routière** (aller et aller-retour) entre le laboratoire et chaque adresse, puis génère un **rapport CSV ou Excel** prêt pour les notes de frais.

Le traitement d'image et l'IA tournent **en local sur la machine** : aucune donnée n'est envoyée à un service payant. Une connexion internet est nécessaire uniquement pour le calcul des distances et, la toute première fois, pour télécharger les modèles.

100 % gratuit et open source. **Aucun fichier `.exe` à installer.**

---

## Démonstration

![Démonstration de Receipt Reader](images/demo.gif)

*Aperçu : import des tickets, extraction des adresses et calcul des distances.*

---

## 1. À installer une seule fois

Deux logiciels gratuits à installer une fois sur la machine :

| Logiciel | Rôle | Lien |
|---|---|---|
| **Python 3** | fait tourner l'application | https://www.python.org/downloads/ |
| **Ollama** | l'IA locale qui lit les adresses | https://ollama.com/download |

Tout le reste (bibliothèques, modèle d'IA) s'installe **automatiquement** au premier lancement. Il n'y a rien d'autre à faire à la main.

---

## 2. Installation

### Sur Windows

1. **Installer Python** depuis https://www.python.org/downloads/.
   Pendant l'installation, **cocher la case « Add Python to PATH »** (important, sinon l'application ne se lancera pas).
2. **Installer Ollama** depuis https://ollama.com/download et lancer l'installeur. Ollama démarre ensuite tout seul en arrière-plan.
3. **Récupérer l'application** : sur la page GitHub du projet, bouton vert **« Code » → « Download ZIP »**, puis décompresser le dossier où vous voulez (le Bureau par exemple).
   *(ou, si Git est installé : `git clone https://github.com/Traxxouu/receiptReader.git`)*
4. **Lancer** : ouvrir le dossier `receiptReader` et **double-cliquer sur `run.bat`**.

C'est tout. Aucune ligne de commande nécessaire sous Windows.

### Sur Linux (Ubuntu, Arch…)

1. **Installer Python et Ollama** :

   Ubuntu / Debian :
   ```bash
   sudo apt install python3 python3-venv
   curl -fsSL https://ollama.com/install.sh | sh
   ```

   Arch :
   ```bash
   sudo pacman -S python ollama
   ```

2. **Récupérer l'application** :
   ```bash
   git clone https://github.com/Traxxouu/receiptReader.git
   cd receiptReader
   ```

3. **Lancer** :
   ```bash
   chmod +x run.sh   # une seule fois
   ./run.sh
   ```

> Sur une machine Linux totalement vierge (Python / git / curl absents), un script tout-en-un peut aussi installer les dépendances système automatiquement : `bash install.sh`.

---

## 3. Premier lancement (à savoir)

Le tout premier lancement est **plus long** (quelques minutes) car l'application :

- crée son environnement et télécharge ses bibliothèques (dont l'OCR EasyOCR, assez volumineux) ;
- télécharge le modèle d'IA `llama3.2` (~2 Go).

C'est **normal et cela n'arrive qu'une seule fois**. Les lancements suivants sont quasi immédiats. Il faut laisser la fenêtre ouverte pendant cette étape, sans la fermer.

---

## 4. Utiliser l'application

La fenêtre comporte un panneau de réglages à gauche et la zone de travail à droite.

1. **Saisir l'adresse du laboratoire** dans le champ « ADRESSE DU LABORATOIRE » en haut à gauche. C'est le point de départ utilisé pour calculer les distances.
2. **Ajouter les tickets** : glisser-déposer les photos dans la zone en pointillés, ou cliquer dessus pour les sélectionner dans l'explorateur. Formats acceptés : JPG, PNG, WEBP, BMP, TIFF.
3. Cliquer sur **« Extraire les adresses »**. Chaque ticket est traité l'un après l'autre (lecture de l'image → OCR → IA → calcul de distance), une barre de progression indique l'avancement.
4. **Vérifier les résultats** dans le tableau — colonnes *Fichier*, *Adresse extraite*, *Distance* :
   - bouton **« Voir »** : afficher la photo du ticket pour contrôle ;
   - bouton **« Corriger »** : si une adresse est fausse ou introuvable, ouvrir la recherche de suggestions, sélectionner la bonne adresse et valider. La distance est alors recalculée automatiquement.
5. **Exporter** le rapport avec **« Exporter CSV »** ou **« Exporter Excel »**. L'application **demande dans quel dossier** enregistrer le fichier.

Le fichier généré (`rapport_csv_…csv` ou `rapport_excel_…xlsx`) contient les colonnes : **Adresse de départ**, **Adresse d'arrivée**, **Nom de l'entreprise**, **Distance (km)**, **A/R (km)**, **Date**. Le fichier Excel est déjà mis en forme (tableau, en-têtes, lignes en erreur surlignées).

Le bouton **« Effacer »** vide la liste pour repartir sur un nouveau lot de tickets.

---

## 5. En cas de problème

| Message / symptôme | Solution |
|---|---|
| « Ollama ne répond pas » | Vérifier qu'Ollama est installé et lancé. Windows : ouvrir l'application Ollama une fois. Linux : `ollama serve`. Puis relancer. |
| « Le modèle llama3.2 n'est pas installé » | Cliquer sur « Oui » quand l'application propose de le télécharger, ou lancer `ollama pull llama3.2`. |
| `command not found: py` / `python` | Python n'est pas installé ou pas dans le PATH. Réinstaller Python en cochant « Add Python to PATH » (Windows). Sur Linux la commande est `python` ou `python3`. |
| Premier lancement très long | Normal : téléchargement des bibliothèques et du modèle d'IA. Cela n'arrive qu'une fois. |
| Une adresse est mal lue | Utiliser le bouton « Corriger » sur la ligne concernée pour choisir la bonne adresse. |
| Distance affichée « N/A » | L'adresse n'a pas pu être localisée : la corriger via « Corriger », et vérifier la connexion internet. |

---

## 6. Comment ça marche (résumé technique)

Chaîne de traitement, entièrement avec des outils gratuits et open source :

1. **Prétraitement de l'image** — OpenCV (nettoyage, redressement).
2. **OCR** — EasyOCR (lecture du texte du ticket).
3. **Extraction de l'adresse** — modèle d'IA `llama3.2` exécuté en local via Ollama.
4. **Distance** — géocodage Nominatim + itinéraire routier OSRM (services OpenStreetMap gratuits).
5. **Export** — rapport CSV ou Excel mis en forme.

Interface graphique : PyQt6.
