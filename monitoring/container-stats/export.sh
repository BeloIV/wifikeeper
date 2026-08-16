#!/bin/sh
# Exportuje per-kontajner CPU/RAM z `docker stats` do Prometheus textfile formátu.
# Náhrada za cAdvisor, ktorý na tomto hoste nevie priradiť kontajnery kvôli
# containerd snapshotter storage drivru (nie je schopný nájsť read-write layer).
set -eu

OUT_DIR="/textfile"
TMP="$OUT_DIR/container_stats.prom.tmp"
FINAL="$OUT_DIR/container_stats.prom"

to_bytes() {
  echo "$1" | awk '
    {
      if (match($0, /GiB$/)) { sub(/GiB$/,""); print $0*1024*1024*1024; exit }
      if (match($0, /MiB$/)) { sub(/MiB$/,""); print $0*1024*1024; exit }
      if (match($0, /KiB$/)) { sub(/KiB$/,""); print $0*1024; exit }
      if (match($0, /B$/))   { sub(/B$/,"");   print $0; exit }
      print 0
    }'
}

while true; do
  {
    echo "# HELP wifikeeper_container_cpu_percent Docker stats CPU percent per container"
    echo "# TYPE wifikeeper_container_cpu_percent gauge"
    echo "# HELP wifikeeper_container_memory_used_bytes Docker stats memory usage per container"
    echo "# TYPE wifikeeper_container_memory_used_bytes gauge"
    echo "# HELP wifikeeper_container_memory_limit_bytes Docker stats memory limit per container"
    echo "# TYPE wifikeeper_container_memory_limit_bytes gauge"

    docker stats --no-stream --format '{{.Name}}|{{.CPUPerc}}|{{.MemUsage}}' 2>/dev/null | \
    while IFS='|' read -r name cpu mem; do
      name_clean=$(echo "$name" | sed 's#^/##')
      cpu_val=$(echo "$cpu" | tr -d '%')
      case "$cpu_val" in ''|*[!0-9.]*) cpu_val=0 ;; esac

      used=$(echo "$mem" | awk -F'/' '{gsub(/^ +| +$/,"",$1); print $1}')
      limit=$(echo "$mem" | awk -F'/' '{gsub(/^ +| +$/,"",$2); print $2}')
      used_bytes=$(to_bytes "$used")
      limit_bytes=$(to_bytes "$limit")

      echo "wifikeeper_container_cpu_percent{name=\"$name_clean\"} $cpu_val"
      echo "wifikeeper_container_memory_used_bytes{name=\"$name_clean\"} $used_bytes"
      echo "wifikeeper_container_memory_limit_bytes{name=\"$name_clean\"} $limit_bytes"
    done

    echo "# HELP wifikeeper_container_up 1 ak kontajner beží, 0 ak nie (zastavený/crash-loop)"
    echo "# TYPE wifikeeper_container_up gauge"
    docker ps -a --filter "label=com.docker.compose.project=wifikeeper" \
      --format '{{.Names}}|{{.State}}|{{.Label "com.docker.compose.service"}}' 2>/dev/null | \
    while IFS='|' read -r name state svc; do
      # jednorazové init/migration joby (restart: "no") nie sú trvalé služby, vynechať
      case "$svc" in init|certbot) continue ;; esac
      name_clean=$(echo "$name" | sed 's#^/##')
      if [ "$state" = "running" ]; then up=1; else up=0; fi
      echo "wifikeeper_container_up{name=\"$name_clean\",state=\"$state\"} $up"
    done
  } > "$TMP"
  mv "$TMP" "$FINAL"
  sleep 15
done
