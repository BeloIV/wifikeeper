#!/bin/bash
# setup.sh – wifikeeper onboarding entry point
# Spusti ako: bash setup.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Farby ──────────────────────────────────────────────────────
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; }
info() { echo -e "  ${CYAN}→${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }

ask() {
  local prompt="$1"
  local default="$2"
  local var_name="$3"
  local secret="${4:-}"
  if [ -n "$secret" ]; then
    read -s -p "  $prompt: " input
    echo ""
  else
    read -p "  $prompt${default:+ [${default}]}: " input
  fi
  eval "$var_name='${input:-$default}'"
}

# ── Banner ─────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║      wifikeeper – Server Onboarding      ║${NC}"
echo -e "${BOLD}║      WPA2 Enterprise WiFi správca        ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════╝${NC}"
echo ""

# ── 1. Konfigurácia ────────────────────────────────────────────
echo -e "${BOLD}── 1. Konfigurácia ───────────────────────────────────────${NC}"
echo ""

echo "  Sieť:"
ask "Hostname servera" "wifikeeper" CFG_HOSTNAME
ask "Statická IP servera" "192.168.1.222" CFG_STATIC_IP
ask "Gateway (IP routera)" "192.168.1.1" CFG_GATEWAY

DEFAULT_IFACE=$(ip route 2>/dev/null | grep default | awk '{print $5}' | head -1)
ask "Sieťový interface" "${DEFAULT_IFACE:-enp1s0}" CFG_INTERFACE

echo ""
echo "  Doména a certifikát:"
ask "Doména" "radius.oratko.sk" CFG_DOMAIN
ask "Email pre Let's Encrypt" "admin@oratko.sk" CFG_EMAIL
ask "Cloudflare API token" "" CFG_CF_TOKEN secret

echo ""
echo "  UniFi / RADIUS:"
warn "Ak nepoznáš IP UniFi controllera, nechaj prázdne (povolí RADIUS pre všetkých – doriešiš neskôr)"
ask "IP UniFi controllera" "" CFG_UNIFI_IP

echo ""
echo "  Tailscale:"
warn "Auth key nájdeš na https://login.tailscale.com/admin/settings/keys (reusable, expiry podľa potreby)"
warn "Ak necháš prázdne, skript zobrazí link pre manuálne prihlásenie v prehliadači"
ask "Tailscale auth key (voliteľné)" "" CFG_TAILSCALE_AUTHKEY secret

echo ""
echo "  Projekt:"
ask "Cesta kde bude wifi-manager" "/opt/wifi-manager" CFG_PROJECT_DIR

echo ""

# Export pre child skripty
export CFG_HOSTNAME CFG_STATIC_IP CFG_GATEWAY CFG_INTERFACE
export CFG_DOMAIN CFG_EMAIL CFG_CF_TOKEN CFG_UNIFI_IP
export CFG_TAILSCALE_AUTHKEY CFG_PROJECT_DIR

# ── 2. Kontrola stavu ──────────────────────────────────────────
echo -e "${BOLD}── 2. Kontrola stavu ─────────────────────────────────────${NC}"
echo ""

NEED_BASE=false
NEED_FIREWALL=false
NEED_DOCKER=false
NEED_CERTBOT=false
NEED_SSH=false
NEED_TAILSCALE=false

# Hostname
if [ "$(hostname)" = "$CFG_HOSTNAME" ]; then
  ok "Hostname: $(hostname)"
else
  fail "Hostname: $(hostname) → nastavím na $CFG_HOSTNAME"
  NEED_BASE=true
fi

# Statická IP
if ip addr show 2>/dev/null | grep -q "$CFG_STATIC_IP"; then
  ok "Statická IP: $CFG_STATIC_IP"
else
  fail "Statická IP $CFG_STATIC_IP: nenájdená → nastavím"
  NEED_BASE=true
fi

# UFW
if sudo ufw status 2>/dev/null | grep -q "Status: active"; then
  ok "UFW firewall: aktívny"
else
  fail "UFW firewall: neaktívny → nastavím"
  NEED_FIREWALL=true
fi

# Docker
if command -v docker &>/dev/null; then
  ok "Docker: $(docker --version 2>/dev/null | grep -oP 'version \K[^,]+')"
else
  fail "Docker: nenájdený → nainštalujem"
  NEED_DOCKER=true
fi

# Certbot + certifikát
if command -v certbot &>/dev/null; then
  ok "Certbot: nainštalovaný"
  if sudo certbot certificates 2>/dev/null | grep -q "$CFG_DOMAIN"; then
    ok "Certifikát pre $CFG_DOMAIN: existuje"
  else
    fail "Certifikát pre $CFG_DOMAIN: neexistuje → vydám"
    NEED_CERTBOT=true
  fi
else
  fail "Certbot: nenájdený → nainštalujem"
  NEED_CERTBOT=true
fi

# SSH hardening
if [ -f /etc/ssh/sshd_config.d/hardening.conf ]; then
  ok "SSH hardening: nastavený"
else
  fail "SSH hardening: nenastavený → nastavím"
  NEED_SSH=true
fi

# Tailscale
if command -v tailscale &>/dev/null && tailscale status &>/dev/null; then
  ok "Tailscale: $(tailscale ip -4 2>/dev/null)"
else
  fail "Tailscale: nenájdený alebo nepripojený → nainštalujem"
  NEED_TAILSCALE=true
fi

echo ""

# ── 3. Potvrdenie ──────────────────────────────────────────────
if ! $NEED_BASE && ! $NEED_FIREWALL && ! $NEED_DOCKER && ! $NEED_CERTBOT && ! $NEED_SSH && ! $NEED_TAILSCALE; then
  echo -e "  ${GREEN}Všetko je nastavené. Nič nerobím.${NC}"
  echo ""
  info "Ak chceš nasadiť projekt: cd $CFG_PROJECT_DIR && docker compose up -d"
  exit 0
fi

echo -e "${BOLD}── 3. Čo sa spustí ───────────────────────────────────────${NC}"
echo ""
$NEED_BASE       && info "01-base.sh          – hostname, systém, statická IP"
$NEED_FIREWALL   && info "02-firewall.sh      – UFW firewall"
$NEED_DOCKER     && info "03-docker.sh        – Docker"
$NEED_CERTBOT    && info "04-certbot.sh       – Certbot + Let's Encrypt"
$NEED_SSH        && info "05-ssh-hardening.sh – SSH (iba kľúč, bez hesla)"
$NEED_TAILSCALE  && info "06-tailscale.sh     – Tailscale VPN"
echo ""

if $NEED_SSH; then
  warn "05-ssh-hardening.sh zakáže prihlásenie heslom."
  warn "Uisti sa že máš SSH kľúč nastavený PRED pokračovaním!"
  echo ""
fi

read -p "  Pokračovať? [Y/n]: " CONFIRM
if [[ "${CONFIRM,,}" == "n" ]]; then
  echo "  Zrušené."
  exit 0
fi

echo ""

# ── 4. Spustenie ───────────────────────────────────────────────
echo -e "${BOLD}── 4. Inštalácia ─────────────────────────────────────────${NC}"
echo ""

$NEED_BASE      && bash "$SCRIPT_DIR/01-base.sh"
$NEED_FIREWALL  && bash "$SCRIPT_DIR/02-firewall.sh"
$NEED_DOCKER    && bash "$SCRIPT_DIR/03-docker.sh"
$NEED_CERTBOT   && bash "$SCRIPT_DIR/04-certbot.sh"
$NEED_SSH       && bash "$SCRIPT_DIR/05-ssh-hardening.sh"
$NEED_TAILSCALE && bash "$SCRIPT_DIR/06-tailscale.sh"

# ── 5. Záver ───────────────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║         Setup kompletný!                 ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════╝${NC}"
echo ""
echo "  Ďalší krok – nasadiť projekt:"
echo ""
echo "    git clone <repo> $CFG_PROJECT_DIR"
echo "    cd $CFG_PROJECT_DIR"
echo "    cp .env.example .env"
echo "    nano .env"
echo "    docker compose up -d"
echo ""
if [ -z "$CFG_UNIFI_IP" ]; then
  warn "RADIUS porty sú otvorené pre všetkých. Po zistení IP UniFi"
  warn "controllera spusti: bash setup/02-firewall.sh"
fi
echo ""
