#!/bin/bash
# 01-base.sh - Základný server setup
# Spusti ako: bash 01-base.sh

set -e  # zastav pri chybe

echo "=== 01-base.sh: Základný setup ==="

# --- Premenné (z setup.sh alebo defaults) ---
HOSTNAME="${CFG_HOSTNAME:-wifikeeper}"
STATIC_IP="${CFG_STATIC_IP:-192.168.1.222}"
GATEWAY="${CFG_GATEWAY:-192.168.1.1}"
INTERFACE="${CFG_INTERFACE:-enp1s0}"
DNS1="8.8.8.8"
DNS2="1.1.1.1"

# --- Hostname ---
echo "[1/4] Nastavujem hostname..."
sudo hostnamectl set-hostname "$HOSTNAME"
echo "Hostname: $HOSTNAME ✓"

# --- Update systému ---
echo "[2/4] Aktualizujem systém..."
sudo apt update && sudo apt upgrade -y
echo "Systém aktualizovaný ✓"

# --- Základné nástroje ---
echo "[3/4] Inštalujem základné nástroje..."
sudo apt install -y \
    curl \
    wget \
    git \
    nano \
    htop \
    net-tools \
    unzip \
    ca-certificates \
    gnupg \
    ufw
echo "Nástroje nainštalované ✓"

# --- Statická IP ---
echo "[4/4] Nastavujem statickú IP $STATIC_IP..."
NETPLAN_FILE="/etc/netplan/99-wifikeeper.yaml"

sudo tee "$NETPLAN_FILE" > /dev/null <<EOF
network:
  version: 2
  ethernets:
    $INTERFACE:
      dhcp4: no
      addresses:
        - $STATIC_IP/24
      routes:
        - to: default
          via: $GATEWAY
      nameservers:
        addresses: [$DNS1, $DNS2]
EOF

sudo netplan apply
echo "Statická IP $STATIC_IP nastavená ✓"

echo ""
echo "=== 01-base.sh HOTOVO ==="
echo "Pokračuj: bash 02-firewall.sh"
