#!/usr/bin/env bash
# setup-brevo.sh – nastaví Brevo sender, doménu a zobrazí DNS záznamy (SPF/DKIM)
#
# Požadované env premenné:
#   BREVO_API_KEY  – REST API kľúč v3 (app.brevo.com → API Keys, NIE SMTP kľúč)
#   MAIL_FROM      – odosielacia adresa, napr. wifi@salezianipresov.xyz
#
# Použitie:
#   export BREVO_API_KEY=xkeysib-...
#   export MAIL_FROM=wifi@salezianipresov.xyz
#   bash scripts/setup-brevo.sh
#
# Alebo načíta z .env ak existuje:
#   bash scripts/setup-brevo.sh

set -euo pipefail

# ── Načítaj .env ak nie sú premenné nastavené ─────────────────────────────────
if [[ -z "${BREVO_API_KEY:-}" || -z "${MAIL_FROM:-}" ]]; then
  ENV_FILE="$(dirname "$0")/../.env"
  if [[ -f "$ENV_FILE" ]]; then
    # shellcheck disable=SC1090
    set -o allexport
    source "$ENV_FILE"
    set +o allexport
  fi
fi

# ── Kontrola závislostí ────────────────────────────────────────────────────────
for cmd in curl jq; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "ERROR: '$cmd' nie je nainštalovaný" >&2
    exit 1
  fi
done

# ── Kontrola požadovaných premenných ──────────────────────────────────────────
[[ -z "${BREVO_API_KEY:-}" ]] && echo "ERROR: BREVO_API_KEY nie je nastavený" >&2 && exit 1
[[ -z "${MAIL_FROM:-}" ]]     && echo "ERROR: MAIL_FROM nie je nastavený" >&2     && exit 1

DOMAIN="${MAIL_FROM##*@}"

API="https://api.brevo.com/v3"
HDR_KEY="api-key: $BREVO_API_KEY"
HDR_JSON="Content-Type: application/json"

brevo_get()  { curl -fsSL -H "$HDR_KEY" "$API$1"; }
brevo_post() { curl -fsSL -H "$HDR_KEY" -H "$HDR_JSON" -X POST -d "$2" "$API$1"; }

# Senders: email → meno
declare -A SENDERS_MAP=(
  ["$MAIL_FROM"]="WiFi Oratko"
  ["admin@$DOMAIN"]="Admin Oratko"
  ["no-reply@$DOMAIN"]="Oratko (no-reply)"
  ["support@$DOMAIN"]="Oratko Support"
)

echo "========================================"
echo " Brevo setup: $DOMAIN"
echo "========================================"

# ── 1. Overenie API kľúča ─────────────────────────────────────────────────────
echo ""
echo "▶  1/4  Overujem API kľúč..."
ACCOUNT=$(brevo_get /account)
COMPANY=$(echo "$ACCOUNT" | jq -r '.companyName // .email // "neznámy"')
PLAN=$(echo "$ACCOUNT"    | jq -r '.plan[0].type // "neznámy"')
echo "    Účet : $COMPANY"
echo "    Plán : $PLAN"

# ── 2. Vytvorenie senderov ─────────────────────────────────────────────────────
echo ""
echo "▶  2/4  Vytváram senderov..."

EXISTING_SENDERS=$(brevo_get /senders)

create_sender() {
  local email="$1" name="$2"
  local exists
  exists=$(echo "$EXISTING_SENDERS" | jq -r --arg e "$email" '.senders[]? | select(.email == $e) | .id')
  if [[ -n "$exists" ]]; then
    echo "    $email – už existuje (id=$exists), preskakujem."
  else
    local resp
    resp=$(brevo_post /senders "{\"name\": \"$name\", \"email\": \"$email\"}" 2>&1 || true)
    if echo "$resp" | jq -e '.id' &>/dev/null; then
      echo "    $email – vytvorený (id=$(echo "$resp" | jq '.id'))."
    else
      echo "    $email – WARN: $(echo "$resp" | jq -r '.message // .' 2>/dev/null)"
    fi
  fi
}

for email in "${!SENDERS_MAP[@]}"; do
  create_sender "$email" "${SENDERS_MAP[$email]}"
done

# ── 3. Registrácia domény v Brevo ─────────────────────────────────────────────
echo ""
echo "▶  3/5  Registrujem doménu $DOMAIN v Brevo..."

DOMAINS=$(brevo_get /senders/domains)
DOM_EXISTS=$(echo "$DOMAINS" | jq -r --arg d "$DOMAIN" '.domains[]? | select(.domain_name == $d) | .domain_name')

if [[ -n "$DOM_EXISTS" ]]; then
  echo "    Doména už existuje, preskakujem."
else
  DRESP=$(brevo_post /senders/domains "{\"name\": \"$DOMAIN\"}" 2>&1 || true)
  if echo "$DRESP" | jq -r '.message // ""' 2>/dev/null | grep -qi "already"; then
    echo "    Doména už existuje."
  elif echo "$DRESP" | jq -e '.domain_name // .name' &>/dev/null 2>&1; then
    echo "    Doména zaregistrovaná."
  else
    echo "    WARN: $(echo "$DRESP" | jq -r '.message // .' 2>/dev/null || echo "$DRESP")"
  fi
fi

# ── 4. DNS záznamy z Brevo ────────────────────────────────────────────────────
echo ""
echo "▶  4/5  Získavam DNS záznamy pre $DOMAIN..."

AUTH=$(brevo_get "/senders/domains/$DOMAIN/authenticate" 2>&1 || true)
RECORDS_KEY=$(echo "$AUTH" | jq -r 'if .dnsRecords then "dnsRecords" else "records" end' 2>/dev/null || true)

