FROM freeradius/freeradius-server:latest

# PostgreSQL klient pre testovanie spojenia
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    postgresql-client \
    gettext-base \
    && rm -rf /var/lib/apt/lists/*

# Skopírujeme konfiguráciu – bude overrideovaná volume-mountom
COPY config/ /etc/freeradius/3.0/

# Entrypoint skript – substituuje env premenné v konfigurácii
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 1812/udp 1813/udp 3799/udp

ENTRYPOINT ["/docker-entrypoint.sh"]
# -X (plný debug) sa nemá používať v produkcii — FreeRADIUS to explicitne
# odporúča nerobiť. Spôsoboval obrovský objem logov (~370k riadkov/deň),
# ktorý pri zápise na stdout vedel zablokovať samotné spracovanie RADIUS
# requestov (namerané oneskorenia v EAP-PEAP konverzáciách až do 30s).
# -f = foreground (nutné pre Docker), -l stdout = normálne logy naďalej
# na stdout (viditeľné v `docker compose logs` aj Loki/Grafana).
CMD ["freeradius", "-f", "-l", "stdout"]
