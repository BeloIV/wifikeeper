#!/bin/bash
# cf-tunnel-setup.sh – Permanentný Cloudflare Named Tunnel pre wifikeeper
# Vytvorí tunel cez Cloudflare API, nastaví DNS a nainštaluje systemd service
#
# Použitie: bash scripts/cf-tunnel-setup.sh
# Vyžaduje: CLOUDFLARE_API_TOKEN a DOMAIN v .env (alebo ako env premenné)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_DIR/.env"

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
echo -e "${BOLD}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║   wifikeeper – Cloudflare Tunnel Setup       ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════╝${NC}"
echo ""

# ── Načítaj .env ───────────────────────────────────────────────
if [ -f "$ENV_FILE" ]; then
  set -a
  source <(grep -E '^[A-Z_]+=.' "$ENV_FILE" | sed 's/[[:space:]]*#.*//')
  set +a
  ok "Načítaný .env"
fi

CF_TOKEN="${CLOUDFLARE_API_TOKEN:-}"
DOMAIN="${DOMAIN:-}"
TUNNEL_NAME="${CF_TUNNEL_NAME:-wifimanager}"
SUBDOMAIN="${CF_TUNNEL_SUBDOMAIN:-wifimanager}"
CF_DIR="${HOME}/.cloudflared"

# ── Validácia ─────────────────────────────────────────────────
[ -z "$CF_TOKEN" ] && fail "CLOUDFLARE_API_TOKEN nie je nastavený v .env"
[ -z "$DOMAIN"   ] && fail "DOMAIN nie je nastavený v .env"

HOSTNAME="${SUBDOMAIN}.${DOMAIN}"
info "Doména tunela: ${BOLD}${HOSTNAME}${NC}"
info "Názov tunela:  ${BOLD}${TUNNEL_NAME}${NC}"
echo ""

# ── 1. Inštalácia cloudflared ──────────────────────────────────
if ! command -v cloudflared &>/dev/null; then
  info "Inštalujem cloudflared..."
  curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb \
    -o /tmp/cloudflared.deb
  sudo dpkg -i /tmp/cloudflared.deb
  rm /tmp/cloudflared.deb
  ok "cloudflared nainštalovaný"
else
  ok "cloudflared: $(cloudflared --version)"
fi

# ── 2. CF API helper ───────────────────────────────────────────
cf_api() {
  local method="$1"
  local path="$2"
  local data="${3:-}"
  if [ -n "$data" ]; then
    curl -sf -X "$method" "https://api.cloudflare.com/client/v4${path}" \
      -H "Authorization: Bearer ${CF_TOKEN}" \
      -H "Content-Type: application/json" \
      --data "$data"
  else
    curl -sf -X "$method" "https://api.cloudflare.com/client/v4${path}" \
      -H "Authorization: Bearer ${CF_TOKEN}" \
      -H "Content-Type: application/json"
  fi
}

# ── 3. Account ID ──────────────────────────────────────────────
info "Zisťujem Account ID..."
ACCOUNT_ID=$(cf_api GET "/accounts?per_page=1" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print(d['result'][0]['id'])")
[ -z "$ACCOUNT_ID" ] && fail "Nepodarilo sa získať Account ID — skontroluj CF_TOKEN"
ok "Account ID: ${ACCOUNT_ID}"

# ── 4. Zone ID ─────────────────────────────────────────────────
info "Zisťujem Zone ID pre ${DOMAIN}..."
ZONE_ID=$(cf_api GET "/zones?name=${DOMAIN}&per_page=1" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print(d['result'][0]['id'])")
[ -z "$ZONE_ID" ] && fail "Doména ${DOMAIN} nenájdená v Cloudflare — skontroluj token oprávnenia"
ok "Zone ID: ${ZONE_ID}"

# ── 5. Vytvor alebo získaj existujúci tunel ────────────────────
mkdir -p "$CF_DIR"
CREDS_FILE="${CF_DIR}/${TUNNEL_NAME}.json"

info "Hľadám existujúci tunel '${TUNNEL_NAME}'..."
EXISTING=$(cf_api GET "/accounts/${ACCOUNT_ID}/cfd_tunnel?name=${TUNNEL_NAME}&is_deleted=false")
TUNNEL_ID=$(echo "$EXISTING" | python3 -c "
import sys,json
d=json.load(sys.stdin)
r=d.get('result',[])
print(r[0]['id'] if r else '')
" 2>/dev/null || echo "")

if [ -n "$TUNNEL_ID" ]; then
  warn "Tunel '${TUNNEL_NAME}' už existuje (ID: ${TUNNEL_ID})"
  read -p "  Použiť existujúci? [Y/n]: " USE_EXISTING
  USE_EXISTING="${USE_EXISTING:-Y}"
  if [[ "$USE_EXISTING" =~ ^[Nn] ]]; then
    fail "Zruš existujúci tunel ručne v Cloudflare dashboarde a spusti znova"
  fi
  TUNNEL_TOKEN=$(echo "$EXISTING" | python3 -c "
import sys,json
d=json.load(sys.stdin)
print(d['result'][0].get('token',''))
" 2>/dev/null || echo "")
else
  info "Vytváram nový tunel '${TUNNEL_NAME}'..."
  RESPONSE=$(cf_api POST "/accounts/${ACCOUNT_ID}/cfd_tunnel" \
    "{\"name\":\"${TUNNEL_NAME}\",\"config_src\":\"cloudflare\"}")
  TUNNEL_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['result']['id'])")
  TUNNEL_TOKEN=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['result']['token'])")
  ok "Tunel vytvorený (ID: ${TUNNEL_ID})"
fi

# ── 6. Nastav ingress cez Cloudflare API (config_src=cloudflare) ──
info "Nastavujem ingress pravidlá pre tunel..."
cf_api PUT "/accounts/${ACCOUNT_ID}/cfd_tunnel/${TUNNEL_ID}/configurations" \
  "{
    \"config\": {
      \"ingress\": [
        {
          \"hostname\": \"${HOSTNAME}\",
          \"service\": \"https://localhost\",
          \"originRequest\": {
            \"noTLSVerify\": true
          }
        },
        {
          \"service\": \"http_status:404\"
        }
      ]
    }
  }" > /dev/null
