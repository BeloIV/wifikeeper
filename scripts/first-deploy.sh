#!/bin/bash
# =============================================================================
# Prvé produkčné nasadenie wifi-manager
#
# Čo robí:
#   1. Skontroluje prerekvizity (.env, premenné, nástroje)
#   2. Vytvorí/aktualizuje DNS A záznamy v Cloudflare (bez duplikátov)
#   3. Vytvorí certbot/cloudflare.ini
#   4. Vytvorí ./certs/ adresár, DH parametre a CA certifikát
#   5. Získa Let's Encrypt certifikát cez Cloudflare DNS-01
#   6. Skopíruje certy (s -L) do ./certs/ pre FreeRADIUS
#   7. Nastaví symlink deploy hooku pre auto-obnovu
#   8. Spustí docker compose -f docker-compose.prod.yml up -d
#
# Použitie:
#   cd /opt/wifi-manager
#   bash scripts/first-deploy.sh
# =============================================================================

set -euo pipefail
trap 'echo -e "\033[0;31m✗ Skript zlyhal na riadku $LINENO: $BASH_COMMAND\033[0m"' ERR

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CERTS_DIR="$PROJECT_DIR/certs"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.prod.yml"
HOOK_SRC="$SCRIPT_DIR/deploy-cert-hook.sh"
HOOK_DEST="/etc/letsencrypt/renewal-hooks/deploy/wifi-manager-radius.sh"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}!${NC} $*"; }
err()  { echo -e "${RED}✗${NC} $*"; exit 1; }
step() { echo -e "\n${YELLOW}──── $* ────${NC}"; }

# ── 1. Prerekvizity ──────────────────────────────────────────────────────────
step "Kontrola prerekvizít"

cd "$PROJECT_DIR"

[ -f ".env" ] || err ".env neexistuje. Skopíruj .env.example a vyplň hodnoty."

# Načítaj premenné z .env
set -a; source .env; set +a

[ -n "${DOMAIN:-}" ]                  || err "DOMAIN nie je nastavená v .env"
[ -n "${CLOUDFLARE_API_TOKEN:-}" ]    || err "CLOUDFLARE_API_TOKEN nie je nastavený v .env"
[ -n "${ADMIN_EMAIL:-}" ]             || err "ADMIN_EMAIL nie je nastavený v .env"
[ -n "${POSTGRES_PASSWORD:-}" ]       || err "POSTGRES_PASSWORD nie je nastavená v .env"
[ -n "${DJANGO_SECRET_KEY:-}" ]       || err "DJANGO_SECRET_KEY nie je nastavená v .env"
[ -n "${FIELD_ENCRYPTION_KEY:-}" ]    || err "FIELD_ENCRYPTION_KEY nie je nastavená v .env"
[ -n "${LDAP_ADMIN_PASSWORD:-}" ]     || err "LDAP_ADMIN_PASSWORD nie je nastavená v .env"
[ -n "${LDAP_READONLY_PASSWORD:-}" ]  || err "LDAP_READONLY_PASSWORD nie je nastavená v .env"
[ -n "${RADIUS_SECRET:-}" ]           || err "RADIUS_SECRET nie je nastavený v .env"

command -v docker >/dev/null 2>&1     || err "docker nie je nainštalovaný"
command -v openssl >/dev/null 2>&1    || err "openssl nie je nainštalovaný"

ok "Prerekvizity OK (doména: $DOMAIN)"

# Oprav vlastníka data/ adresára ak ho vytvoril Docker ako root
# Pozor: data/postgres musí vlastniť uid 999 (postgres container), nie oratko
if [ -d "$PROJECT_DIR/data" ] && [ "$(stat -c '%U' "$PROJECT_DIR/data")" != "$(id -un)" ]; then
    warn "Opravujem vlastníka data/ adresára (Docker ho vytvoril ako root)..."
    sudo chown "$(id -un):$(id -gn)" "$PROJECT_DIR/data"
    for d in ldap-certs unifi-config; do
        [ -d "$PROJECT_DIR/data/$d" ] && sudo chown -R "$(id -un):$(id -gn)" "$PROJECT_DIR/data/$d"
    done
    ok "Vlastník data/ opravený (postgres a ldap dáta vynechané)"
fi

# ── 2. DNS záznamy v Cloudflare ─────────────────────────────────────────────
step "Kontrola a vytvorenie DNS záznamov (Cloudflare)"

command -v curl >/dev/null 2>&1 || err "curl nie je nainštalovaný"

