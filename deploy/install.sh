#!/usr/bin/env bash
# Yangi Ubuntu serverga to'liq o'rnatish (root sifatida):
#   curl -fsSL https://raw.githubusercontent.com/ravshanbekh/SayxunTeamTest/main/deploy/install.sh | bash
# yoki repo clone qilingan bo'lsa:  bash deploy/install.sh
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/SayxunTeamTest}"
REPO_URL="${REPO_URL:-https://github.com/ravshanbekh/SayxunTeamTest.git}"

[ "$(id -u)" -eq 0 ] || { echo "root sifatida ishga tushiring (sudo -i)"; exit 1; }

echo "==> 1/6 Paketlar va Docker"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y git curl ufw openssl
if ! command -v docker >/dev/null 2>&1; then
    curl -fsSL https://get.docker.com | sh
fi
systemctl enable --now docker

echo "==> 2/6 Firewall (22, 80, 443)"
ufw allow OpenSSH >/dev/null
ufw allow 80/tcp >/dev/null
ufw allow 443/tcp >/dev/null
ufw allow 443/udp >/dev/null
ufw --force enable >/dev/null

echo "==> 3/6 Loyiha: $APP_DIR"
if [ -d "$APP_DIR/.git" ]; then
    git -C "$APP_DIR" pull --ff-only
else
    git clone "$REPO_URL" "$APP_DIR"
fi
cd "$APP_DIR"

echo "==> 4/6 .env"
if [ ! -f .env ]; then
    ip="$(curl -fsS4 https://api.ipify.org || hostname -I | awk '{print $1}')"
    default_domain="$(echo "$ip" | tr '.' '-').sslip.io"
    read -r -p "Domen [$default_domain]: " domain < /dev/tty
    domain="${domain:-$default_domain}"
    read -r -p "Telegram BOT_TOKEN: " bot_token < /dev/tty
    [ -n "$bot_token" ] || { echo "BOT_TOKEN bo'sh bo'lmasligi kerak"; exit 1; }
    cp .env.example .env
    sed -i "s|^DOMAIN=.*|DOMAIN=$domain|" .env
    sed -i "s|^BOT_TOKEN=.*|BOT_TOKEN=$bot_token|" .env
    sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$(openssl rand -hex 24)|" .env
    sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$(openssl rand -hex 32)|" .env
    chmod 600 .env
    echo ".env yaratildi (DOMAIN=$domain)"
else
    echo ".env mavjud - o'zgartirilmadi"
fi

echo "==> 5/6 Build va ishga tushirish"
docker compose up -d --build
for _ in $(seq 1 60); do
    status="$(docker inspect -f '{{.State.Health.Status}}' "$(docker compose ps -q backend)" 2>/dev/null || true)"
    [ "$status" = "healthy" ] && break
    sleep 2
done
docker compose ps

echo "==> 6/6 Admin foydalanuvchi"
read -r -p "Admin login [admin]: " admin_user < /dev/tty
admin_user="${admin_user:-admin}"
docker compose exec backend python create_admin.py "$admin_user" < /dev/tty || true

# Har kuni 03:00 da zaxira
( crontab -l 2>/dev/null | grep -v 'deploy/backup.sh'; \
  echo "0 3 * * * cd $APP_DIR && ./deploy/backup.sh >> backups/backup.log 2>&1" ) | crontab -

domain="$(grep '^DOMAIN=' .env | cut -d= -f2)"
echo
echo "Tayyor!"
echo "  Sog'liq:     https://$domain/health"
echo "  Admin panel: https://$domain/static/admin/index.html"
echo "  Loglar:      cd $APP_DIR && docker compose logs -f bot"
