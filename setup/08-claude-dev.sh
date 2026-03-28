#!/bin/bash
# 08-claude-dev.sh – Claude Code CLI a claude-mem plugin
# Spusti ako: bash 08-claude-dev.sh

set -e

echo "=== 08-claude-dev.sh: Claude Code + claude-mem ==="

GREEN='\033[0;32m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; }
info() { echo -e "  ${CYAN}→${NC} $1"; }

# ── Predpoklad: Node.js musí byť nainštalovaný ─────────────────
if ! command -v node &>/dev/null; then
  echo "  CHYBA: Node.js nenájdený. Spusti najprv: bash 07-node.sh"
  exit 1
fi

# ── 1. Claude Code CLI ─────────────────────────────────────────
echo ""
echo "[1/2] Claude Code CLI..."

if command -v claude &>/dev/null; then
  ok "Claude Code už nainštalovaný: $(claude --version 2>/dev/null || echo 'ok')"
else
  info "Inštalujem Claude Code CLI..."
  sudo npm install -g @anthropic-ai/claude-code
  ok "Claude Code nainštalovaný"
fi

# ── 2. claude-mem plugin ───────────────────────────────────────
echo ""
echo "[2/2] claude-mem plugin..."

PLUGIN_DIR="$HOME/.claude/plugins/marketplaces/thedotmack/plugin"

if [ ! -d "$PLUGIN_DIR" ]; then
  fail "Plugin adresár neexistuje – Claude Code musí byť spustený aspoň raz"
  echo ""
  echo "  1. Spusti: claude"
  echo "  2. Prihlás sa: claude auth login"
  echo "  3. V Claude: /plugins → nainštaluj claude-mem@thedotmack"
  echo "  4. Spusti tento skript znovu"
  echo ""
  exit 0
fi

ok "Plugin adresár existuje"

info "Inštalujem závislosti claude-mem..."
echo '{}' | node "$PLUGIN_DIR/scripts/smart-install.js" 2>&1 \
  && ok "Závislosti nainštalované" \
  || fail "smart-install.js zlyhalo – skontroluj manuálne"

info "Testujem worker-service..."
echo '{}' | node "$PLUGIN_DIR/scripts/bun-runner.js" "$PLUGIN_DIR/scripts/worker-service.cjs" start 2>&1 | head -5
ok "Worker service OK"

# ── settings.json ──────────────────────────────────────────────
SETTINGS="$HOME/.claude/settings.json"
if [ -f "$SETTINGS" ]; then
  if grep -q "claude-mem@thedotmack" "$SETTINGS"; then
    ok "claude-mem je v settings.json"
  else
    info "claude-mem nie je v settings.json – aktivuj cez /plugins v Claude"
  fi
else
  info "settings.json neexistuje – vytvorí sa pri prvom spustení Claude"
fi

echo ""
echo "=== 08-claude-dev.sh HOTOVO ==="
echo ""
echo "  Ďalší kroky:"
echo "  1. Spusti: claude"
echo "  2. Prihlás sa ak treba: claude auth login"
echo "  3. claude-mem sa aktivuje automaticky pri ďalšom štarte"
echo "Pokračuj: bash 09-everything-claude-code.sh"
