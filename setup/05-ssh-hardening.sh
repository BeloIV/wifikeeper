#!/bin/bash
# 05-ssh-hardening.sh - Zabezpečenie SSH
# Spusti ako: bash 05-ssh-hardening.sh

set -e

echo "=== 05-ssh-hardening.sh: SSH hardening ==="

echo "[1/2] Nastavujem SSH konfiguráciu..."
sudo tee /etc/ssh/sshd_config.d/hardening.conf > /dev/null <<EOF
# Len IPv4
AddressFamily inet

# Timeout nečinného spojenia (15 min)
ClientAliveInterval 900
ClientAliveCountMax 0
EOF

echo "SSH konfigurácia nastavená ✓"

# --- Reštart SSH ---
echo "[2/2] Reštartujem SSH..."
sudo systemctl restart ssh
echo "SSH reštartovaný ✓"

echo ""
echo "=== 05-ssh-hardening.sh HOTOVO ==="
echo ""
echo "Ďalší krok: nasadiť wifi-manager projekt (docker compose up)"
