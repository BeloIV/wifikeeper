#!/bin/sh
set -e

# Substituuj env premenné v konfiguračných šablónach
# envsubst nahradí ${VAR} v .template súboroch

for template in /etc/freeradius/3.0/**/*.template /etc/freeradius/3.0/*.template; do
    [ -f "$template" ] || continue
    dest="${template%.template}"
    envsubst < "$template" > "$dest"
    echo "Generated: $dest"
done

# Aktivuj moduly a sites (symlinky)
for mod in sql ldap eap; do
    if [ -f "/etc/freeradius/3.0/mods-available/$mod" ]; then
        ln -sf "/etc/freeradius/3.0/mods-available/$mod" \
               "/etc/freeradius/3.0/mods-enabled/$mod" 2>/dev/null || true
    fi
done

for site in default inner-tunnel; do
    if [ -f "/etc/freeradius/3.0/sites-available/$site" ]; then
        ln -sf "/etc/freeradius/3.0/sites-available/$site" \
               "/etc/freeradius/3.0/sites-enabled/$site" 2>/dev/null || true
    fi
done

# Odstráň defaultné sites ktoré nechceme
rm -f /etc/freeradius/3.0/sites-enabled/default.orig
rm -f /etc/freeradius/3.0/sites-enabled/inner-tunnel.orig

exec "$@"
