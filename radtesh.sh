#!/bin/bash
# WiFi RADIUS test skript
# Uprav zoznamy nižšie, potom spusti: ./radtesh.sh

RADIUS_HOST="192.168.1.222"
SECRET="6a8284911046cf0c191f0532425e28e30f501e966be7fd6f"

# ── Zoznam bežných používateľov (testuje sa 1× Accept) ───────────────────────
# Formát: "username:heslo"
USERS=(
    "beluskostefan@gmail.com:E8z5IMHD"
    # "dalsi@email.sk:heslo"
)

# ── Zoznam N-násobných kľúčov (N× Accept, N+1× Reject) ──────────────────────
# Formát: "username:heslo:N"
MULTI_KEYS=(
    # "guest_abc123:HesloKluca:3"
    "beluskostefan@gmail.com:6HuAZuhw:4"

    

)

# ─────────────────────────────────────────────────────────────────────────────

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0

_pass() { echo -e "${GREEN}✓${NC} $1"; PASS=$((PASS+1)); }
_fail() { echo -e "${RED}✗${NC} $1"; FAIL=$((FAIL+1)); }
_info() { echo -e "${YELLOW}→${NC} $1"; }

_expect_accept() {
    local user="$1" pass="$2" label="$3"
    local out
    out=$(radtest "$user" "$pass" "$RADIUS_HOST" 0 "$SECRET" 2>/dev/null)
    if echo "$out" | grep -q "Access-Accept"; then
        local vlan
        vlan=$(echo "$out" | grep "Tunnel-Private-Group-Id" | grep -o '[0-9]*$')
        _pass "$label${vlan:+ (VLAN $vlan)}"
    else
        local msg
        msg=$(echo "$out" | grep "Reply-Message" | sed 's/.*Reply-Message = //')
        _fail "$label → Reject${msg:+ — $msg}"
    fi
}

_expect_reject() {
    local user="$1" pass="$2" label="$3"
    local out
    out=$(radtest "$user" "$pass" "$RADIUS_HOST" 0 "$SECRET" 2>/dev/null)
    if echo "$out" | grep -q "Access-Reject"; then
        _pass "$label"
    else
        _fail "$label → dostal Accept (mal byť Reject!)"
    fi
}

_cleanup() {
    _info "Spúšťam cleanup LDAP účtov..."
    docker compose exec -T backend python manage.py shell -c "
from apps.keys.tasks import cleanup_expired_keys_safe
cleanup_expired_keys_safe()
" 2>/dev/null
}

# ── Bežní používatelia ────────────────────────────────────────────────────────

if [ ${#USERS[@]} -gt 0 ]; then
    echo ""
    echo "═══ Bežní používatelia ════════════════════════════════"
    for entry in "${USERS[@]}"; do
        user="${entry%%:*}"
        pass="${entry#*:}"
        _expect_accept "$user" "$pass" "$user"
    done
fi

# ── N-násobné kľúče ───────────────────────────────────────────────────────────

if [ ${#MULTI_KEYS[@]} -gt 0 ]; then
    echo ""
    echo "═══ N-násobné kľúče ═══════════════════════════════════"
    for entry in "${MULTI_KEYS[@]}"; do
        user=$(echo "$entry" | cut -d: -f1)
        pass=$(echo "$entry" | cut -d: -f2)
        n=$(echo "$entry" | cut -d: -f3)

        echo ""
        _info "$user  (max=$n použití)"
        for i in $(seq 1 "$n"); do
            _expect_accept "$user" "$pass" "  pokus $i/$n"
        done
        # Trigger na radius_postauth automaticky zmaže radreply — nie je treba čakať
        _expect_reject "$user" "$pass" "  pokus $((n+1))/$n — po vyčerpaní"
        _cleanup
    done
fi

# ── Súhrn ─────────────────────────────────────────────────────────────────────

echo ""
echo "═══════════════════════════════════════════════════════"
echo -e "  ${GREEN}✓ $PASS OK${NC}   ${RED}✗ $FAIL FAIL${NC}"
[ "$FAIL" -gt 0 ] && exit 1 || exit 0