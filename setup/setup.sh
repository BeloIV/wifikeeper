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

# ── Načítaj .env ak existuje ───────────────────────────────────
ENV_FILE="$(dirname "$SCRIPT_DIR")/.env"
if [ -f "$ENV_FILE" ]; then
  # Načítaj len riadky KEY=VALUE, preskočí komentáre a prázdne riadky
  set -a
  # shellcheck disable=SC1090
  source <(grep -E '^[A-Z_]+=.' "$ENV_FILE" | sed 's/[[:space:]]*#.*//')
  set +a
  info "Načítaný .env: $ENV_FILE"
fi

# ── Banner ─────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║      wifikeeper – Server Onboarding      ║${NC}"
echo -e "${BOLD}║      WPA2 Enterprise WiFi správca        ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════╝${NC}"
echo ""

# ── Prerekvizity ───────────────────────────────────────────────
echo -e "${BOLD}── Prerekvizity – pred spustením si priprav: ─────────────${NC}"
echo ""
echo -e "  ${GREEN}✔${NC}  ${BOLD}Doména prenesená na Cloudflare${NC}"
echo "     – Registruj doménu (napr. salezianipresov.xyz) kdekoľvek"
echo "     – V Cloudflare: Add site → zmeň nameservery u registrátora"
echo "     – Potrebuješ API token: dash.cloudflare.com → My Profile → API Tokens"
echo "     – Permissions: Zone:DNS:Edit + Zone:Zone:Read"
echo ""
echo -e "  ${GREEN}✔${NC}  ${BOLD}Tailscale účet${NC}  (tailscale.com – free tier stačí)"
echo "     – Auth key: tailscale.com/admin/settings/keys"
echo "     – Reusable key, expiry podľa potreby"
echo "     – Použiješ na bezpečný vzdialený prístup k serveru"
echo ""
echo -e "  ${GREEN}✔${NC}  ${BOLD}Brevo účet${NC}  (brevo.com – free: 300 emailov/deň)"
echo "     – Potrebuješ SMTP credentials: app.brevo.com → Transactional → SMTP & API"
echo "     – Login email + SMTP API kľúč (nie heslo od účtu)"
echo "     – Použiješ na spoľahlivé doručovanie emailov cez Stalwart mail server"
echo ""
echo -e "  ${GREEN}✔${NC}  ${BOLD}Email adresy – 2 druhy, nezamieňaj ich:${NC}"
echo -e "     – ${BOLD}Admin email (Let's Encrypt / Certbot)${NC}"
echo "       Môže byť akýkoľvek existujúci email (napr. tvoj Gmail)."
echo "       Let's Encrypt ti naň pošle upozornenie pred vypršaním certifikátu."
echo "       Nemusí byť na tvojej doméne."
echo ""
echo -e "     – ${BOLD}Odosielacia adresa (MAIL_FROM)${NC}"
echo "       Adresa z ktorej systém posiela emaily používateľom (napr. wifi@salezianipresov.xyz)."
echo "       MUSÍ byť na tvojej doméne – vytvoríš ju v Stalwart Admin UI po inštalácii."
echo ""
echo -e "  ${GREEN}✔${NC}  ${BOLD}DNS záznamy v Cloudflare${NC}  (nastav po inštalácii, pred spustením)"
echo "     Typ    Názov                              Hodnota"
echo "     ──────────────────────────────────────────────────────────────"
echo "     A      salezianipresov.xyz                ${SERVER_IP:-<IP servera>}  [Proxy ON]"
echo "     A      mail.salezianipresov.xyz            ${SERVER_IP:-<IP servera>}  [Proxy OFF – šedý mrak!]"
echo "     MX     salezianipresov.xyz                mail.salezianipresov.xyz  (priorita 10)"
echo "     TXT    salezianipresov.xyz                v=spf1 include:spf.brevo.com ~all"
echo "     TXT    _dmarc.salezianipresov.xyz          v=DMARC1; p=none; rua=mailto:admin@salezianipresov.xyz"
echo "     ──────────────────────────────────────────────────────────────"
echo -e "     ${YELLOW}⚠${NC}  mail.* MUSÍ mať Proxy vypnutý – inak Cloudflare blokuje SMTP porty!"
echo -e "     ${YELLOW}⚠${NC}  DKIM záznam nastav AŽ PO inštalácii:"
echo "       1. Spusti: docker compose up -d"
echo "       2. Otvor:  http://${SERVER_IP:-<IP servera>}:8080  (Stalwart Admin UI)"
echo "       3. Choď:   Directories → Domains → salezianipresov.xyz → DKIM"
echo "       4. Skopíruj vygenerovaný TXT záznam do Cloudflare DNS"
echo ""
echo -e "  ${YELLOW}◎${NC}  ${BOLD}Claude predplatné${NC}  (voliteľné – claude.ai/pricing)"
echo "     – Bez predplatného funguje Claude Code s API kľúčom (pay-as-you-go)"
echo "     – S predplatným Pro/Max máš zahrnuté kredity pre Claude Code"
echo ""
echo -e "  ${GREEN}✔${NC}  ${BOLD}SSH kľúč na tomto serveri${NC}"
echo "     – Skript 05-ssh-hardening.sh zakáže prihlásenie heslom"
echo "     – Uisti sa že máš kľúč v ~/.ssh/authorized_keys PRED pokračovaním"
echo ""

read -p "  Máš všetko pripravené? [Y/n]: " PREREQ
if [[ "${PREREQ,,}" == "n" ]]; then
  echo ""
  echo "  Priprav prerekvizity a spusti setup znova."
  exit 0
fi
echo ""

# ── 1. Konfigurácia ────────────────────────────────────────────
echo -e "${BOLD}── 1. Konfigurácia ───────────────────────────────────────${NC}"
echo ""

