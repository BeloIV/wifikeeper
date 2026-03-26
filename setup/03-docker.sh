#!/bin/bash
# 03-docker.sh - Docker inštalácia
# Spusti ako: bash 03-docker.sh

set -e

echo "=== 03-docker.sh: Docker inštalácia ==="

# --- GPG kľúč ---
echo "[1/4] Pridávam Docker GPG kľúč..."
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
    sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "GPG kľúč pridaný ✓"

# --- Repository ---
echo "[2/4] Pridávam Docker repository..."
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
echo "Repository pridaný ✓"

# --- Inštalácia ---
echo "[3/4] Inštalujem Docker..."
sudo apt install -y \
    docker-ce \
    docker-ce-cli \
    containerd.io \
    docker-buildx-plugin \
    docker-compose-plugin
echo "Docker nainštalovaný ✓"

# --- User do docker skupiny ---
echo "[4/4] Pridávam usera do docker skupiny..."
CURRENT_USER="${SUDO_USER:-$USER}"
sudo usermod -aG docker "$CURRENT_USER"
echo "User $CURRENT_USER pridaný do skupiny docker ✓"

# --- Test ---
sudo docker run hello-world

echo ""
echo "=== 03-docker.sh HOTOVO ==="
echo "⚠️  Odhláš sa a prihlás znova (logout) aby docker fungoval bez sudo"
echo "Pokračuj: bash 04-certbot.sh"
