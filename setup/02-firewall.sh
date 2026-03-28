#!/bin/bash
# 02-firewall.sh - UFW Firewall setup
# Spusti ako: bash 02-firewall.sh

set -e

echo "=== 02-firewall.sh: Firewall setup ==="

# --- Reset firewall ---
echo "[1/3] Resetujem UFW..."
sudo ufw --force reset

# --- Pravidlá ---
echo "[2/3] Nastavujem pravidlá..."

# SSH - dôležité! Najprv inak sa zamkneš von
sudo ufw allow 22/tcp comment 'SSH'

# HTTP/HTTPS - pre admin panel + certbot
sudo ufw allow 80/tcp comment 'HTTP'
sudo ufw allow 443/tcp comment 'HTTPS'

# Mail server (Stalwart) - len v produkcii
# Port 8181 (Admin UI) zámerne NEotvárame navonok - prístup cez Tailscale/VPN
sudo ufw allow 25/tcp   comment 'SMTP inbound'
sudo ufw allow 587/tcp  comment 'SMTP submission'
sudo ufw allow 143/tcp  comment 'IMAP'
sudo ufw allow 993/tcp  comment 'IMAPS'

# UniFi Network Application
sudo ufw allow 8443/tcp  comment 'UniFi Web UI (HTTPS)'
sudo ufw allow 8080/tcp  comment 'UniFi AP → controller'
sudo ufw allow 3478/udp  comment 'UniFi STUN'
sudo ufw allow 10001/udp comment 'UniFi AP discovery'
sudo ufw allow 6789/tcp  comment 'UniFi mobile speed test'

# RADIUS - porty pre UniFi AP-čka
UNIFI_IP="${CFG_UNIFI_IP:-}"
if [ -n "$UNIFI_IP" ]; then
  sudo ufw allow from "$UNIFI_IP" to any port 1812 proto udp comment 'RADIUS Auth (UniFi)'
  sudo ufw allow from "$UNIFI_IP" to any port 1813 proto udp comment 'RADIUS Acct (UniFi)'
  echo "RADIUS porty povolené len pre $UNIFI_IP ✓"
else
  sudo ufw allow 1812/udp comment 'RADIUS Auth (allow all – TODO: restrict to UniFi IP)'
  sudo ufw allow 1813/udp comment 'RADIUS Acct (allow all – TODO: restrict to UniFi IP)'
  echo "RADIUS porty povolené pre všetkých (doriešiť neskôr) ✓"
fi

# --- Zapni firewall ---
echo "[3/3] Zapínam firewall..."
sudo ufw --force enable

sudo ufw status verbose

echo ""
echo "=== 02-firewall.sh HOTOVO ==="
echo "Pokračuj: bash 03-docker.sh"
