#!/bin/sh
set -e

CONF_SRC=/etc/freeradius/3.0
CONF_DIR=/etc/freeradius

# Substituuj env premenné v konfiguračných šablónach
for template in $CONF_SRC/**/*.template $CONF_SRC/*.template; do
    [ -f "$template" ] || continue
    dest="${template%.template}"
    envsubst < "$template" > "$dest"
    echo "Generated: $dest"
done

# clients.conf
cp "$CONF_SRC/clients.conf" "$CONF_DIR/clients.conf"
echo "Copied clients.conf"

# sites
for site in default inner-tunnel; do
    if [ -f "$CONF_SRC/sites-available/$site" ]; then
        cp "$CONF_SRC/sites-available/$site" "$CONF_DIR/sites-available/$site"
        ln -sf "$CONF_DIR/sites-available/$site" "$CONF_DIR/sites-enabled/$site"
        echo "Enabled site: $site"
    fi
done

# modules — envsubst len pre naše Docker env premenné
OUR_VARS='$FR_POSTGRES_HOST $FR_POSTGRES_USER $FR_POSTGRES_PASS $FR_POSTGRES_DB $FR_LDAP_HOST $FR_LDAP_BASE_DN $FR_LDAP_BIND_DN $FR_LDAP_BIND_PASS $RADIUS_SECRET $RADIUS_CLIENT_NETWORK'
for mod in sql ldap eap; do
    if [ -f "$CONF_SRC/mods-available/$mod" ]; then
        envsubst "$OUR_VARS" < "$CONF_SRC/mods-available/$mod" > "$CONF_DIR/mods-available/$mod"
        ln -sf "$CONF_DIR/mods-available/$mod" "$CONF_DIR/mods-enabled/$mod"
        echo "Enabled module: $mod"
    fi
done

# policy.d — skopíruj všetky (vlan_policy je statická, číta radreply dynamicky)
if [ -d "$CONF_SRC/policy.d" ]; then
    for f in "$CONF_SRC/policy.d/"*; do
        cp "$f" "$CONF_DIR/policy.d/$(basename "$f")"
    done
    echo "Copied policy.d"
fi

# mods-config
if [ -d "$CONF_SRC/mods-config" ]; then
    cp -r "$CONF_SRC/mods-config/." "$CONF_DIR/mods-config/"
    echo "Copied mods-config"
fi

exec "$@"
