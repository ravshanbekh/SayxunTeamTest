# ADMIN YARATISH VA KIRISH
# ========================

## Usul 1: API orqali (Eng oson)

1. Browser da oching: http://localhost:8000/docs

2. `/api/v1/auth/register` endpoint ni toping

3. "Try it out" tugmasini bosing

4. Request body ga quyidagini kiriting:
```json
{
  "username": "admin",
  "password": "admin123",
  "role": "admin"
}
```

5. "Execute" bosing

## Usul 2: Database ga to'g'ridan-to'g'ri qo'shish

PowerShell da:

```powershell
cd "C:\Users\ANUBIS PC\Desktop\Rash\backend"
python -c "import asyncio, uuid; from datetime import datetime; from app.database import AsyncSessionLocal; from app.models.admin import AdminUser; from passlib.context import CryptContext; pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto'); exec('async def create():\n async with AsyncSessionLocal() as db:\n  admin = AdminUser(id=uuid.uuid4(), username=\"admin\", password_hash=pwd_context.hash(\"admin123\"), created_at=datetime.utcnow())\n  db.add(admin)\n  await db.commit()\n  print(\"Admin created!\")\nasyncio.run(create())')"
```

## ADMIN PANEL ga Kirish

URL: http://localhost:8000/static/admin/

**Login:**
- Username: `admin`
- Password: `admin123`

## Test Yaratish

Admin panelda:

