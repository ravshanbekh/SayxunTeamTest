#!/usr/bin/env bash
# Yangi versiyani o'rnatish: git'dan oxirgi o'zgarishlarni olib, qayta build qilish
set -euo pipefail
cd "$(dirname "$0")/.."

./deploy/backup.sh
git pull --ff-only
docker compose up -d --build
docker image prune -f
docker compose ps
