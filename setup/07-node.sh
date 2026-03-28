#!/bin/bash
# 07-node.sh – Node.js LTS + Bun
# Spusti ako: bash 07-node.sh

set -e

echo "=== 07-node.sh: Node.js ==="

GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
info() { echo -e "  ${CYAN}→${NC} $1"; }

echo ""

if command -v node &>/dev/null; then
  ok "Node.js už nainštalovaný: $(node --version), npm $(npm --version)"
else
  info "Inštalujem Node.js LTS cez NodeSource..."
  curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
  sudo apt install -y nodejs
  ok "Node.js $(node --version) nainštalovaný"
fi

# ── Bun ───────────────────────────────────────────────────────
echo ""

if command -v bun &>/dev/null; then
  ok "Bun už nainštalovaný: $(bun --version)"
else
  info "Inštalujem závislosti pre Bun..."
  sudo apt install -y unzip
  info "Inštalujem Bun..."
  curl -fsSL https://bun.sh/install | bash
  # Pridaj do PATH pre aktuálnu session
  export BUN_INSTALL="$HOME/.bun"
  export PATH="$BUN_INSTALL/bin:$PATH"
  ok "Bun $(bun --version) nainštalovaný"
  echo ""
  echo "  POZOR: Bun je v ~/.bun/bin – reštartuj terminál alebo spusti:"
  echo "    source ~/.bashrc"
fi

echo ""
echo "=== 07-node.sh HOTOVO ==="
echo "Pokračuj: bash 08-claude-dev.sh"
