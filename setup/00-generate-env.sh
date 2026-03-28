#!/bin/bash
# 00-generate-env.sh – Vygeneruje .env so silnými heslami
# Spusti ako: bash setup/00-generate-env.sh
# Spúšťa sa PRED ostatnými skriptmi

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_DIR/.env"

# ── Farby ──────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
info() { echo -e "  ${CYAN}→${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }

# ── Generátory ────────────────────────────────────────────────
gen_pass()   { openssl rand -base64 32 | tr -d '=+/' | cut -c1-32; }
gen_secret() { openssl rand -base64 64 | tr -d '=+/\n' | cut -c1-64; }
gen_hex()    { openssl rand -hex 24; }

echo ""
echo -e "${BOLD}=== 00-generate-env.sh: Generovanie .env ===${NC}"
echo ""

# ── Kontrola ak .env existuje ─────────────────────────────────
if [ -f "$ENV_FILE" ]; then
  warn ".env už existuje: $ENV_FILE"
  read -p "  Prepísať? [y/N]: " OVERWRITE
  if [[ "${OVERWRITE,,}" != "y" ]]; then
    echo "  Zrušené – .env zostáva nezmenený."
    exit 0
  fi
  cp "$ENV_FILE" "${ENV_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
  ok "Záloha uložená: ${ENV_FILE}.backup.*"
fi

# ── Interaktívna konfigurácia ──────────────────────────────────
echo -e "${BOLD}── Konfigurácia (Enter = default) ────────────────────────${NC}"
echo ""

ask() {
  local prompt="$1" default="$2" var="$3"
  read -p "  $prompt${default:+ [$default]}: " input
  eval "$var='${input:-$default}'"
}

ask "IP servera"                ""                           CFG_SERVER_IP
ask "Doména"                    "salezianipresov.xyz"        CFG_DOMAIN
ask "Email admina"              "admin@salezianipresov.xyz"  CFG_ADMIN_EMAIL
ask "LDAP doména"               "oratko.local"               CFG_LDAP_DOMAIN
ask "Odosielacia adresa"        "wifi@salezianipresov.xyz"   CFG_MAIL_FROM
ask "Brevo SMTP user (email)"   ""                  CFG_BREVO_USER
ask "Brevo SMTP API key"        ""                  CFG_BREVO_KEY
ask "Brevo REST API kľúč (v3)"  ""                  CFG_BREVO_API_KEY
ask "Cloudflare API token"      ""                  CFG_CF_TOKEN
ask "UniFi Mongo user"          "unifi"             CFG_UNIFI_MONGO_USER

echo ""
info "Generujem heslá..."
echo ""

# ── Generuj heslá ─────────────────────────────────────────────
POSTGRES_PASSWORD=$(gen_pass)
REDIS_PASSWORD=$(gen_pass)
LDAP_ADMIN_PASSWORD=$(gen_pass)
LDAP_CONFIG_PASSWORD=$(gen_pass)
LDAP_READONLY_PASSWORD=$(gen_pass)
RADIUS_SECRET=$(gen_hex)
DJANGO_SECRET_KEY=$(gen_secret)
UNIFI_MONGO_PASS=$(gen_pass)
DJANGO_SUPERUSER_PASSWORD=$(gen_pass)

# LDAP base DN z domény (oratko.local → dc=oratko,dc=local)
LDAP_BASE_DN=$(echo "$CFG_LDAP_DOMAIN" | awk -F. '{for(i=1;i<=NF;i++){printf "dc=" $i; if(i<NF) printf ","}; print ""}')

# ── Zapis .env ────────────────────────────────────────────────
cat > "$ENV_FILE" <<EOF
# =============================================================================
# wifi-manager – environment premenné
# Vygenerované: $(date '+%Y-%m-%d %H:%M:%S')
# NIKDY nekomiťuj tento súbor do gitu!
# =============================================================================

# ── PostgreSQL ────────────────────────────────────────────────────────────────
POSTGRES_DB=wifimanager
POSTGRES_USER=wifimanager
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}

# ── Redis ─────────────────────────────────────────────────────────────────────
REDIS_PASSWORD=${REDIS_PASSWORD}

# ── OpenLDAP ──────────────────────────────────────────────────────────────────
LDAP_DOMAIN=${CFG_LDAP_DOMAIN}
LDAP_BASE_DN=${LDAP_BASE_DN}
LDAP_ADMIN_PASSWORD=${LDAP_ADMIN_PASSWORD}
LDAP_CONFIG_PASSWORD=${LDAP_CONFIG_PASSWORD}
LDAP_READONLY_PASSWORD=${LDAP_READONLY_PASSWORD}

