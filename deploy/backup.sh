#!/usr/bin/env bash
# PostgreSQL bazasining zaxira nusxasi: ./backups/db_YYYY-mm-dd_HHMM.sql.gz
# Cron (har kuni 03:00):  0 3 * * * cd /opt/SayxunTeamTest && ./deploy/backup.sh >> backups/backup.log 2>&1
set -euo pipefail
cd "$(dirname "$0")/.."

KEEP_DAYS="${KEEP_DAYS:-14}"
mkdir -p backups
file="backups/db_$(date +%Y-%m-%d_%H%M).sql.gz"

docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --clean --if-exists' | gzip > "$file"
echo "$(date '+%F %T') zaxira: $file ($(du -h "$file" | cut -f1))"

find backups -name 'db_*.sql.gz' -mtime +"$KEEP_DAYS" -delete
