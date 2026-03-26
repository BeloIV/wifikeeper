#!/bin/bash
# =============================================================================
# Let's Encrypt deploy hook – spustí sa po každom úspešnom obnovení certifikátu
# Nakopíruje cert do FreeRADIUS a reloaduje ho.
#
# Inštalácia:
#   chmod +x scripts/deploy-cert-hook.sh
#   ln -s /absolútna/cesta/k/scripts/deploy-cert-hook.sh \
#         /etc/letsencrypt/renewal-hooks/deploy/wifi-manager-radius.sh
#
# Premenné prostredia nastavuje certbot automaticky:
#   RENEWED_LINEAGE  – cesta k obnovenému certifikátu (/etc/letsencrypt/live/DOMAIN)
#   RENEWED_DOMAINS  – zoznam domén oddelený medzerami
# =============================================================================

set -e

COMPOSE_FILE="/opt/wifi-manager/docker-compose.prod.yml"
RADIUS_CONTAINER="wifi-manager-freeradius-1"

echo "[$(date)] Deploy hook spustený pre: $RENEWED_DOMAINS"
echo "  Certifikát: $RENEWED_LINEAGE"

# FreeRADIUS má certifikáty mountované priamo z /etc/letsencrypt/live/DOMAIN
# (volume mount v docker-compose.prod.yml), takže stačí reloadovať proces.

# Reload FreeRADIUS (pošle SIGHUP)
if docker ps --format '{{.Names}}' | grep -q "^${RADIUS_CONTAINER}$"; then
    docker kill --signal=SIGHUP "$RADIUS_CONTAINER"
    echo "[$(date)] FreeRADIUS reloadovaný."
else
    echo "[$(date)] Kontajner $RADIUS_CONTAINER nenájdený, skúšam cez docker compose..."
    if [ -f "$COMPOSE_FILE" ]; then
        docker compose -f "$COMPOSE_FILE" kill --signal=SIGHUP freeradius
        echo "[$(date)] FreeRADIUS reloadovaný cez docker compose."
    else
        echo "[$(date)] VAROVANIE: Nepodarilo sa reloadovať FreeRADIUS. Reštartuj ho manuálne."
        exit 1
    fi
fi

# Reload nginx
NGINX_CONTAINER="wifi-manager-nginx-1"
if docker ps --format '{{.Names}}' | grep -q "^${NGINX_CONTAINER}$"; then
    docker exec "$NGINX_CONTAINER" nginx -s reload
    echo "[$(date)] Nginx reloadovaný."
fi

echo "[$(date)] Deploy hook dokončený."