if [[ -z "$RECORDS_KEY" ]] || ! echo "$AUTH" | jq -e ".$RECORDS_KEY" &>/dev/null 2>&1; then
  echo "    WARN: Nepodarilo sa získať DNS záznamy."
  echo "$AUTH" | jq . 2>/dev/null || echo "$AUTH"
else
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo " DNS záznamy z Brevo:"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "$AUTH" | jq -r ".$RECORDS_KEY[] | \
    \"Typ    : \" + (.type // \"TXT\"),\
    \"Meno   : \" + (.hostName // .host // .name // \"@\"),\
    \"Hodnota: \" + (.value // .data),\
    \"─────────────────────────────────────────────────\""
fi

# ── 5. Cloudflare DNS upsert + DMARC fix ──────────────────────────────────────
echo ""
if [[ -z "${CLOUDFLARE_API_TOKEN:-}" ]]; then
  echo "▶  5/5  CLOUDFLARE_API_TOKEN nie je nastavený – nastav DNS záznamy ručne."
else
  echo "▶  5/5  Nastavujem DNS záznamy cez Cloudflare API..."

  CF_API="https://api.cloudflare.com/client/v4"
  cf_get()    { curl -fsSL -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" "$CF_API$1"; }
  cf_post()   { curl -fsSL -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
                             -H "Content-Type: application/json" -X POST  -d "$2" "$CF_API$1"; }
  cf_put()    { curl -fsSL -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
                             -H "Content-Type: application/json" -X PUT   -d "$2" "$CF_API$1"; }
  cf_delete() { curl -fsSL -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" -X DELETE "$CF_API$1"; }

  # Získaj zone ID
  ZONE_ID=$(cf_get "/zones?name=$DOMAIN" | jq -r '.result[0].id // empty')
  if [[ -z "$ZONE_ID" ]]; then
    echo "    WARN: Cloudflare zóna pre $DOMAIN nenájdená – nastav DNS ručne."
  else
    echo "    Cloudflare zóna: $ZONE_ID"

    # Upsert funkcia
    upsert_record() {
      local type="$1" host="$2" content="$3"
      local name
      [[ "$host" == "@" ]] && name="$DOMAIN" || name="$host.$DOMAIN"

      local existing record_id
      existing=$(cf_get "/zones/$ZONE_ID/dns_records?type=$type&name=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$name'))")")
      record_id=$(echo "$existing" | jq -r '.result[0].id // empty')

      local payload
      payload=$(jq -nc --arg t "$type" --arg n "$name" --arg c "$content" \
        '{"type":$t,"name":$n,"content":$c,"ttl":1}')

      if [[ -n "$record_id" ]]; then
        cf_put "/zones/$ZONE_ID/dns_records/$record_id" "$payload" | jq -r '"    \(.errors // [] | if length>0 then "WARN: \(.[0].message)" else "aktualizovaný"  end)"' \
          | sed "s/^/    $type $host – /" 2>/dev/null || echo "    $type $host – aktualizovaný"
      else
        cf_post "/zones/$ZONE_ID/dns_records" "$payload" | jq -r '"    \(.errors // [] | if length>0 then "WARN: \(.[0].message)" else "vytvorený" end)"' \
          | sed "s/^/    $type $host – /" 2>/dev/null || echo "    $type $host – vytvorený"
      fi
    }

    # Pushni záznamy z Brevo
    if [[ -n "$RECORDS_KEY" ]]; then
      while IFS= read -r record; do
        rtype=$(echo "$record" | jq -r '.type // "TXT"')
        rhost=$(echo "$record" | jq -r '.hostName // .host // .name // "@"')
        rval=$(echo  "$record" | jq -r '.value // .data')
        upsert_record "$rtype" "$rhost" "$rval"
      done < <(echo "$AUTH" | jq -c ".$RECORDS_KEY[]")
    fi

    # Oprav DMARC duplikáty
    echo ""
    echo "    Kontrolujem DMARC duplikáty..."
    DMARC_NAME="_dmarc.$DOMAIN"
    DMARC_RECORDS=$(cf_get "/zones/$ZONE_ID/dns_records?type=TXT&name=$DMARC_NAME")
    DMARC_COUNT=$(echo "$DMARC_RECORDS" | jq '.result | length')

    if [[ "$DMARC_COUNT" -eq 0 ]]; then
      # Vytvor základný DMARC ak neexistuje
      DMARC_VAL="v=DMARC1; p=none; rua=mailto:${ADMIN_EMAIL:-admin@$DOMAIN}"
      upsert_record "TXT" "_dmarc" "$DMARC_VAL"
      echo "    DMARC vytvorený: $DMARC_VAL"
    elif [[ "$DMARC_COUNT" -gt 1 ]]; then
      echo "    Nájdených $DMARC_COUNT DMARC záznamov – mažem duplikáty (ponechám posledný)..."
      while IFS= read -r dup_id; do
        cf_delete "/zones/$ZONE_ID/dns_records/$dup_id" | jq -r 'if .success then "    Zmazaný DMARC (id='"$dup_id"')" else "    WARN: \(.errors[0].message)" end'
      done < <(echo "$DMARC_RECORDS" | jq -r '.result[0:-1][].id')
    else
      echo "    DMARC – 1 záznam, OK."
    fi
  fi
fi

echo ""
echo "========================================"
echo " Hotovo!"
echo " DNS propagácia môže trvať 24-48h."
echo " Potom over doménu na:"
echo "   app.brevo.com → SMTP & API → Sender domains"
echo "========================================"
