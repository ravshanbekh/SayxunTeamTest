# Contabo serverga Docker orqali o'rnatish

Tarkib (`docker-compose.yml`):

| Servis  | Vazifasi |
|---------|----------|
| `db`      | PostgreSQL 16, faqat ichki tarmoqda |
| `backend` | FastAPI: API, admin panel, talaba test sahifasi, Rasch hisobotlari |
| `bot`     | Telegram bot (polling) |
| `caddy`   | HTTPS (Let's Encrypt sertifikati avtomatik), 80/443 portlar |

Telegram Mini App (test sahifasi) faqat **HTTPS** orqali ochiladi, shuning uchun domen kerak.

---

## Tezkor o'rnatish (bitta buyruq)

Serverga `ssh root@SERVER_IP` bilan kiring va quyidagini ishga tushiring:

```bash
curl -fsSL https://raw.githubusercontent.com/ravshanbekh/SayxunTeamTest/main/deploy/install.sh | bash
```

Skript Docker, firewall, loyiha va `.env` ni (parollarni avtomatik yaratib) sozlaydi, konteynerlarni ishga
tushiradi, admin yaratadi va kunlik zaxirani yoqadi. Sizdan domen (bo'sh qoldirilsa `IP.sslip.io`),
`BOT_TOKEN` va admin paroli so'raladi. Quyidagi bo'limlar xuddi shu ishni qo'lda bajarish uchun.

---

## 1. Tayyorgarlik

- Contabo VPS: Ubuntu 22.04 yoki 24.04 (2 vCPU / 4 GB RAM yetarli).
- Domen yoki subdomen, masalan `test.example.uz`. DNS'da **A yozuvi** server IP manziliga qaratilgan bo'lsin.
  Domen bo'lmasa vaqtincha `IP-manzil.sslip.io` ishlatish mumkin (masalan `203-0-113-10.sslip.io`).
- @BotFather'dan bot tokeni.

## 2. Serverni sozlash (bir marta)

```bash
ssh root@SERVER_IP

apt update && apt upgrade -y
curl -fsSL https://get.docker.com | sh          # Docker + docker compose

# Faqat kerakli portlar
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 443/udp
ufw --force enable
```

## 3. Loyihani yuklash

```bash
git clone https://github.com/ravshanbekh/SayxunTeamTest.git /opt/SayxunTeamTest
cd /opt/SayxunTeamTest
```

Repozitoriy private bo'lsa, GitHub'da Personal Access Token yoki deploy key ishlating.

## 4. `.env` faylini to'ldirish

```bash
cp .env.example .env
openssl rand -hex 24   # -> POSTGRES_PASSWORD
openssl rand -hex 32   # -> SECRET_KEY
nano .env
```

Majburiy qiymatlar: `DOMAIN`, `BOT_TOKEN`, `POSTGRES_PASSWORD`, `SECRET_KEY`.
`.env` git'ga qo'shilmaydi. Uni hech kimga yubormang.

## 5. Ishga tushirish

```bash
docker compose up -d --build
docker compose ps          # hammasi "Up", backend "healthy" bo'lishi kerak
docker compose logs -f bot # bot loglari (Ctrl+C - chiqish)
```

Birinchi ishga tushishda Caddy sertifikat oladi (10-30 soniya).

## 6. Admin yaratish

```bash
docker compose exec backend python create_admin.py admin
# parol so'raladi (kamida 6 belgi)
```

## 7. Tekshirish

- `https://DOMAIN/health` → `{"status":"healthy"}`
- Admin panel: `https://DOMAIN/static/admin/index.html`
- Telegram'da botga `/start` → ro'yxatdan o'tish → test kodi → test sahifasi ochiladi.

---

## Railway'dan ko'chish

1. **Railway'dagi bot servisini to'xtating.** Bitta token bilan ikkita bot ishlasa, Telegram
   `TelegramConflictError` beradi va botlar bir-biriga xalaqit qiladi.
2. Eski ma'lumotlarni ko'chirish (Railway PostgreSQL → Contabo):
   ```bash
   cd /opt/SayxunTeamTest
   mkdir -p backups
   # RAILWAY_URL - Railway'dagi DATABASE_URL (postgresql://...); Railway Postgres versiyasiga mos tag tanlang
   docker run --rm postgres:16-alpine pg_dump "RAILWAY_URL" --no-owner --clean --if-exists | gzip > backups/railway.sql.gz
   docker compose up -d db
   ./deploy/restore.sh backups/railway.sql.gz
   docker compose up -d
   ```
3. Hammasi ishlagach, Railway servislarini o'chirishingiz mumkin.

---

## Kundalik ishlar

| Vazifa | Buyruq |
|--------|--------|
| Holat | `docker compose ps` |
| Loglar | `docker compose logs -f backend` / `bot` / `caddy` |
| Qayta ishga tushirish | `docker compose restart bot` |
| Yangilash (git pull + build) | `./deploy/update.sh` |
| Zaxira nusxa | `./deploy/backup.sh` → `backups/db_*.sql.gz` |
| Zaxiradan tiklash | `./deploy/restore.sh backups/db_....sql.gz` |
| To'xtatish | `docker compose down` (ma'lumotlar saqlanadi) |

`docker compose down -v` buyrug'ini **ishlatmang**: u bazani ham o'chiradi.

Har kuni avtomatik zaxira (14 kun saqlanadi):

```bash
crontab -e
# qo'shing:
0 3 * * * cd /opt/SayxunTeamTest && ./deploy/backup.sh >> backups/backup.log 2>&1
```

Zaxiralarni vaqti-vaqti bilan serverdan tashqariga ham ko'chirib turing (masalan `scp`).

## Sozlamalar

- `RASCH_MAX_SCORE=75`: Rasch ballini 75 bilan cheklash (bo'sh qoldirilsa cheklanmaydi).
- `SESSION_DURATION_MINUTES`: test vaqti belgilanmagan testlar uchun davomiylik (daqiqa).

`.env` o'zgartirilgandan keyin: `docker compose up -d`.

## Muammolar

- **HTTPS sertifikat olinmayapti:** DNS A yozuvi server IP'siga qaraganini (`ping DOMAIN`) va 80/443 portlar
  ochiqligini tekshiring. `docker compose logs caddy` ni ko'ring.
- **Bot javob bermayapti:** `docker compose logs bot`. `Conflict` xatosi bo'lsa, shu token bilan boshqa joyda
  (Railway, kompyuter) bot ishlab turibdi.
- **Test sahifasi ochilmayapti:** `.env` dagi `DOMAIN` haqiqiy domen bo'lishi va `https://DOMAIN/health` ishlashi kerak.
