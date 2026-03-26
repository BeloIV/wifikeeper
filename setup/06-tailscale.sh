#!/bin/bash
# 06-tailscale.sh - Tailscale inštalácia
# Spusti ako: bash 06-tailscale.sh

set -e

echo "=== 06-tailscale.sh: Tailscale ==="

TAILSCALE_AUTHKEY="${CFG_TAILSCALE_AUTHKEY:-}"

# --- Inštalácia ---
echo "[1/3] Inštalujem Tailscale..."
curl -fsSL https://tailscale.com/install.sh | sh
echo "Tailscale nainštalovaný ✓"

# --- Povolenie IP forwardingu (pre subnet router ak treba) ---
echo "[2/3] Povolujem IP forwarding..."
echo 'net.ipv4.ip_forward = 1' | sudo tee -a /etc/sysctl.d/99-tailscale.conf > /dev/null
echo 'net.ipv6.conf.all.forwarding = 1' | sudo tee -a /etc/sysctl.d/99-tailscale.conf > /dev/null
sudo sysctl -p /etc/sysctl.d/99-tailscale.conf > /dev/null
echo "IP forwarding povolený ✓"

# --- Prihlásenie ---
echo "[3/3] Prihlasovanie do Tailscale..."
if [ -n "$TAILSCALE_AUTHKEY" ]; then
  sudo tailscale up --authkey "$TAILSCALE_AUTHKEY" --ssh
  echo "Tailscale pripojený cez auth key ✓"
else
  echo ""
  echo "  ┌─────────────────────────────────────────────────────┐"
  echo "  │  Prihlás sa do Tailscale:                           │"
  echo "  │  1. Skopíruj link ktorý sa zobrazí nižšie           │"
  echo "  │  2. Otvor ho v prehliadači na svojom počítači        │"
  echo "  │  3. Potvrď prihlásenie – skript pokračuje sám        │"
  echo "  └─────────────────────────────────────────────────────┘"
  echo ""
  sudo tailscale up --ssh
fi

echo ""
echo "Tailscale IP: $(tailscale ip -4 2>/dev/null || echo 'zistíš po prihlásení')"
echo ""
echo "=== 06-tailscale.sh HOTOVO ==="
