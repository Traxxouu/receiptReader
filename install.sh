#!/usr/bin/env bash

# Receipt Reader - installation Linux simple
# Usage conseillé :
#   git clone https://github.com/Traxxouu/receiptReader.git
#   cd receiptReader
#   bash install.sh
#
# Le script fonctionne aussi depuis une archive ou via curl si le dépôt
# n'est pas déjà cloné localement.

set -euo pipefail

REPO_URL="https://github.com/Traxxouu/receiptReader.git"
APP_NAME="receipt-reader"
MODEL_NAME="${OLLAMA_MODEL:-llama3.2}"

log() { printf '\n[Receipt Reader] %s\n' "$1"; }
die() { printf '\n[Erreur] %s\n' "$1" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }

detect_python() {
    if have python3; then
        printf '%s\n' "python3"
    elif have python; then
        printf '%s\n' "python"
    else
        return 1
    fi
}

detect_app_dir() {
    if [ -f "./app.py" ] && [ -f "./requirements.txt" ]; then
        pwd
    else
        printf '%s/%s\n' "$HOME" "$APP_NAME"
    fi
}

APP_DIR="$(detect_app_dir)"

install_packages_apt() {
    sudo apt-get update -y
    sudo apt-get install -y python3 python3-venv python3-pip git curl
}

install_packages_pacman() {
    sudo pacman -Sy --noconfirm --needed python python-pip git curl
}

install_system_dependencies() {
    if detect_python >/dev/null 2>&1 && have git && have curl; then
        log "Python3, git et curl sont deja disponibles"
        return
    fi

    if have apt-get; then
        log "Installation des dependances systeme via apt"
        install_packages_apt
    elif have pacman; then
        log "Installation des dependances systeme via pacman"
        install_packages_pacman
    else
        die "Gestionnaire de paquets non supporte. Installe Python 3, git et curl manuellement puis relance le script."
    fi
}

prepare_repo() {
    if [ -f "$APP_DIR/app.py" ]; then
        log "Dossier projet detecte : $APP_DIR"
        if [ -d "$APP_DIR/.git" ]; then
            log "Mise a jour du depot"
            git -C "$APP_DIR" pull --ff-only || true
        fi
        return
    fi

    log "Clonage du depot dans $APP_DIR"
    rm -rf "$APP_DIR"
    git clone "$REPO_URL" "$APP_DIR"
}

create_venv_and_install_python_deps() {
    log "Creation de l'environnement virtuel"
    cd "$APP_DIR"
    local python_bin
    python_bin="$(detect_python || true)"
    if [ -z "$python_bin" ]; then
        die "Python introuvable apres installation des dependances systeme"
    fi
    "$python_bin" -m venv venv
    # shellcheck disable=SC1091
    source venv/bin/activate
    python -m pip install --upgrade pip >/dev/null
    python -m pip install -r requirements.txt
    deactivate
}

ensure_ollama() {
    if have ollama; then
        log "Ollama est deja installe"
        return
    fi

    log "Installation d'Ollama"
    if ! have curl; then
        die "curl est requis pour installer Ollama automatiquement"
    fi
    curl -fsSL https://ollama.com/install.sh | sh
}

pull_model() {
    log "Telechargement du modele IA : $MODEL_NAME"
    ollama pull "$MODEL_NAME"
}

create_launcher() {
    log "Creation du lanceur"
    cat > "$APP_DIR/start.sh" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd "\$(dirname "\$0")"
if ! pgrep -x ollama >/dev/null 2>&1; then
    ollama serve >/tmp/receipt-reader-ollama.log 2>&1 &
    sleep 2
fi
# shellcheck disable=SC1091
source venv/bin/activate
python app.py
EOF
    chmod +x "$APP_DIR/start.sh"
}

create_desktop_entry() {
    local desktop_dir="${XDG_DESKTOP_DIR:-$HOME/Desktop}"
    local app_dir="$APP_DIR"
    local applications_dir="$HOME/.local/share/applications"

    mkdir -p "$applications_dir"

    cat > "$applications_dir/receipt-reader.desktop" <<EOF
[Desktop Entry]
Name=Receipt Reader
Comment=Extraction d'adresses de tickets de caisse
Exec=bash $app_dir/start.sh
Path=$app_dir
Terminal=false
Type=Application
Categories=Utility;
EOF

    if [ -d "$desktop_dir" ]; then
        cp "$applications_dir/receipt-reader.desktop" "$desktop_dir/receipt-reader.desktop" 2>/dev/null || true
        chmod +x "$desktop_dir/receipt-reader.desktop" 2>/dev/null || true
    fi
}

main() {
    log "Installation de Receipt Reader"
    install_system_dependencies
    prepare_repo
    create_venv_and_install_python_deps
    ensure_ollama
    pull_model
    create_launcher
    create_desktop_entry

    cat <<EOF

Installation terminee.

Lancement :
  cd "$APP_DIR"
  bash start.sh

Le script a installe et prepare :
  - Python 3 et les dependances systeme
  - l'environnement virtuel local
  - les dependances Python du projet
  - Ollama et le modele $MODEL_NAME
  - un lanceur local start.sh

EOF
}

main "$@"
