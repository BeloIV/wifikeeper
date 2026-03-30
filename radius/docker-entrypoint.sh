#!/bin/sh
set -e

# Substituuj env premenné v konfiguračných šablónach
# envsubst nahradí ${VAR} v .template súboroch

CONF_SRC=/etc/freeradius/3.0
CONF_DIR=/etc/freeradius

for template in $CONF_SRC/**/*.template $CONF_SRC/*.template; do
    [ -f "$template" ] || continue
    dest="${template%.template}"
    envsubst < "$template" > "$dest"
    echo "Generated: $dest"
done

# Skopíruj vlastné konfiguračné súbory do skutočného konfig adresára
# kde FreeRADIUS číta konfiguráciu (/etc/freeradius, nie /etc/freeradius/3.0)

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

# modules — envsubst len pre naše Docker env premenné (FR_*, RADIUS_*), nie FreeRADIUS interné
OUR_VARS='$FR_POSTGRES_HOST $FR_POSTGRES_USER $FR_POSTGRES_PASS $FR_POSTGRES_DB $FR_LDAP_HOST $FR_LDAP_BASE_DN $FR_LDAP_BIND_DN $FR_LDAP_BIND_PASS $RADIUS_SECRET $RADIUS_CLIENT_NETWORK'
for mod in sql ldap eap; do
    if [ -f "$CONF_SRC/mods-available/$mod" ]; then
        envsubst "$OUR_VARS" < "$CONF_SRC/mods-available/$mod" > "$CONF_DIR/mods-available/$mod"
        ln -sf "$CONF_DIR/mods-available/$mod" "$CONF_DIR/mods-enabled/$mod"
        echo "Enabled module: $mod"
    fi
done

# policy.d — skopíruj všetky okrem vlan_policy (ten generujeme z DB)
if [ -d "$CONF_SRC/policy.d" ]; then
    for f in "$CONF_SRC/policy.d/"*; do
        name=$(basename "$f")
        [ "$name" = "vlan_policy" ] && continue
        cp "$f" "$CONF_DIR/policy.d/$name"
    done
    echo "Copied policy.d"
fi

# Vygeneruj vlan_policy z PostgreSQL DB
echo "Generating vlan_policy from DB..."
VLAN_POLICY="$CONF_DIR/policy.d/vlan_policy"

# Čakaj kým DB bude dostupná (max 30s)
i=0
until PGPASSWORD="$FR_POSTGRES_PASS" psql -h "$FR_POSTGRES_HOST" -U "$FR_POSTGRES_USER" -d "$FR_POSTGRES_DB" -c '\q' 2>/dev/null; do
    i=$((i+1))
    [ $i -ge 30 ] && echo "DB not ready, using fallback vlan_policy" && break
    sleep 1
done

# Začiatok súboru
cat > "$VLAN_POLICY" <<'EOF'
# VLAN policy — generovaný pri štarte z DB (users_ldapgroup)
# Pre zmenu skupín reštartuj freeradius kontajner.

vlan_policy {
EOF

# Pridaj if/elsif blok pre každú skupinu z DB
PGPASSWORD="$FR_POSTGRES_PASS" psql -h "$FR_POSTGRES_HOST" -U "$FR_POSTGRES_USER" \
    -d "$FR_POSTGRES_DB" -t -A \
    -c "SELECT name, vlan FROM users_ldapgroup ORDER BY name" 2>/dev/null \
| while IFS='|' read -r grp vlan; do
    [ -z "$grp" ] && continue
    cat >> "$VLAN_POLICY" <<EOF
    if (LDAP-Group == "${grp}") {
        update reply {
            Tunnel-Type             := VLAN
            Tunnel-Medium-Type      := IEEE-802
            Tunnel-Private-Group-Id := "${vlan}"
        }
    }
    elsif
EOF
done

# Uzatvárajúci else blok (odstráň posledný elsif a pridaj else)
# Zapíš priamo uzatvárací blok
cat >> "$VLAN_POLICY" <<'EOF'
    (1 == 2) {
        # placeholder — nikdy sa nevykoná
        noop
    }
    else {
        update reply {
            Reply-Message := "Pristup odmietnuty: pouzivatel nie je clenom ziadnej povolenej skupiny"
        }
        reject
    }
}
EOF

echo "Generated vlan_policy with $(PGPASSWORD="$FR_POSTGRES_PASS" psql -h "$FR_POSTGRES_HOST" -U "$FR_POSTGRES_USER" -d "$FR_POSTGRES_DB" -t -c "SELECT COUNT(*) FROM users_ldapgroup" 2>/dev/null | tr -d ' ') groups"

# mods-config (sql queries, eap certs config, etc.)
if [ -d "$CONF_SRC/mods-config" ]; then
    cp -r "$CONF_SRC/mods-config/." "$CONF_DIR/mods-config/"
    echo "Copied mods-config"
fi

exec "$@"
