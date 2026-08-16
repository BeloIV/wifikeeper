#!/bin/sh
# Read-only rola pre Grafana (Postgres datasource).
# Beží automaticky iba pri prvej inicializácii prázdneho postgres volume,
# teda PRED tým, ako Django migrácie vytvoria tabuľku radius_sessions.
# Preto tu vytvárame len rolu + DB/schema práva; samotný GRANT SELECT na
# radius_sessions dorobí `init` kontajner po `manage.py migrate`
# (docker-compose.yml, služba `init`) — tabuľka musí existovať pred grantom.
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
  DO \$\$
  BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'grafana_ro') THEN
      CREATE ROLE grafana_ro LOGIN PASSWORD '${GRAFANA_PG_PASSWORD}';
    END IF;
  END
  \$\$;

  GRANT CONNECT ON DATABASE "$POSTGRES_DB" TO grafana_ro;
  GRANT USAGE ON SCHEMA public TO grafana_ro;
EOSQL
