#!/bin/bash

# ─────────────────────────────────────────────
# Receipt Reader - Installateur Linux/Ubuntu
# Usage : curl -fsSL https://raw.githubusercontent.com/Traxxouu/receiptReader/main/install.sh | bash
# ─────────────────────────────────────────────

set -e

REPO="https://github.com/Traxxouu/receiptReader"
INSTALL_DIR="$HOME/receipt-reader"
PYTHON_MIN="3.10"

echo ""
echo "╔══════════════════════════════════════╗"
echo "║        Receipt Reader - Install      ║"
echo "╚══════════════════════════════════════╝"
echo ""

# ── 1. Vérifier Python
echo "[1/5] Vérification de Python..."
if ! command -v python3 &>/dev/null; then
    echo "     Python3 non trouvé. Installation..."
    sudo apt-get update -qq
    sudo apt-get install -y python3 python3-pip python3-venv
else
    echo "     Python3 trouvé : $(python3 --version)"
fi

# ── 2. Vérifier Git
echo "[2/5] Vérification de Git..."
if ! command -v git &>/dev/null; then
    echo "     Git non trouvé. Installation..."
    sudo apt-get install -y git
else
    echo "     Git trouvé."
fi

# ── 3. Cloner ou mettre à jour le repo
echo "[3/5] Téléchargement de Receipt Reader..."
if [ -d "$INSTALL_DIR" ]; then
    echo "     Mise à jour..."
    cd "$INSTALL_DIR"
    git pull origin main
else
    git clone "$REPO" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# ── 4. Environnement virtuel + dépendances Python
echo "[4/5] Installation des dépendances Python..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
deactivate

# ── 5. Installer Ollama + modèle
echo "[5/5] Installation d'Ollama et du modèle IA..."
if ! command -v ollama &>/dev/null; then
    echo "     Installation d'Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo "     Ollama déjà installé."
fi

echo "     Téléchargement du modèle llama3.2 (peut prendre quelques minutes)..."
ollama pull llama3.2

# ── Créer le lanceur
cat > "$INSTALL_DIR/start.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
ollama serve &>/dev/null &
sleep 2
python app.py
EOF
chmod +x "$INSTALL_DIR/start.sh"

# ── Créer un raccourci bureau si possible
DESKTOP="$HOME/Desktop"
if [ -d "$DESKTOP" ]; then
    cat > "$DESKTOP/ReceiptReader.desktop" << EOF
[Desktop Entry]
Name=Receipt Reader
Comment=Extraction d'adresses de tickets de caisse
Exec=bash $INSTALL_DIR/start.sh
Terminal=false
Type=Application
EOF
    chmod +x "$DESKTOP/ReceiptReader.desktop"
    echo ""
    echo "     Raccourci créé sur le bureau."
fi

echo ""
echo "╔══════════════════════════════════════╗"
echo "║   Installation terminée avec succes  ║"
echo "╚══════════════════════════════════════╝"
echo ""
echo "  Pour lancer l'application :"
echo "  bash $INSTALL_DIR/start.sh"
echo ""
