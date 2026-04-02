#!/bin/bash
# cf-tunnel.sh – Cloudflare Quick Tunnel pre wifikeeper (nginx → frontend + API)
# Použitie: bash scripts/cf-tunnel.sh

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; exit 1; }
info() { echo -e "  ${CYAN}→${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║     wifikeeper – Cloudflare Tunnel       ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════╝${NC}"
echo ""

# ── 1. Skontroluj cloudflared ──────────────────────────────────
if ! command -v cloudflared &>/dev/null; then
  warn "cloudflared nie je nainštalovaný, inštalujem..."
  curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb \
    -o /tmp/cloudflared.deb
  sudo dpkg -i /tmp/cloudflared.deb
  rm /tmp/cloudflared.deb
  ok "cloudflared nainštalovaný"
else
  ok "cloudflared nájdený: $(cloudflared --version)"
fi

# ── 2. Skontroluj či nginx beží ────────────────────────────────
if ! curl -sk --max-time 3 https://localhost/ >/dev/null 2>&1; then
  warn "nginx neodpovedá na https://localhost — skontroluj docker-compose"
fi

# ── 3. Spusti tunel ───────────────────────────────────────────
info "Spúšťam Cloudflare Quick Tunnel → https://localhost (nginx)..."
info "Ctrl+C pre zastavenie"
echo ""

exec cloudflared tunnel --url https://localhost --no-tls-verify
