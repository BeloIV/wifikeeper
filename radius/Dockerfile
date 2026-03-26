FROM freeradius/freeradius-server:latest

# PostgreSQL klient pre testovanie spojenia
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gettext-base \
    && rm -rf /var/lib/apt/lists/*

# Skopírujeme konfiguráciu – bude overrideovaná volume-mountom
COPY config/ /etc/freeradius/3.0/

# Entrypoint skript – substituuje env premenné v konfigurácii
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 1812/udp 1813/udp 3799/udp

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["freeradius", "-X"]
