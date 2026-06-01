#!/usr/bin/env bash
# Receipt Reader - lanceur unique (Linux / Arch / Ubuntu / macOS)
# Une seule commande : la 1ere fois ca installe tout, ensuite ca lance direct.
#   chmod +x run.sh   (une seule fois)
#   ./run.sh
set -euo pipefail
cd "$(dirname "$0")"

# --- Choix de l'interpreteur Python ---
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "!! Python n'est pas installe."
  echo "   Arch   : sudo pacman -S python"
  echo "   Ubuntu : sudo apt install python3 python3-venv"
  echo "   (ou machine vierge : lance 'bash install.sh')"
  exit 1
fi

# --- 1. venv + dependances (premiere fois seulement) ---
if [ ! -d "venv" ]; then
  echo ">> Premier lancement : creation de l'environnement Python..."
  "$PY" -m venv venv
  source venv/bin/activate
  python -m pip install --upgrade pip >/dev/null
  echo ">> Installation des dependances (quelques minutes, EasyOCR + torch c'est lourd)..."
  python -m pip install -r requirements.txt
else
  source venv/bin/activate
  # venv deja present mais peut-etre incomplet : on verifie une dependance cle
  if ! python -c "import requests, PyQt6, easyocr" >/dev/null 2>&1; then
    echo ">> Environnement incomplet, (re)installation des dependances..."
    python -m pip install --upgrade pip >/dev/null
    python -m pip install -r requirements.txt
  fi
fi

# --- 2. Ollama installe ? ---
if ! command -v ollama >/dev/null 2>&1; then
  echo ""
  echo "!! Ollama n'est pas installe. Installe-le puis relance ./run.sh :"
  echo "   Arch   : sudo pacman -S ollama"
  echo "   Ubuntu : curl -fsSL https://ollama.com/install.sh | sh"
  echo "   Windows: https://ollama.com/download"
  exit 1
fi

# --- 3. Serveur Ollama demarre ? ---
if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
  echo ">> Demarrage du serveur Ollama..."
  ollama serve >/tmp/receipt-reader-ollama.log 2>&1 &
  for _ in $(seq 1 30); do
    curl -s http://localhost:11434/api/tags >/dev/null 2>&1 && break
    sleep 1
  done
fi

# --- 4. Modele present ? ---
if ! ollama list | grep -q "llama3.2"; then
  echo ">> Telechargement du modele llama3.2 (~2 Go, une seule fois)..."
  ollama pull llama3.2
fi

# --- 5. Lancement ---
echo ">> Lancement de receiptReader..."
python app.py