# ── FreeRADIUS ────────────────────────────────────────────────────────────────
RADIUS_SECRET=${RADIUS_SECRET}

# ── Django ────────────────────────────────────────────────────────────────────
DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_PASSWORD=${DJANGO_SUPERUSER_PASSWORD}

# ── Brevo email ───────────────────────────────────────────────────────────────
MAIL_FROM=${CFG_MAIL_FROM}
BREVO_SMTP_USER=${CFG_BREVO_USER}
BREVO_SMTP_KEY=${CFG_BREVO_KEY}
BREVO_API_KEY=${CFG_BREVO_API_KEY}
ADMIN_EMAIL=${CFG_ADMIN_EMAIL}

# ── Server ────────────────────────────────────────────────────────────────────
SERVER_IP=${CFG_SERVER_IP}

# ── Doména ────────────────────────────────────────────────────────────────────
DOMAIN=${CFG_DOMAIN}

# ── Cloudflare DNS-01 (Let's Encrypt) ─────────────────────────────────────────
CLOUDFLARE_API_TOKEN=${CFG_CF_TOKEN}

# ── UniFi Network Application ─────────────────────────────────────────────────
UNIFI_MONGO_USER=${CFG_UNIFI_MONGO_USER}
UNIFI_MONGO_PASS=${UNIFI_MONGO_PASS}
EOF

chmod 600 "$ENV_FILE"

# ── Výpis ─────────────────────────────────────────────────────
ok "Súbor vytvorený: $ENV_FILE"
ok "Oprávnenia: 600 (čita iba vlastník)"
echo ""
echo -e "${BOLD}── Vygenerované heslá ────────────────────────────────────${NC}"
echo ""
echo "  POSTGRES_PASSWORD     = ${POSTGRES_PASSWORD}"
echo "  REDIS_PASSWORD        = ${REDIS_PASSWORD}"
echo "  LDAP_ADMIN_PASSWORD   = ${LDAP_ADMIN_PASSWORD}"
echo "  LDAP_CONFIG_PASSWORD  = ${LDAP_CONFIG_PASSWORD}"
echo "  LDAP_READONLY_PASSWORD= ${LDAP_READONLY_PASSWORD}"
echo "  RADIUS_SECRET         = ${RADIUS_SECRET}"
echo "  DJANGO_SECRET_KEY     = ${DJANGO_SECRET_KEY:0:20}..."
echo "  UNIFI_MONGO_PASS           = ${UNIFI_MONGO_PASS}"
echo "  DJANGO_SUPERUSER_PASSWORD  = ${DJANGO_SUPERUSER_PASSWORD}"
echo ""
warn "Toto je jediný výpis hesiel – ulož ich na bezpečné miesto!"
echo ""
echo -e "${BOLD}── Brevo – čo kde nájdeš ─────────────────────────────────${NC}"
echo ""
echo -e "  ${CYAN}BREVO_SMTP_USER${NC}  = tvoj prihlasovací email na Brevo (napr. jan@gmail.com)"
echo -e "  ${CYAN}BREVO_SMTP_KEY${NC}   = SMTP heslo  →  app.brevo.com → SMTP & API → SMTP → Generate key"
echo -e "                   (začína na xsmtpsib-...)"
echo ""
echo -e "  ${CYAN}BREVO_API_KEY${NC}    = REST API kľúč  →  app.brevo.com → SMTP & API → API Keys → Generate"
echo -e "                   (začína na xkeysib-...)"
echo -e "  ${YELLOW}⚠${NC}  Toto sú DVA RÔZNE kľúče! SMTP kľúč ≠ API kľúč."

# Ak BREVO_API_KEY nebol zadaný, upozorni
if [[ -z "${CFG_BREVO_API_KEY:-}" ]]; then
  echo ""
  warn "BREVO_API_KEY nebol zadaný – doplň ho ručne do .env:"
  echo "     BREVO_API_KEY=xkeysib-..."
fi

echo ""
echo -e "${BOLD}── Ďalší postup ──────────────────────────────────────────${NC}"
echo ""
echo "  1. bash setup/setup.sh          – spustí infraštruktúru"
echo "  2. bash scripts/setup-brevo.sh  – overí Brevo, vytvorí sendera,"
echo "                                    zaregistruje doménu a vypíše"
echo "                                    SPF/DKIM/DMARC záznamy pre DNS"
echo ""
echo "=== 00-generate-env.sh HOTOVO ==="
echo ""
