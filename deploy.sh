#!/usr/bin/env bash
# =============================================================================
# deploy.sh — Script de déploiement MINER sur VPS Linux (Ubuntu)
# =============================================================================
# Usage (depuis /home/ubuntu/Projets_en_Production/MINER/) :
#   bash deploy.sh
#
# Ce script :
#   1. Installe les dépendances système (Python 3, pip, rsync)
#   2. Installe Ollama et télécharge le modèle deepseek-r1:8b
#   3. Installe le virtualenv dans /home/ubuntu/Projets_en_Production/MINER
#   4. Crée l'environnement virtuel Python et installe les dépendances
#   5. Installe les 3 services systemd (démarrage auto, restart on failure)
#   6. Vérifie la présence des fichiers secrets (.env et cles_google.json.json)
# =============================================================================

set -euo pipefail

INSTALL_DIR="/home/ubuntu/Projets_en_Production/MINER"
SERVICE_USER="ubuntu"
LOG_DIR="/var/log/miner"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Couleurs ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# =============================================================================
# ÉTAPE 1 — Dépendances système
# =============================================================================
info "Mise à jour et installation des dépendances système…"
sudo apt-get update -q
sudo apt-get install -y -q python3 python3-venv python3-pip rsync curl

# =============================================================================
# ÉTAPE 2 — Ollama
# =============================================================================
if ! command -v ollama &>/dev/null; then
    info "Installation d'Ollama…"
    curl -fsSL https://ollama.com/install.sh | sh
    sudo systemctl enable ollama
    sudo systemctl start ollama
    sleep 5
else
    info "Ollama déjà installé."
    sudo systemctl start ollama || true
fi

info "Téléchargement du modèle deepseek-r1:8b (peut prendre plusieurs minutes)…"
ollama pull deepseek-r1:8b || warn "Échec du pull — relancer manuellement : ollama pull deepseek-r1:8b"

# =============================================================================
# ÉTAPE 3 — Copie du projet dans /home/ubuntu/miner
# =============================================================================
info "Déploiement des fichiers dans $INSTALL_DIR…"
mkdir -p "$INSTALL_DIR"
rsync -a --exclude='.venv' --exclude='__pycache__' --exclude='*.pyc' \
         --exclude='*.log' --exclude='.monitor_*.json' --exclude='.monitor_state.json' \
         "$SCRIPT_DIR/" "$INSTALL_DIR/"

# =============================================================================
# ÉTAPE 4 — Environnement virtuel Python
# =============================================================================
info "Création de l'environnement virtuel Python…"
python3 -m venv "$INSTALL_DIR/.venv"
"$INSTALL_DIR/.venv/bin/pip" install --upgrade pip -q
"$INSTALL_DIR/.venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt" -q
info "Dépendances Python installées."

# =============================================================================
# ÉTAPE 5 — Dossier de logs
# =============================================================================
sudo mkdir -p "$LOG_DIR"
sudo chown "$SERVICE_USER:$SERVICE_USER" "$LOG_DIR"

# =============================================================================
# ÉTAPE 6 — Services systemd
# =============================================================================
info "Installation des services systemd…"
sudo cp "$INSTALL_DIR/systemd/miner-main.service"      /etc/systemd/system/
sudo cp "$INSTALL_DIR/systemd/miner-diffusion.service" /etc/systemd/system/
sudo cp "$INSTALL_DIR/systemd/miner-exclusion.service" /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable miner-main miner-diffusion miner-exclusion
info "Services systemd installés et activés."

# =============================================================================
# ÉTAPE 7 — Vérification des fichiers secrets
# =============================================================================
echo ""
info "=== Vérification des fichiers secrets ==="

if [[ ! -f "$INSTALL_DIR/.env" ]]; then
    warn ".env MANQUANT — copier et remplir avant de démarrer :"
    warn "  cp $INSTALL_DIR/.env.example $INSTALL_DIR/.env"
    warn "  nano $INSTALL_DIR/.env"
else
    info ".env présent."
    chmod 600 "$INSTALL_DIR/.env"
fi

if [[ ! -f "$INSTALL_DIR/cles_google.json.json" ]]; then
    warn "cles_google.json.json MANQUANT — transférer le fichier :"
    warn "  scp cles_google.json.json ubuntu@VPS_IP:$INSTALL_DIR/"
else
    info "cles_google.json.json présent."
    chmod 600 "$INSTALL_DIR/cles_google.json.json"
fi

# =============================================================================
# RÉSUMÉ
# =============================================================================
echo ""
info "=== Déploiement terminé ==="
echo ""
echo "  Répertoire d'installation : $INSTALL_DIR"
echo "  Logs                      : $LOG_DIR"
echo ""
echo "  Après avoir copié .env et cles_google.json.json, démarrer les services :"
echo ""
echo "    sudo systemctl start miner-main"
echo "    sudo systemctl start miner-diffusion"
echo "    sudo systemctl start miner-exclusion"
echo ""
echo "  Vérifier le statut :"
echo "    sudo systemctl status miner-main"
echo "    tail -f /var/log/miner/monitor_main.log"
echo ""
