#!/bin/sh
# Zbiera REÁLNE interné štatistiky FreeRADIUS cez Status-Server socket
# a zapisuje ich do Prometheus textfile formátu.
#
# Prečo takto:
#  - Sú to čísla o SKUTOČNEJ prevádzke reálnych používateľov, nie syntetický test.
#  - Stats-Elapsed-* je histogram latencie, ktorý meria priamo FreeRADIUS
#    (pokrýva všetky pakety vrátane EAP challenge, nielen posledný).
#  - Auth-Duplicate-Requests = AP nedostal odpoveď včas a poslal request znova.
#    To je priamo ten príznak, ktorý hlási UniFi ("server neodpovedá").
#
# Status socket počúva len na 127.0.0.1 VNÚTRI freeradius kontajnera,
# preto sa naň dotazujeme cez `docker exec` (žiadny port navonok).
set -eu

OUT_DIR="/textfile"
TMP="$OUT_DIR/radius_stats.prom.tmp"
FINAL="$OUT_DIR/radius_stats.prom"
FR_CONTAINER="wifikeeper-freeradius-1"

# Mapovanie: FreeRADIUS atribút -> názov Prometheus metriky
emit_counter() {
    attr="$1"; metric="$2"; help="$3"; data="$4"
    value=$(echo "$data" | sed -n "s/.*${attr} = \([0-9][0-9]*\).*/\1/p" | head -1)
    [ -n "$value" ] || return 0
    echo "# HELP $metric $help"
    echo "# TYPE $metric counter"
    echo "$metric $value"
}

while true; do
    stats=$(docker exec "$FR_CONTAINER" sh -c \
        "echo 'Message-Authenticator = 0x00, FreeRADIUS-Statistics-Type = 1' | \
         radclient -x 127.0.0.1:18121 status \"\$RADIUS_STATUS_SECRET\"" 2>/dev/null || true)

    if [ -n "$stats" ]; then
        {
            emit_counter "FreeRADIUS-Total-Access-Requests" \
                "wifikeeper_radius_access_requests_total" \
                "Celkovy pocet Access-Request paketov" "$stats"
            emit_counter "FreeRADIUS-Total-Access-Accepts" \
                "wifikeeper_radius_access_accepts_total" \
                "Celkovy pocet uspesnych prihlaseni" "$stats"
            emit_counter "FreeRADIUS-Total-Access-Rejects" \
                "wifikeeper_radius_access_rejects_total" \
                "Celkovy pocet odmietnutych prihlaseni" "$stats"
            emit_counter "FreeRADIUS-Total-Auth-Duplicate-Requests" \
                "wifikeeper_radius_auth_duplicate_requests_total" \
                "Retransmisie od AP = server neodpovedal vcas" "$stats"
            emit_counter "FreeRADIUS-Total-Auth-Dropped-Requests" \
                "wifikeeper_radius_auth_dropped_requests_total" \
                "Pakety zahodene serverom" "$stats"

            # Histogram latencie reálnych requestov.
            # Pozor: FreeRADIUS vracia POCET requestov v danom koši, kose nie su kumulativne.
            echo "# HELP wifikeeper_radius_latency_bucket_total Pocet realnych requestov v danom kosi latencie"
            echo "# TYPE wifikeeper_radius_latency_bucket_total counter"
            for b in 1us 10us 100us 1ms 10ms 100ms 1s 10s; do
                v=$(echo "$stats" | sed -n "s/.*FreeRADIUS-Stats-Elapsed-${b} = \([0-9][0-9]*\).*/\1/p" | head -1)
                [ -n "$v" ] || continue
                echo "wifikeeper_radius_latency_bucket_total{bucket=\"$b\"} $v"
            done

            echo "# HELP wifikeeper_radius_stats_up 1 ak sa podarilo precitat statistiky"
            echo "# TYPE wifikeeper_radius_stats_up gauge"
            echo "wifikeeper_radius_stats_up 1"
        } > "$TMP"
        mv "$TMP" "$FINAL"
    else
        echo "wifikeeper_radius_stats_up 0" > "$TMP"
        mv "$TMP" "$FINAL"
    fi

    sleep 30
done
