#!/bin/bash
# =============================================================================
# Let's Encrypt deploy hook – spustí sa po každom úspešnom obnovení certifikátu
# Nakopíruje cert do ./certs/ (pre FreeRADIUS) a reloaduje RADIUS + nginx.
#
# Inštalácia:
#   chmod +x scripts/deploy-cert-hook.sh
#   ln -s /absolútna/cesta/k/scripts/deploy-cert-hook.sh \
#         /etc/letsencrypt/renewal-hooks/deploy/wifi-manager-radius.sh
#
# Premenné prostredia nastavuje certbot automaticky:
#   RENEWED_LINEAGE  – cesta k obnovenému certifikátu (/etc/letsencrypt/live/DOMAIN)
#   RENEWED_DOMAINS  – zoznam domén oddelený medzerami
#
# Voliteľné:
#   WIFIMANAGER_DIR  – absolútna cesta k projektu (default: /opt/wifi-manager)
# =============================================================================

set -e

WIFIMANAGER_DIR="${WIFIMANAGER_DIR:-/opt/wifi-manager}"
COMPOSE_FILE="$WIFIMANAGER_DIR/docker-compose.prod.yml"
CERTS_DIR="$WIFIMANAGER_DIR/certs"
RADIUS_CONTAINER="wifi-manager-freeradius-1"
NGINX_CONTAINER="wifi-manager-nginx-1"

echo "[$(date)] Deploy hook spustený pre: $RENEWED_DOMAINS"
echo "  Certifikát: $RENEWED_LINEAGE"
echo "  Cieľový adresár: $CERTS_DIR"

# ── Skopíruj LE certy do ./certs/ (s -L = dereference symlinkov) ─────────────
# LE ukladá v live/ symlinky na archive/ – v Docker kontajneri by boli rozbité.
# Kopírujeme fyzické súbory s názvami, ktoré FreeRADIUS očakáva.

cp -L "$RENEWED_LINEAGE/fullchain.pem" "$CERTS_DIR/server.crt"
cp -L "$RENEWED_LINEAGE/privkey.pem"   "$CERTS_DIR/server.key"
chmod 640 "$CERTS_DIR/server.key"

echo "[$(date)] Certifikáty skopírované do $CERTS_DIR"
echo "  server.crt ← fullchain.pem"
echo "  server.key ← privkey.pem"

# dh a ca.crt sú statické (generované raz cez scripts/gen-self-signed.sh) – nemeniť

# ── Skopíruj certy pre OpenLDAP ───────────────────────────────────────────────
LDAP_CERTS_DIR="$WIFIMANAGER_DIR/data/ldap-certs"
if [ -d "$LDAP_CERTS_DIR" ]; then
    cp -L "$RENEWED_LINEAGE/fullchain.pem" "$LDAP_CERTS_DIR/ldap.crt"
    cp -L "$RENEWED_LINEAGE/privkey.pem"   "$LDAP_CERTS_DIR/ldap.key"
    cp -L "$RENEWED_LINEAGE/chain.pem"     "$LDAP_CERTS_DIR/ca.crt"
    chmod 640 "$LDAP_CERTS_DIR/ldap.key"
    echo "[$(date)] OpenLDAP certifikáty aktualizované."
fi

# ── Reload FreeRADIUS (SIGHUP – znovu načíta TLS cert bez výpadku) ────────────
if docker ps --format '{{.Names}}' | grep -q "^${RADIUS_CONTAINER}$"; then
    docker kill --signal=SIGHUP "$RADIUS_CONTAINER"
    echo "[$(date)] FreeRADIUS reloadovaný."
elif [ -f "$COMPOSE_FILE" ]; then
    docker compose -f "$COMPOSE_FILE" kill --signal=SIGHUP freeradius
    echo "[$(date)] FreeRADIUS reloadovaný cez docker compose."
else
    echo "[$(date)] VAROVANIE: Nepodarilo sa reloadovať FreeRADIUS. Reštartuj ho manuálne."
    exit 1
fi

# ── Reload nginx ───────────────────────────────────────────────────────────────
if docker ps --format '{{.Names}}' | grep -q "^${NGINX_CONTAINER}$"; then
    docker exec "$NGINX_CONTAINER" nginx -s reload
    echo "[$(date)] Nginx reloadovaný."
fi

echo "[$(date)] Deploy hook dokončený."
