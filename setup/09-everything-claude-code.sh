#!/bin/bash
# 09-everything-claude-code.sh – everything-claude-code plugin pre Claude Code
# Spusti ako: bash 09-everything-claude-code.sh

set -e

echo "=== 09-everything-claude-code.sh: everything-claude-code plugin ==="

# ── Farby ──────────────────────────────────────────────────────
GREEN='\033[0;32m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; }
info() { echo -e "  ${CYAN}→${NC} $1"; }

REPO_URL="https://github.com/affaan-m/everything-claude-code"
TMP_DIR="/tmp/everything-claude-code"
CLAUDE_DIR="$HOME/.claude"

# ── 1. Kontrola Claude Code ────────────────────────────────────
echo ""
echo "[1/4] Kontrolujem Claude Code..."

if ! command -v claude &>/dev/null; then
  fail "Claude Code CLI nenájdený – najprv spusti 07-claude-dev.sh"
  exit 1
fi
ok "Claude Code: $(claude --version 2>/dev/null || echo 'ok')"

# ── 2. Klonovanie repozitára ───────────────────────────────────
echo ""
echo "[2/4] Sťahujem everything-claude-code..."

if [ -d "$TMP_DIR" ]; then
  info "Aktualizujem existujúci klon..."
  git -C "$TMP_DIR" pull --quiet
else
  info "Klónujem $REPO_URL..."
  git clone --quiet "$REPO_URL" "$TMP_DIR"
fi
ok "Repozitár pripravený"

# ── 3. Inštalácia komponentov ──────────────────────────────────
echo ""
echo "[3/4] Inštalujem komponenty..."

mkdir -p "$CLAUDE_DIR/agents" "$CLAUDE_DIR/commands" "$CLAUDE_DIR/skills" "$CLAUDE_DIR/rules"

# Agenty
AGENT_COUNT=$(ls "$TMP_DIR/agents/"*.md 2>/dev/null | wc -l)
cp "$TMP_DIR/agents/"*.md "$CLAUDE_DIR/agents/"
ok "Agenty: $AGENT_COUNT súborov → $CLAUDE_DIR/agents/"

# Príkazy
CMD_COUNT=$(ls "$TMP_DIR/commands/"*.md 2>/dev/null | wc -l)
cp "$TMP_DIR/commands/"*.md "$CLAUDE_DIR/commands/"
ok "Príkazy: $CMD_COUNT súborov → $CLAUDE_DIR/commands/"

# Skills
SKILL_COUNT=$(find "$TMP_DIR/skills/" -mindepth 1 -maxdepth 1 -type d | wc -l)
cp -r "$TMP_DIR/skills/"* "$CLAUDE_DIR/skills/"
ok "Skills: $SKILL_COUNT kategórií → $CLAUDE_DIR/skills/"

# Rules (common + jazykovo-špecifické)
cp -r "$TMP_DIR/rules/common" "$CLAUDE_DIR/rules/"
RULES_EXTRA=$(ls -d "$TMP_DIR/rules/"*/ 2>/dev/null | grep -v common | wc -l)
ok "Rules: common + $RULES_EXTRA jazykových sád → $CLAUDE_DIR/rules/"

# ── 4. Overenie ────────────────────────────────────────────────
echo ""
echo "[4/4] Overenie..."

INST_AGENTS=$(ls "$CLAUDE_DIR/agents/"*.md 2>/dev/null | wc -l)
INST_CMDS=$(ls "$CLAUDE_DIR/commands/"*.md 2>/dev/null | wc -l)
INST_SKILLS=$(find "$CLAUDE_DIR/skills/" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l)

ok "Nainštalované: $INST_AGENTS agentov, $INST_CMDS príkazov, $INST_SKILLS skill kategórií"

echo ""
echo "=== 09-everything-claude-code.sh HOTOVO ==="
echo ""
echo "  Dostupné príkazy v Claude Code:"
echo "    /plan          – plánovanie implementácie"
echo "    /tdd           – test-driven development"
echo "    /code-review   – code review"
echo "    /security-scan – bezpečnostný audit"
echo ""
echo "  Reštartuj Claude Code pre aktiváciu pluginu."
echo ""