1. **"Tests" menyusini bosing**
2. **"Create New Test" tugmasini bosing**
3. Ma'lumotlarni kiriting:
   - Test Code: `MATH001` (o'quvchilar bu kodni botga kiritadi)
   - Title: "Matematika Test 1"
   - Description: "Test tavsifi"

4. **MCQ Javoblarini kiriting** (1-35 gacha):
   ```
   1: A
   2: B
   3: C
   ...
   35: D
   ```

5. **"Save Test" bosing**

## O'quvchi Test Ishlaydi

Telegram botda:
1. `/start`
2. "✅ Testni boshlash" tugmasini bosing
3. Test kodini yuboring: `MATH001`
4. Test sahifasi ochiladi - 60 daqiqa timer bilan!

## Natijalarni Ko'rish

Admin panelda:
1. "Results" sahifasiga o'ting
2. Barcha natijalar ko'rinadi
3. Yozma javoblarni qo'lda baholang
4. Excel yoki PDF export qiling

## Rasch natijalari (milliy sertifikat uslubida)

Sertifikat testi kartasida ikkita tugma bor:
- **🏅 Rasch natija (PDF)**: rangli jadval (№, Ism familiya, To'g'ri, Rash, Foiz, Daraja, 1-Fan, 2-Fan)
- **🏅 Rasch natija (Excel)**: shu jadval, savollar tahlili (qiyinlik, logit) va 0/1 javoblar matritsasi

Hisoblash tartibi (BMBA metodikasi):
1. 55 ta topshiriq (1–35 test, 36a–45b yozma qismlar) 0/1 ko'rinishida olinadi.
2. Topshiriq qiyinliklari Rasch modeli bo'yicha CML usulida, talabgor qobiliyati (θ) esa WLE usulida baholanadi.
3. Standartlashtirish: `Z = (θ − o'rtacha) / standart og'ish`, `T = 50 + 10·Z`. 75 shartli maksimal: rasmiy hujjatda A+ "70 – 75 va undan yuqori", shuning uchun ball 75 da kesilmaydi (masalan, matematikada 90.14 ballik sertifikatlar bor). Cheklash kerak bo'lsa `RASCH_MAX_SCORE=75` muhit o'zgaruvchisini qo'ying.
4. Darajalar: A+ ≥ 70, A ≥ 65, B+ ≥ 60, B ≥ 55, C+ ≥ 50, C ≥ 46 (46 dan past bo'lsa sertifikat berilmaydi).
5. Foiz: A+ va A uchun 100%, qolganlari uchun `ball / 65`.
6. `1-Fan = foiz × 93 + 11`, `2-Fan = foiz × 63 + 11` (majburiy fan uchun 11 ball to'liq beriladi).

Eslatmalar:
- Ball barcha ishtirokchilarga nisbatan hisoblanadi, shuning uchun natija test tugagandan keyin yakuniy bo'ladi.
  Botda talaba Rasch natijasini test tugash vaqti (`end_time` + qo'shimcha daqiqalar) o'tgandan keyin ko'radi.
- Bitta variantda bir xil sondagi to'g'ri javob bir xil Rasch ball beradi, chunki Rasch modelida xom ball yetarli statistika hisoblanadi.
- Ishtirokchilar 30 tadan kam bo'lsa, hisobotda ogohlantirish chiqadi.

Testlarni ishga tushirish:
```bash
cd backend
pip install -r requirements-dev.txt
pytest -q
```

## Offline (qog'ozda) o'tkazilgan imtihon natijalari

Imtihonni bir qism talabalar qog'ozda topshirgan bo'lsa, ularning natijalari onlayn natijalarga qo'shiladi
va **umumiy Rasch hisobiga** kiradi.

1. Sertifikat testi kartasida **📥 Offline shablon** tugmasini bosing. Excel shablon yuklab olinadi.
2. `Natijalar` varag'ini to'ldiring: har bir qatorga bitta talaba, `Ism familiya` (majburiy), `Viloyat` (ixtiyoriy),
   har bir savol ustuniga `1` (to'g'ri) yoki `0` (xato). Bo'sh katak `0` deb hisoblanadi.
   Sertifikat testida ustunlar: `1`–`35` va yozma savollar uchun `36a`, `36b`, … `45b`.
3. **📤 Offline natija yuklash** tugmasi bilan faylni yuklang. Faylda xato bo'lsa (masalan `2` yoki `A`),
   qaysi qator va qaysi savolda ekani ko'rsatiladi va hech narsa saqlanmaydi.
4. Qayta yuklansa, shu testning oldingi offline natijalari yangisi bilan **almashtiriladi**.
5. **📋 Offline natijalar** tugmasi yuklanganlar ro'yxatini ko'rsatadi; u yerdan ularni o'chirish ham mumkin.

Rasch hisobotida (PDF/Excel) onlayn va offline talabalar bitta jadvalda chiqadi. PDF sarlavhasida ularning soni
alohida ko'rsatiladi, Excel'dagi `Manba` ustunida esa har bir talaba onlayn yoki offline ekani yoziladi.
Botda onlayn talabaning o'rni ham offline talabalar bilan birga hisoblanadi.

## Pullik testlar va to'lovlar

**Test narxi.** Test yaratish/tahrirlash oynasida "Pullik test" belgilansa va narx kiritilsa, talaba testga
kirishi uchun balansida shu summa bo'lishi kerak. Belgi olib tashlansa test bepul bo'ladi va bot balans haqida
umuman so'ramaydi. Eski testlar avtomatik bepul.

**Karta rekvizitlari.** "To'lovlar" sahifasidagi "To'lov kartasi rekvizitlari" bo'limiga karta raqami, karta
egasi va (ixtiyoriy) izoh kiriting. Bot talabalarga aynan shu ma'lumotni ko'rsatadi.

**Talaba tomoni (bot):**
1. Talaba test kodini yuboradi. Test pullik va balans yetmasa, bot narx, balans, karta raqami va
   to'lanadigan summani ko'rsatadi.
2. Talaba pul o'tkazib, chek skrinshotini (rasm) yoki PDF chekni botga yuboradi.
3. Admin tasdiqlagach, talabaga "To'lovingiz tasdiqlandi" xabari keladi; u test kodini qayta yuboradi va
   testga kiradi. Narx balansdan bir marta yechiladi (sessiya tozalanib qayta kirilsa qayta yechilmaydi).
4. Bosh menyudagi "💳 Balans" tugmasi orqali balansni ko'rish va oldindan to'ldirish ham mumkin.

**Admin tomoni (sayt, "To'lovlar" sahifasi):**
- "Kutilmoqda" ro'yxatida har bir chek: rasm yoki PDF, talaba, test, summa. Chekni bosib kattalashtirib ko'rish mumkin.
- Summani tasdiqlashdan oldin o'zgartirish mumkin (masalan, talaba kamroq o'tkazgan bo'lsa).
- Tasdiqlash: bittalab ("Tasdiqlash"), belgilanganlarni ("Belgilanganlarni tasdiqlash") yoki hammasini bittada
  ("Hammasini tasdiqlash"). "Rad etish"da sababni yozsangiz, u talabaga yuboriladi.
- Yon menyudagi "To'lovlar" yonida tekshirilmagan cheklar soni ko'rinadi.

**Cheklar qancha saqlanadi:** testga bog'langan chek o'sha test tugaguncha saqlanadi, test tugagach saytdan
avtomatik o'chiriladi (to'lov yozuvi va summa qoladi). Testga bog'lanmagan (balansni to'ldirish) cheklar ko'rib
chiqilgandan 7 kun keyin o'chiriladi (`RECEIPT_RETENTION_DAYS`). Tekshirilmagan cheklar o'chirilmaydi.

Talabaga tasdiq/rad xabari borishi uchun serverdagi `.env` faylida `BOT_TOKEN` bo'lishi yetarli (backend ham undan foydalanadi).
