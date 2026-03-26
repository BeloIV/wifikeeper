#!/bin/bash
# 05-ssh-hardening.sh - Zabezpečenie SSH
# Spusti ako: bash 05-ssh-hardening.sh
# ⚠️  Spusti AŽ po tom čo máš SSH kľúč nastavený!

set -e

echo "=== 05-ssh-hardening.sh: SSH hardening ==="

echo "[1/2] Nastavujem SSH konfiguráciu..."
sudo tee /etc/ssh/sshd_config.d/hardening.conf > /dev/null <<EOF
# Zakáž prihlásenie heslom (iba SSH kľúč)
PasswordAuthentication no

# Zakáž root login
PermitRootLogin no

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
echo "⚠️  Od teraz funguje prihlásenie IBA cez SSH kľúč!"
echo "   Heslo nebude fungovať."
echo ""
echo "=== 05-ssh-hardening.sh HOTOVO ==="
echo ""
echo "🎉 Základný setup servera wifikeeper je kompletný!"
echo ""
echo "Ďalší krok: nasadiť wifi-manager projekt (docker compose up)"
