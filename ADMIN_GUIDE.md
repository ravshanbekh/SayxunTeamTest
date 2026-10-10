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
