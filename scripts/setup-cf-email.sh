#!/usr/bin/env bash
# setup-cf-email.sh – nastaví Cloudflare Email Routing pre doménu
#
# Čo robí:
#   1. Zapne Email Routing pre zónu (pridá MX záznamy automaticky)
#   2. Zaregistruje cieľovú adresu (Cloudflare pošle verifikačný email!)
#   3. Vytvorí pravidlá preposlania:
#        wifi@    → FORWARD_TO
#        admin@   → FORWARD_TO
#        no-reply@ → drop (nikto nemá odpovedať)
#        catch-all → FORWARD_TO
#
# Požadované premenné v .env:
#   CLOUDFLARE_API_TOKEN  – Zone:Email Routing:Edit permission
#   DOMAIN                – napr. salezianipresov.xyz
#   FORWARD_TO            – kam preposlať (tvoj Gmail/Outlook)
#                           ak nie je nastavený, použije sa ADMIN_EMAIL
#
# Použitie:
#   bash scripts/setup-cf-email.sh

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'
ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }
info() { echo -e "  ${CYAN}→${NC} $1"; }

# ── Načítaj .env ──────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env"
if [[ -f "$ENV_FILE" ]]; then
  set -o allexport; source "$ENV_FILE"; set +o allexport
fi

# ── Kontrola závislostí ────────────────────────────────────────────────────────
for cmd in curl jq; do
  command -v "$cmd" &>/dev/null || { echo "ERROR: '$cmd' nie je nainštalovaný" >&2; exit 1; }
done

# ── Kontrola premenných ────────────────────────────────────────────────────────
[[ -z "${CLOUDFLARE_API_TOKEN:-}" ]] && { echo "ERROR: CLOUDFLARE_API_TOKEN nie je nastavený" >&2; exit 1; }
[[ -z "${DOMAIN:-}" ]]               && { echo "ERROR: DOMAIN nie je nastavený" >&2; exit 1; }

FORWARD_TO="${FORWARD_TO:-${BREVO_SMTP_USER:-${ADMIN_EMAIL:-}}}"
if [[ -z "$FORWARD_TO" ]]; then
  echo "ERROR: Nastav FORWARD_TO, BREVO_SMTP_USER alebo ADMIN_EMAIL v .env" >&2
  exit 1
fi

