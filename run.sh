#!/usr/bin/env bash
# Receipt Reader - lanceur unique (Linux / Ubuntu / Arch)
#   chmod +x run.sh   (une seule fois)
#   ./run.sh
set -euo pipefail
cd "$(dirname "$0")"

# --- Couleurs ---
GREEN='\033[92m'; PINK='\033[95m'; CYAN='\033[96m'; RED='\033[91m'; BOLD='\033[1m'; RESET='\033[0m'

# --- Choix de l'interpreteur Python ---
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo -e "${RED}!! Python n'est pas installe.${RESET}"
  echo "   Ubuntu : sudo apt install python3 python3-venv"
  echo "   Arch   : sudo pacman -S python"
  echo "   (machine vierge : lance 'bash install.sh')"
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
  if ! python -c "import requests, PyQt6, easyocr" >/dev/null 2>&1; then
    echo ">> Environnement incomplet, (re)installation des dependances..."
    python -m pip install --upgrade pip >/dev/null
    python -m pip install -r requirements.txt
  fi
fi

# --- 2. Ollama installe ? ---
OLLAMA_OK=0
if command -v ollama >/dev/null 2>&1; then OLLAMA_OK=1; fi

# --- 3. Serveur Ollama demarre ? ---
SERVER_OK=0
if [ "$OLLAMA_OK" = "1" ]; then
  if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo ">> Demarrage du serveur Ollama..."
    ollama serve >/tmp/receipt-reader-ollama.log 2>&1 &
    for _ in $(seq 1 30); do
      curl -s http://localhost:11434/api/tags >/dev/null 2>&1 && break
      sleep 1
    done
  fi
  curl -s http://localhost:11434/api/tags >/dev/null 2>&1 && SERVER_OK=1
fi

# --- 4. Modele present ? ---
MODEL_OK=0
if [ "$SERVER_OK" = "1" ]; then
  if ! ollama list | grep -q "llama3.2"; then
    echo ">> Telechargement du modele llama3.2 (~2 Go, une seule fois)..."
    ollama pull llama3.2
  fi
  ollama list | grep -q "llama3.2" && MODEL_OK=1
fi

# --- 5. Ecran final ---
clear
echo ""
echo -e "${GREEN}${BOLD}  ============================================${RESET}"
echo -e "${GREEN}${BOLD}            INSTALLATION TERMINEE${RESET}"
echo -e "${GREEN}${BOLD}  ============================================${RESET}"
echo ""
if [ "$OLLAMA_OK" = "1" ]; then
  echo -e "${PINK}   [OK] Ollama est installe sur ta machine.${RESET}"
else
  echo -e "${RED}   [X] Ollama n'est PAS installe : curl -fsSL https://ollama.com/install.sh | sh${RESET}"
fi
if [ "$SERVER_OK" = "1" ]; then
  echo -e "${PINK}   [OK] Le serveur Ollama tourne (port 11434).${RESET}"
else
  echo -e "${RED}   [X] Le serveur Ollama ne repond pas.${RESET}"
fi
if [ "$MODEL_OK" = "1" ]; then
  echo -e "${PINK}   [OK] Le modele llama3.2 est present.${RESET}"
else
  echo -e "${RED}   [X] Le modele llama3.2 est absent : ollama pull llama3.2${RESET}"
fi
echo ""
echo -e "${CYAN}${BOLD}   Pour lancer l'application, tape :${RESET}"
echo ""
echo -e "${CYAN}${BOLD}        python app.py${RESET}"
echo ""
echo "   (puis Entree)"
echo ""

# --- 6. Shell pret : venv deja active, bon dossier ---
exec bash --init-file <(echo "source venv/bin/activate; cd '$(pwd)'")