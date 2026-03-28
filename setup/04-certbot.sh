#!/bin/bash
# 04-certbot.sh - Let's Encrypt certifikát cez Cloudflare DNS-01
# Spusti ako: bash 04-certbot.sh

set -e

echo "=== 04-certbot.sh: Certbot + Let's Encrypt ==="

# --- Premenné (z setup.sh alebo defaults) ---
DOMAIN="${CFG_DOMAIN:-radius.tvoja-domena.xyz}"
EMAIL="${CFG_EMAIL:-tvoj@email.com}"
CF_TOKEN="${CFG_CF_TOKEN:-CLOUDFLARE_API_TOKEN_SEM}"
PROJECT_DIR="${CFG_PROJECT_DIR:-/opt/wifi-manager}"

# --- Inštalácia Certbot ---
echo "[1/4] Inštalujem Certbot..."
sudo apt install -y certbot python3-certbot-dns-cloudflare
echo "Certbot nainštalovaný ✓"

# --- Cloudflare credentials ---
echo "[2/4] Vytváram Cloudflare credentials..."
sudo mkdir -p /etc/cloudflare
sudo tee /etc/cloudflare/credentials.ini > /dev/null <<EOF
dns_cloudflare_api_token = $CF_TOKEN
EOF
sudo chmod 600 /etc/cloudflare/credentials.ini
echo "Credentials uložené ✓"

# --- Vydaj certifikát ---
echo "[3/4] Vydávam certifikát pre $DOMAIN..."
sudo certbot certonly \
    --dns-cloudflare \
    --dns-cloudflare-credentials /etc/cloudflare/credentials.ini \
    --dns-cloudflare-propagation-seconds 30 \
    -d "$DOMAIN" \
    --email "$EMAIL" \
    --agree-tos \
    --non-interactive
echo "Certifikát vydaný ✓"

# --- Deploy hook pre FreeRADIUS (Docker) ---
echo "[4/4] Vytváram deploy hook..."
sudo tee /etc/letsencrypt/renewal-hooks/deploy/wifi-manager.sh > /dev/null <<EOF
#!/bin/bash
# Po obnovení certifikátu: skopíruj certy do projektu a reštartuj RADIUS kontajner
set -e

PROJECT_DIR="$PROJECT_DIR"
DOMAIN="$DOMAIN"

mkdir -p "\$PROJECT_DIR/certs"
cp /etc/letsencrypt/live/\$DOMAIN/fullchain.pem \$PROJECT_DIR/certs/server.crt
cp /etc/letsencrypt/live/\$DOMAIN/privkey.pem  \$PROJECT_DIR/certs/server.key
chmod 644 \$PROJECT_DIR/certs/server.pem
chmod 640 \$PROJECT_DIR/certs/server.key

docker compose -f \$PROJECT_DIR/docker-compose.yml restart radius
EOF
sudo chmod +x /etc/letsencrypt/renewal-hooks/deploy/wifi-manager.sh
echo "Deploy hook vytvorený ✓"

# --- Prvé skopírovanie certov ---
echo "Kopírujem certifikáty do projektu..."
mkdir -p "$PROJECT_DIR/certs"
sudo cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem "$PROJECT_DIR/certs/server.crt"
sudo cp /etc/letsencrypt/live/$DOMAIN/privkey.pem  "$PROJECT_DIR/certs/server.key"
sudo chmod 644 "$PROJECT_DIR/certs/server.crt"
sudo chmod 640 "$PROJECT_DIR/certs/server.key"
echo "Certifikáty skopírované do $PROJECT_DIR/certs/ ✓"

# --- Test obnovy ---
echo "Testujem automatickú obnovu..."
sudo certbot renew --dry-run

echo ""
echo "Certifikáty sú v: /etc/letsencrypt/live/$DOMAIN/"
echo ""
echo "=== 04-certbot.sh HOTOVO ==="
echo "Pokračuj: bash 05-ssh-hardening.sh"