# Zisti Zone ID pre doménu
CF_ZONE_ID=$(curl -sf "https://api.cloudflare.com/client/v4/zones?name=${DOMAIN}" \
    -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
    -H "Content-Type: application/json" \
    | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

[ -n "$CF_ZONE_ID" ] || err "Nepodarilo sa nájsť Cloudflare zónu pre $DOMAIN. Skontroluj CLOUDFLARE_API_TOKEN."

ok "Cloudflare zone ID: $CF_ZONE_ID"

SERVER_IP="${SERVER_IP:-}"
if [ -z "$SERVER_IP" ]; then
    SERVER_IP=$(curl -sf https://api.ipify.org || curl -sf https://ifconfig.me)
    [ -n "$SERVER_IP" ] || err "Nepodarilo sa zistiť verejnú IP servera. Nastav SERVER_IP v .env"
    ok "Verejná IP servera (auto-detect): $SERVER_IP"
fi

cf_ensure_a_record() {
    local NAME="$1"
    local RESPONSE RECORD_ID CURRENT_IP RESULT

    RESPONSE=$(curl -s "https://api.cloudflare.com/client/v4/zones/${CF_ZONE_ID}/dns_records?name=${NAME}" \
        -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
        -H "Content-Type: application/json") || { warn "curl zlyhal pre $NAME"; return 0; }

    RECORD_ID=$(echo "$RESPONSE" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4 || true)

    if [ -n "$RECORD_ID" ]; then
        local RECORD_TYPE
        RECORD_TYPE=$(echo "$RESPONSE" | grep -o '"type":"[^"]*"' | head -1 | cut -d'"' -f4 || true)
        CURRENT_IP=$(echo "$RESPONSE" | grep -o '"content":"[^"]*"' | head -1 | cut -d'"' -f4 || true)

        if [ "$RECORD_TYPE" = "A" ] && [ "$CURRENT_IP" = "$SERVER_IP" ]; then
            ok "DNS A $NAME → $SERVER_IP (už existuje)"
            return 0
        fi

        # CNAME alebo iná IP – zmaž a vytvor nový A záznam
        if [ "$RECORD_TYPE" != "A" ]; then
            warn "DNS $NAME má $RECORD_TYPE záznam – mažem a nahrádzam A záznamom..."
            curl -s -X DELETE "https://api.cloudflare.com/client/v4/zones/${CF_ZONE_ID}/dns_records/${RECORD_ID}" \
                -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" > /dev/null || true
            RESULT=$(curl -s -X POST "https://api.cloudflare.com/client/v4/zones/${CF_ZONE_ID}/dns_records" \
                -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
                -H "Content-Type: application/json" \
                --data "{\"type\":\"A\",\"name\":\"${NAME}\",\"content\":\"${SERVER_IP}\",\"proxied\":false}") || true
        else
            # A záznam s inou IP – aktualizuj
            RESULT=$(curl -s -X PUT "https://api.cloudflare.com/client/v4/zones/${CF_ZONE_ID}/dns_records/${RECORD_ID}" \
                -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
                -H "Content-Type: application/json" \
                --data "{\"type\":\"A\",\"name\":\"${NAME}\",\"content\":\"${SERVER_IP}\",\"proxied\":false}") || true
        fi

        if echo "$RESULT" | grep -q '"success":true'; then
            ok "DNS A $NAME → $SERVER_IP (nastavený)"
        else
            warn "DNS A $NAME – zlyhalo: $(echo "$RESULT" | grep -o '"message":"[^"]*"' | head -1)"
        fi
    else
        # Vytvor nový záznam
        RESULT=$(curl -s -X POST "https://api.cloudflare.com/client/v4/zones/${CF_ZONE_ID}/dns_records" \
            -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
            -H "Content-Type: application/json" \
            --data "{\"type\":\"A\",\"name\":\"${NAME}\",\"content\":\"${SERVER_IP}\",\"proxied\":false}") || true
        if echo "$RESULT" | grep -q '"success":true'; then
            ok "DNS A $NAME → $SERVER_IP (vytvorený)"
        else
            warn "DNS A $NAME – vytvorenie zlyhalo: $(echo "$RESULT" | grep -o '"message":"[^"]*"' | head -1)"
        fi
    fi
}

cf_ensure_a_record "${DOMAIN}"
cf_ensure_a_record "www.${DOMAIN}"

warn "Čakám 10 sekúnd na propagáciu DNS..."
sleep 10

# ── 3. Cloudflare credentials pre certbot ────────────────────────────────────
step "Príprava Cloudflare credentials"

CF_INI="$PROJECT_DIR/certbot/cloudflare.ini"
mkdir -p "$PROJECT_DIR/certbot"

if [ -f "$CF_INI" ]; then
    ok "certbot/cloudflare.ini už existuje"
else
    cat > "$CF_INI" << EOF
# Cloudflare API token pre DNS-01 challenge
dns_cloudflare_api_token = ${CLOUDFLARE_API_TOKEN}
EOF
    chmod 600 "$CF_INI"
    ok "certbot/cloudflare.ini vytvorený"
fi

# ── 3. Adresár certs/ + DH parametre ────────────────────────────────────────
step "Príprava adresára certs/"

mkdir -p "$CERTS_DIR"

if [ -f "$CERTS_DIR/dh" ]; then
    ok "DH parametre už existujú – preskakujem"
else
    warn "Generujem DH parametre (môže trvať 1-2 min)..."
    openssl dhparam -out "$CERTS_DIR/dh" 2048 2>/dev/null
    ok "DH parametre vygenerované"
fi

# CA certifikát pre FreeRADIUS (ak neexistuje, vytvoríme self-signed CA)
if [ ! -f "$CERTS_DIR/ca.crt" ]; then
    warn "Generujem CA certifikát..."
    openssl genrsa -out "$CERTS_DIR/ca.key" 4096 2>/dev/null
    openssl req -new -x509 -days 1826 -key "$CERTS_DIR/ca.key" \
        -out "$CERTS_DIR/ca.crt" \
        -subj "/C=SK/O=Salezianske oratorium/CN=WiFi-Manager-CA" 2>/dev/null
    ok "CA certifikát vygenerovaný"
fi

# ── 4. Let's Encrypt certifikát ──────────────────────────────────────────────
step "Získanie Let's Encrypt certifikátu (DNS-01 / Cloudflare)"

LE_LIVE="/etc/letsencrypt/live/${DOMAIN}"

if [ -f "${LE_LIVE}/fullchain.pem" ]; then
    ok "Let's Encrypt certifikát pre $DOMAIN už existuje"
else
    warn "Žiadam certifikát pre $DOMAIN a www.$DOMAIN..."
    docker compose -f "$COMPOSE_FILE" run --rm certbot \
        certonly \
        --dns-cloudflare \
        --dns-cloudflare-credentials /opt/cloudflare.ini \
        --dns-cloudflare-propagation-seconds 60 \
        --email "$ADMIN_EMAIL" \
        --agree-tos \
        --no-eff-email \
        --keep-until-expiring \
        -d "$DOMAIN" \
        -d "www.${DOMAIN}"
    ok "Let's Encrypt certifikát získaný"
fi

# ── 5. Skopírovanie certov do ./certs/ ───────────────────────────────────────
step "Kopírovanie certifikátov do ./certs/"

sudo cp -L "${LE_LIVE}/fullchain.pem" "$CERTS_DIR/server.crt"
sudo cp -L "${LE_LIVE}/privkey.pem"   "$CERTS_DIR/server.key"
sudo chown "$(id -un):$(id -gn)" "$CERTS_DIR/server.crt" "$CERTS_DIR/server.key"
chmod 640 "$CERTS_DIR/server.key"

ok "server.crt ← fullchain.pem"
ok "server.key ← privkey.pem"

# Certy pre OpenLDAP (potrebuje konkrétne názvy súborov, bez :ro mountu)
LDAP_CERTS_DIR="$PROJECT_DIR/data/ldap-certs"
sudo mkdir -p "$LDAP_CERTS_DIR"
sudo chown "$(id -un):$(id -gn)" "$LDAP_CERTS_DIR"
sudo cp -L "${LE_LIVE}/fullchain.pem" "$LDAP_CERTS_DIR/ldap.crt"
sudo cp -L "${LE_LIVE}/privkey.pem"   "$LDAP_CERTS_DIR/ldap.key"
sudo cp -L "${LE_LIVE}/chain.pem"     "$LDAP_CERTS_DIR/ca.crt"
sudo chown -R "$(id -un):$(id -gn)" "$LDAP_CERTS_DIR"
chmod 640 "$LDAP_CERTS_DIR/ldap.key"
ok "ldap.crt + ldap.key + ca.crt → data/ldap-certs/"

# ── 6. Deploy hook pre auto-obnovu ──────────────────────────────────────────
step "Nastavenie auto-obnovy (certbot deploy hook)"

HOOK_DIR="/etc/letsencrypt/renewal-hooks/deploy"

if [ -L "$HOOK_DEST" ]; then
    ok "Deploy hook symlink už existuje"
elif [ -f "$HOOK_DEST" ]; then
    warn "Na $HOOK_DEST existuje súbor (nie symlink) – preskakujem"
else
    if [ -d "$HOOK_DIR" ]; then
        chmod +x "$HOOK_SRC"
        sudo ln -s "$HOOK_SRC" "$HOOK_DEST"
        ok "Deploy hook nastavený: $HOOK_DEST → $HOOK_SRC"
    else
        warn "Adresár $HOOK_DIR neexistuje – hook nenainštalovaný (nainštaluj certbot na hostiteľovi)"
    fi
fi

# ── 7. Spustenie stack-u ─────────────────────────────────────────────────────
step "Spúšťam docker compose (prod)"

docker compose -f "$COMPOSE_FILE" up -d --build --scale certbot=0

ok "Stack spustený"

# ── 8. Záverečný výpis ───────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Nasadenie dokončené!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════${NC}"
echo ""
echo "  Web:    https://${DOMAIN}"
echo "  RADIUS: ${DOMAIN}:1812/1813 (UDP)"
echo ""
echo "  Skontroluj logy:"
echo "    docker compose -f docker-compose.prod.yml logs -f backend"
echo "    docker compose -f docker-compose.prod.yml logs -f freeradius"
echo ""
echo "  Auto-obnova certifikátu:"
echo "    certbot renew --dry-run"
echo ""