CF_API="https://api.cloudflare.com/client/v4"
cf()     { curl -sS -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" "$@"; }
cf_get() { cf "$CF_API$1"; }
cf_post(){ cf -H "Content-Type: application/json" -X POST  -d "$2" "$CF_API$1"; }
cf_put() { cf -H "Content-Type: application/json" -X PUT   -d "$2" "$CF_API$1"; }

cf_check_errors() {
  local resp="$1" label="$2"
  local msg
  msg=$(echo "$resp" | jq -r '.errors[0].message // empty' 2>/dev/null)
  if [[ -n "$msg" ]]; then
    warn "$label – $msg"
    if echo "$msg" | grep -qi "403\|permission\|not allowed\|unauthorized"; then
      warn "Token nemá Email Routing oprávnenie!"
      warn "dash.cloudflare.com → API Tokens → Edit → pridaj:"
      warn "  Zone:Email Routing Rules:Edit"
      warn "  Zone:Email Routing Addresses:Edit"
    fi
    return 1
  fi
  return 0
}

echo "========================================"
echo " Cloudflare Email Routing: $DOMAIN"
echo " Preposlať na: $FORWARD_TO"
echo "========================================"
echo ""

# ── 1. Získaj zone ID ─────────────────────────────────────────────────────────
info "Hľadám Cloudflare zónu pre $DOMAIN..."
ZONE_RESP=$(cf_get "/zones?name=$DOMAIN")
ZONE_ID=$(echo "$ZONE_RESP"    | jq -r '.result[0].id // empty')
ACCOUNT_ID=$(echo "$ZONE_RESP" | jq -r '.result[0].account.id // empty')
[[ -z "$ZONE_ID" ]] && { echo "ERROR: Zóna pre $DOMAIN nenájdená v Cloudflare" >&2; exit 1; }
ok "Zóna: $ZONE_ID"
ok "Účet: $ACCOUNT_ID"

# ── 2. Skontroluj a vymaž staré MX záznamy ───────────────────────────────────
echo ""
info "Kontrolujem existujúce MX záznamy..."
OLD_MX=$(cf_get "/zones/$ZONE_ID/dns_records?type=MX")
OLD_MX_IDS=$(echo "$OLD_MX" | jq -r '.result[] | select(.content | test("cloudflare|route1|route2|route3") | not) | .id + " " + .content')

if [[ -n "$OLD_MX_IDS" ]]; then
  echo ""
  warn "Nájdené staré MX záznamy (nie Cloudflare Email Routing):"
  echo "$OLD_MX" | jq -r '.result[] | select(.content | test("cloudflare|route1|route2|route3") | not) | "    " + .content'
  echo ""
  read -rp "  Zmazať ich? (potrebné pre Email Routing) [y/N]: " CONFIRM
  if [[ "${CONFIRM,,}" == "y" ]]; then
    while IFS= read -r line; do
      rec_id=$(echo "$line" | cut -d' ' -f1)
      rec_val=$(echo "$line" | cut -d' ' -f2-)
      cf -X DELETE "$CF_API/zones/$ZONE_ID/dns_records/$rec_id" | jq -r 'if .success then "    Zmazaný: '"$rec_val"'" else "    WARN: \(.errors[0].message)" end'
    done <<< "$OLD_MX_IDS"
  else
    warn "MX záznamy ponechané – Email Routing nemusí fungovať."
  fi
else
  ok "Žiadne staré MX záznamy"
fi

# ── 3. Zapni Email Routing ────────────────────────────────────────────────────
echo ""
info "Zapínam Email Routing..."
ENABLE_RESP=$(cf_post "/zones/$ZONE_ID/email/routing/enable" '{}' || true)
if ! echo "$ENABLE_RESP" | jq -e '.result' &>/dev/null 2>&1; then
  warn "Neočakávaná odpoveď (možno 403 – skontroluj token oprávnenia):"
  echo "    $ENABLE_RESP" | head -3
  warn "Token musí mať: Zone:Email Routing Rules:Edit + Zone:Email Routing Addresses:Edit"
  exit 1
fi
if echo "$ENABLE_RESP" | jq -e '.result.enabled == true' &>/dev/null; then
  ok "Email Routing zapnutý (MX záznamy pridané automaticky)"
else
  ERR=$(echo "$ENABLE_RESP" | jq -r '.errors[0].message // ""')
  if echo "$ERR" | grep -qi "already\|enabled"; then
    ok "Email Routing už bol zapnutý"
  else
    STATUS=$(cf_get "/zones/$ZONE_ID/email/routing" | jq -r '.result.enabled // false' 2>/dev/null)
    [[ "$STATUS" == "true" ]] && ok "Email Routing je aktívny" || warn "Nepodarilo sa zapnúť: $ERR"
  fi
fi

# ── 3. Registruj cieľovú adresu ───────────────────────────────────────────────
echo ""
info "Registrujem cieľovú adresu $FORWARD_TO..."
ADDR_RESP=$(cf_post "/accounts/$ACCOUNT_ID/email/routing/addresses" \
  "{\"email\": \"$FORWARD_TO\"}" 2>&1 || true)

if echo "$ADDR_RESP" | jq -e '.result.email' &>/dev/null; then
  VERIFIED=$(echo "$ADDR_RESP" | jq -r '.result.verified // "nie"')
  if [[ "$VERIFIED" == "null" || "$VERIFIED" == "nie" ]]; then
    warn "Adresa zaregistrovaná – Cloudflare poslal verifikačný email na $FORWARD_TO"
    warn "KLIKNI NA ODKAZ V EMAILI pred pokračovaním!"
  else
    ok "Adresa $FORWARD_TO overená"
  fi
elif echo "$ADDR_RESP" | jq -r '.errors[0].message // ""' | grep -qi "already\|exist"; then
  ok "Adresa $FORWARD_TO už existuje"
else
  warn "$(echo "$ADDR_RESP" | jq -r '.errors[0].message // .')"
fi

# ── 4. Vytvor pravidlá ────────────────────────────────────────────────────────
echo ""
info "Vytváram pravidlá preposlania..."

create_rule() {
  local name="$1" to_addr="$2" match_type="$3" match_val="${4:-}"

  if [[ "$match_type" == "literal" ]]; then
    local matchers="[{\"type\":\"literal\",\"field\":\"to\",\"value\":\"$match_val\"}]"
  else
    local matchers="[{\"type\":\"all\"}]"
  fi

  local actions
  if [[ "$to_addr" == "drop" ]]; then
    actions='[{"type":"drop"}]'
  else
    actions="[{\"type\":\"forward\",\"value\":[\"$to_addr\"]}]"
  fi

  local payload
  payload=$(jq -nc --arg n "$name" \
    --argjson m "$matchers" \
    --argjson a "$actions" \
    '{"name":$n,"matchers":$m,"actions":$a,"enabled":true}')

  local resp
  resp=$(cf_post "/zones/$ZONE_ID/email/routing/rules" "$payload" 2>&1 || true)

  if echo "$resp" | jq -e '.result.name' &>/dev/null; then
    ok "$name"
  elif echo "$resp" | jq -r '.errors[0].message // ""' | grep -qi "already\|exist"; then
    ok "$name (už existuje)"
  else
    warn "$name – $(echo "$resp" | jq -r '.errors[0].message // .')"
  fi
}

create_rule "wifi@ → forward"     "$FORWARD_TO" "literal" "wifi@$DOMAIN"
create_rule "admin@ → forward"    "$FORWARD_TO" "literal" "admin@$DOMAIN"
create_rule "support@ → forward"  "$FORWARD_TO" "literal" "support@$DOMAIN"
create_rule "no-reply@ → drop"    "drop"        "literal" "no-reply@$DOMAIN"

# Catch-all má špeciálny endpoint
echo ""
info "Nastavujem catch-all pravidlo..."
CATCHALL=$(cf_put "/zones/$ZONE_ID/email/routing/rules/catch_all" \
  "{\"name\":\"Catch-all\",\"matchers\":[{\"type\":\"all\"}],\"actions\":[{\"type\":\"forward\",\"value\":[\"$FORWARD_TO\"]}],\"enabled\":true}" \
  2>&1 || true)
if echo "$CATCHALL" | jq -e '.result.enabled == true' &>/dev/null; then
  ok "Catch-all → $FORWARD_TO"
else
  warn "Catch-all – $(echo "$CATCHALL" | jq -r '.errors[0].message // .')"
fi

# ── Záver ─────────────────────────────────────────────────────────────────────
echo ""
echo "========================================"
ok "Hotovo!"
echo ""
echo "  Pravidlá:"
echo "    wifi@$DOMAIN      → $FORWARD_TO"
echo "    admin@$DOMAIN     → $FORWARD_TO"
echo "    support@$DOMAIN   → $FORWARD_TO"
echo "    no-reply@$DOMAIN  → zahodené (drop)"
echo "    *@$DOMAIN         → $FORWARD_TO"
echo ""
warn "Ak si nedostal verifikačný email od Cloudflare,"
warn "skontroluj spam alebo spusti skript znova."
echo "========================================"
