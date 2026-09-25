#!/bin/sh
# Foreground: nginx (statik JSON). Arka plan: haftalık Diyanet çekimi.
set -eu
DATA="${VAKITLER_DATA:-/data}"
DAYS="${FETCH_INTERVAL_DAYS:-7}"
mkdir -p "$DATA/vakitler"
cp /app/iller.json "$DATA/iller.json"

fetch_loop() {
    while true; do
        REPORT="$DATA/fetch_report.json"
        if [ -f "$REPORT" ] && [ -n "$(find "$REPORT" -mtime "-$((DAYS - 1))" 2>/dev/null)" ]; then
            echo "[vakitler] veri güncel ($(date -u +%F)); atlanıyor"
        else
            echo "[vakitler] çekim başlıyor $(date -u +%FT%TZ)"
            if python3 /app/scripts/fetch_vakitler.py --out "$DATA"; then
                echo "[vakitler] çekim bitti $(date -u +%FT%TZ)"
            else
                echo "[vakitler] çekim HATA; eski dosyalar korunuyor"
            fi
        fi
        sleep 3600
    done
}

fetch_loop &
exec nginx -g 'daemon off;'