ok "Ingress nastavený: ${HOSTNAME} → https://localhost (nginx)"

# ── 7. DNS CNAME záznam ────────────────────────────────────────
info "Nastavujem DNS CNAME ${SUBDOMAIN} → ${TUNNEL_ID}.cfargotunnel.com ..."
CNAME_TARGET="${TUNNEL_ID}.cfargotunnel.com"

# Skontroluj či záznam existuje
EXISTING_DNS=$(cf_api GET "/zones/${ZONE_ID}/dns_records?type=CNAME&name=${HOSTNAME}" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); r=d.get('result',[]); print(r[0]['id'] if r else '')" 2>/dev/null || echo "")

if [ -n "$EXISTING_DNS" ]; then
  cf_api PUT "/zones/${ZONE_ID}/dns_records/${EXISTING_DNS}" \
    "{\"type\":\"CNAME\",\"name\":\"${SUBDOMAIN}\",\"content\":\"${CNAME_TARGET}\",\"proxied\":true,\"ttl\":1}" > /dev/null
  ok "DNS CNAME aktualizovaný"
else
  cf_api POST "/zones/${ZONE_ID}/dns_records" \
    "{\"type\":\"CNAME\",\"name\":\"${SUBDOMAIN}\",\"content\":\"${CNAME_TARGET}\",\"proxied\":true,\"ttl\":1}" > /dev/null
  ok "DNS CNAME vytvorený"
fi

# ── 8. Ulož token do .env ──────────────────────────────────────
if ! grep -q "CF_TUNNEL_TOKEN" "$ENV_FILE" 2>/dev/null; then
  echo "" >> "$ENV_FILE"
  echo "# ── Cloudflare Tunnel ────────────────────────────────────────────────────────" >> "$ENV_FILE"
  echo "CF_TUNNEL_TOKEN=${TUNNEL_TOKEN}" >> "$ENV_FILE"
  echo "CF_TUNNEL_NAME=${TUNNEL_NAME}" >> "$ENV_FILE"
  echo "CF_TUNNEL_SUBDOMAIN=${SUBDOMAIN}" >> "$ENV_FILE"
  ok "Token uložený do .env"
else
  # Aktualizuj existujúci
  sed -i "s|^CF_TUNNEL_TOKEN=.*|CF_TUNNEL_TOKEN=${TUNNEL_TOKEN}|" "$ENV_FILE"
  ok "Token aktualizovaný v .env"
fi

# ── 9. systemd service ─────────────────────────────────────────
info "Inštalujem systemd service (cloudflared-wifikeeper)..."
sudo tee /etc/systemd/system/cloudflared-wifikeeper.service > /dev/null <<EOF
[Unit]
Description=Cloudflare Tunnel – wifikeeper
After=network-online.target docker.service
Wants=network-online.target
Requires=docker.service

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/cloudflared tunnel run --token ${TUNNEL_TOKEN}
Restart=on-failure
RestartSec=5s
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable cloudflared-wifikeeper
sudo systemctl restart cloudflared-wifikeeper
sleep 2

if sudo systemctl is-active --quiet cloudflared-wifikeeper; then
  ok "cloudflared-wifikeeper service beží"
else
  warn "Service sa nespustil — skontroluj: journalctl -u cloudflared-wifikeeper -n 50"
fi

# ── Výsledok ───────────────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║              Setup dokončený!                ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${GREEN}${BOLD}URL:${NC} https://${HOSTNAME}"
echo ""
echo -e "  Tunel ID:   ${TUNNEL_ID}"
echo -e "  Service:    sudo systemctl status cloudflared-wifikeeper"
echo -e "  Logy:       journalctl -u cloudflared-wifikeeper -f"
echo ""