DEFAULT_IFACE=$(ip route 2>/dev/null | grep default | awk '{print $5}' | head -1)

echo "  Sieť:"
ask "Hostname servera"    "${CFG_HOSTNAME:-wifikeeper}"       CFG_HOSTNAME
ask "Statická IP servera" "${CFG_STATIC_IP:-${SERVER_IP:-192.168.1.222}}"  CFG_STATIC_IP
ask "Gateway (IP routera)" "${CFG_GATEWAY:-192.168.1.1}"     CFG_GATEWAY
ask "Sieťový interface"   "${CFG_INTERFACE:-${DEFAULT_IFACE:-enp1s0}}" CFG_INTERFACE

echo ""
echo "  Doména a certifikát:"
ask "Doména"                "${DOMAIN:-salezianipresov.xyz}"             CFG_DOMAIN
ask "Email pre Let's Encrypt" "${ADMIN_EMAIL:-admin@salezianipresov.xyz}" CFG_EMAIL
ask "Cloudflare API token"  "${CLOUDFLARE_API_TOKEN:-}"                  CFG_CF_TOKEN secret

echo ""
echo "  UniFi / RADIUS:"
warn "Ak nepoznáš IP UniFi controllera, nechaj prázdne (povolí RADIUS pre všetkých – doriešiš neskôr)"
ask "IP UniFi controllera" "${CFG_UNIFI_IP:-}" CFG_UNIFI_IP

echo ""
echo "  Tailscale:"
warn "Auth key nájdeš na https://login.tailscale.com/admin/settings/keys (reusable, expiry podľa potreby)"
warn "Ak necháš prázdne, skript zobrazí link pre manuálne prihlásenie v prehliadači"
ask "Tailscale auth key (voliteľné)" "${CFG_TAILSCALE_AUTHKEY:-}" CFG_TAILSCALE_AUTHKEY secret

echo ""

# Projekt je tam kde leží tento skript (setup/ je podadresár projektu)
CFG_PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

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
NEED_NODE=false
NEED_CLAUDE=false
NEED_ECC=false

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

# Node.js + Bun
if command -v node &>/dev/null && command -v bun &>/dev/null; then
  ok "Node.js: $(node --version), Bun: $(bun --version)"
else
  fail "Node.js / Bun: nenájdené → nainštalujem"
  NEED_NODE=true
fi

# Claude Code (vždy spustí 08-claude-dev.sh – je idempotentný)
if command -v claude &>/dev/null; then
  ok "Claude Code: $(claude --version 2>/dev/null || echo 'ok')"
else
  fail "Claude Code: nenájdený → nainštalujem"
fi
NEED_CLAUDE=true

# everything-claude-code (vždy spustí 09 – je idempotentný)
ECC_AGENT_COUNT=$(ls "$HOME/.claude/agents/"*.md 2>/dev/null | wc -l)
if [ "$ECC_AGENT_COUNT" -ge 20 ]; then
  ok "everything-claude-code: ${ECC_AGENT_COUNT} agentov nainštalovaných"
else
  fail "everything-claude-code: nenainštalovaný → nainštalujem"
fi
NEED_ECC=true

echo ""

# ── 3. Potvrdenie ──────────────────────────────────────────────
if ! $NEED_BASE && ! $NEED_FIREWALL && ! $NEED_DOCKER && ! $NEED_CERTBOT && ! $NEED_SSH && ! $NEED_TAILSCALE && ! $NEED_NODE; then
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
$NEED_SSH        && info "05-ssh-hardening.sh – SSH hardening (bez root loginu)"
$NEED_TAILSCALE  && info "06-tailscale.sh     – Tailscale VPN"
$NEED_NODE       && info "07-node.sh          – Node.js LTS"
                    info "08-claude-dev.sh    – Claude Code CLI + claude-mem"
                    info "09-everything-claude-code.sh – agenty, príkazy, skills"
echo ""


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

# Self-signed cert pre dev (ak certbot nebeží a cert neexistuje)
if [ ! -f "$CFG_PROJECT_DIR/certs/server.crt" ]; then
  info "Generujem self-signed certifikát pre dev..."
  mkdir -p "$CFG_PROJECT_DIR/certs"
  openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$CFG_PROJECT_DIR/certs/server.key" \
    -out    "$CFG_PROJECT_DIR/certs/server.crt" \
    -subj "/CN=${CFG_HOSTNAME:-wifikeeper}/O=wifikeeper/C=SK" 2>/dev/null
  chmod 644 "$CFG_PROJECT_DIR/certs/server.crt"
  chmod 600 "$CFG_PROJECT_DIR/certs/server.key"
  ok "Self-signed certifikát vygenerovaný"
fi
$NEED_SSH       && bash "$SCRIPT_DIR/05-ssh-hardening.sh"
$NEED_TAILSCALE && bash "$SCRIPT_DIR/06-tailscale.sh"
$NEED_NODE      && bash "$SCRIPT_DIR/07-node.sh"
bash "$SCRIPT_DIR/08-claude-dev.sh"
bash "$SCRIPT_DIR/09-everything-claude-code.sh"

# ── Stalwart mailboxy ──────────────────────────────────────────
if command -v docker &>/dev/null && docker compose -f "$CFG_PROJECT_DIR/docker-compose.yml" ps stalwart 2>/dev/null | grep -q "running"; then
  info "Stalwart beží – vytváram mailboxy..."
  bash "$SCRIPT_DIR/10-stalwart-mailboxes.sh"
else
  warn "Stalwart nebeží – mailboxy vytvoríš manuálne po spustení docker compose:"
  info "  bash setup/10-stalwart-mailboxes.sh"
fi

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
