#!/usr/bin/env bash
# Zaxiradan tiklash:  ./deploy/restore.sh backups/db_2026-10-21_0300.sql.gz
set -euo pipefail
cd "$(dirname "$0")/.."

file="${1:?Foydalanish: ./deploy/restore.sh backups/db_....sql.gz}"
read -r -p "Joriy baza '$file' bilan almashtiriladi. Davom etilsinmi? (yes/no) " answer
[ "$answer" = "yes" ] || { echo "Bekor qilindi"; exit 1; }

docker compose stop bot backend
gunzip -c "$file" | docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1'
docker compose start backend bot
echo "Tiklandi: $file"
