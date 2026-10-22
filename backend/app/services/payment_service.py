"""
To'lov va balans logikasi.

Oqim:
  1. Pullik testga kirishda balans yetmasa, bot talabaga karta rekvizitlarini ko'rsatadi.
  2. Talaba pul o'tkazib, chek rasmini yoki PDF'ini botga yuboradi -> PaymentRequest (pending).
  3. Admin saytda cheklarni ko'radi va tasdiqlaydi (bittalab, belgilab yoki hammasini).
     Tasdiqlanganda balans to'ldiriladi va talabaga bot orqali xabar boradi.
  4. Testga kirishda narx balansdan bir marta yechiladi (qayta kirishda yechilmaydi).
  5. Chek fayllari: testga bog'langan bo'lsa test tugagach, aks holda ko'rib chiqilgandan
     RECEIPT_RETENTION_DAYS kun o'tgach diskdan o'chiriladi (yozuv saqlanib qoladi).
"""
from datetime import timedelta
from typing import Dict, List, Optional, Tuple
from uuid import UUID, uuid4
import json
import logging
import os
import urllib.request

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.payment import PaymentRequest, BalanceTransaction, AppSetting
from app.models.test import Test
from app.models.user import User
from app.utils.timer import now_uz

logger = logging.getLogger(__name__)

MAX_RECEIPT_BYTES = 10 * 1024 * 1024
MIN_AMOUNT = 1_000
MAX_AMOUNT = 50_000_000
MAX_PENDING_PER_USER = 5

PAYMENT_SETTING_KEYS = ("card_number", "card_holder", "note")

# Fayl turi faylning boshidagi baytlardan aniqlanadi (kengaytmaga ishonilmaydi)
_SIGNATURES = [
    (b"\xff\xd8\xff", "image/jpeg", ".jpg"),
    (b"\x89PNG\r\n\x1a\n", "image/png", ".png"),
    (b"%PDF", "application/pdf", ".pdf"),
]


class PaymentError(Exception):
    pass


def detect_receipt_type(content: bytes) -> Optional[Tuple[str, str]]:
    for signature, mime, ext in _SIGNATURES:
        if content.startswith(signature):
            return mime, ext
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp", ".webp"
    return None


def receipts_dir() -> str:
    path = os.path.join(settings.UPLOAD_DIR, "receipts")
    os.makedirs(path, exist_ok=True)
    return path


# ---------------------------------------------------------------------------
# Balans
# ---------------------------------------------------------------------------
async def get_balance(db: AsyncSession, user_id: UUID) -> int:
    stmt = select(func.coalesce(func.sum(BalanceTransaction.amount), 0)).where(BalanceTransaction.user_id == user_id)
    return int((await db.execute(stmt)).scalar_one())


async def has_paid_for_test(db: AsyncSession, user_id: UUID, test_id: UUID) -> bool:
    stmt = select(BalanceTransaction.id).where(
        BalanceTransaction.user_id == user_id,
        BalanceTransaction.test_id == test_id,
        BalanceTransaction.kind == "test_fee",
    )
    return (await db.execute(stmt)).first() is not None


async def check_test_access(db: AsyncSession, user_id: UUID, test: Test) -> Optional[Dict]:
    """
    Pullik testga kirish huquqini tekshirish (yozmaydi).
    None - kirish mumkin; aks holda yetishmovchilik haqida ma'lumot.
    """
    price = int(test.price or 0)
    if price <= 0 or await has_paid_for_test(db, user_id, test.id):
        return None
    balance = await get_balance(db, user_id)
    if balance >= price:
        return None
    pending = await pending_amount(db, user_id, test.id)
    return {
        "code": "INSUFFICIENT_BALANCE",
        "price": price,
        "balance": balance,
        "required": price - balance,
        "pending_amount": pending,
        "test_id": str(test.id),
    }


async def charge_for_test(db: AsyncSession, user_id: UUID, test: Test) -> int:
    """Test narxini balansdan bir marta yechish. Yechilgan summa (0 - yechilmadi)."""
    price = int(test.price or 0)
    if price <= 0 or await has_paid_for_test(db, user_id, test.id):
        return 0
    db.add(BalanceTransaction(user_id=user_id, amount=-price, kind="test_fee", test_id=test.id,
                              created_at=now_uz()))
    await db.commit()
    return price


async def pending_amount(db: AsyncSession, user_id: UUID, test_id: Optional[UUID] = None) -> int:
    stmt = select(func.coalesce(func.sum(PaymentRequest.amount), 0)).where(
        PaymentRequest.user_id == user_id, PaymentRequest.status == "pending")
    if test_id is not None:
        stmt = stmt.where(PaymentRequest.test_id == test_id)
    return int((await db.execute(stmt)).scalar_one())


# ---------------------------------------------------------------------------
# Chek yuborish (bot)
# ---------------------------------------------------------------------------
async def submit_payment(db: AsyncSession, user: User, amount: int, content: bytes,
                         test_id: Optional[UUID] = None) -> PaymentRequest:
    if not (MIN_AMOUNT <= amount <= MAX_AMOUNT):
        raise PaymentError(f"Summa {MIN_AMOUNT:,} dan {MAX_AMOUNT:,} so'mgacha bo'lishi kerak".replace(",", " "))
    if not content:
        raise PaymentError("Chek fayli bo'sh")
    if len(content) > MAX_RECEIPT_BYTES:
        raise PaymentError("Chek fayli juda katta (maksimal 10 MB)")
    detected = detect_receipt_type(content)
    if not detected:
        raise PaymentError("Chek rasm (JPG, PNG, WEBP) yoki PDF bo'lishi kerak")

    stmt = select(func.count(PaymentRequest.id)).where(
        PaymentRequest.user_id == user.id, PaymentRequest.status == "pending")
    if (await db.execute(stmt)).scalar_one() >= MAX_PENDING_PER_USER:
        raise PaymentError("Sizda tekshirilmagan cheklar ko'p. Admin ko'rib chiqishini kuting")

    if test_id is not None:
        test = (await db.execute(select(Test).where(Test.id == test_id))).scalars().first()
        if not test:
            test_id = None

    mime, ext = detected
    payment_id = uuid4()
    path = os.path.join(receipts_dir(), f"{payment_id}{ext}")
    with open(path, "wb") as f:
        f.write(content)

    payment = PaymentRequest(id=payment_id, user_id=user.id, test_id=test_id, amount=amount, status="pending",
                             file_path=path, content_type=mime, created_at=now_uz())
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return payment


# ---------------------------------------------------------------------------
# Admin: ko'rib chiqish
# ---------------------------------------------------------------------------
async def approve_payments(db: AsyncSession, ids: List[UUID], admin_id: UUID,
                           amounts: Optional[Dict[str, int]] = None) -> List[PaymentRequest]:
    """Tanlangan (pending) to'lovlarni tasdiqlash va balansga qo'shish."""
    if not ids:
        return []
    amounts = amounts or {}
    stmt = select(PaymentRequest).where(PaymentRequest.id.in_(ids), PaymentRequest.status == "pending")
    payments = list((await db.execute(stmt)).scalars().all())
    now = now_uz()
    for payment in payments:
        override = amounts.get(str(payment.id))
        if override is not None:
            if not (MIN_AMOUNT <= int(override) <= MAX_AMOUNT):
                raise PaymentError(f"Noto'g'ri summa: {override}")
            payment.amount = int(override)
        payment.status = "approved"
        payment.reviewed_at = now
        payment.reviewed_by = admin_id
        db.add(BalanceTransaction(user_id=payment.user_id, amount=payment.amount, kind="topup",
                                  payment_id=payment.id, test_id=payment.test_id, created_at=now))
    await db.commit()
    return payments


async def approve_all_pending(db: AsyncSession, admin_id: UUID) -> List[PaymentRequest]:
    stmt = select(PaymentRequest.id).where(PaymentRequest.status == "pending")
    ids = [row[0] for row in (await db.execute(stmt)).all()]
    return await approve_payments(db, ids, admin_id)


async def reject_payment(db: AsyncSession, payment_id: UUID, admin_id: UUID, note: Optional[str]) -> Optional[PaymentRequest]:
    payment = (await db.execute(select(PaymentRequest).where(PaymentRequest.id == payment_id))).scalars().first()
    if not payment or payment.status != "pending":
        return None
    payment.status = "rejected"
    payment.note = (note or "").strip()[:500] or None
    payment.reviewed_at = now_uz()
    payment.reviewed_by = admin_id
    await db.commit()
    return payment


# ---------------------------------------------------------------------------
# Cheklarni o'chirish
# ---------------------------------------------------------------------------
def receipt_expires_at(payment: PaymentRequest, test: Optional[Test]):
    """Chek fayli qachongacha saqlanadi (tekshirilmagan cheklar o'chirilmaydi)."""
    if payment.status == "pending" or not payment.reviewed_at:
        return None
    if test is not None and test.end_time:
        return test.end_time + timedelta(minutes=test.extra_minutes or 0)
    return payment.reviewed_at + timedelta(days=settings.RECEIPT_RETENTION_DAYS)


async def purge_expired_receipts(db: AsyncSession) -> int:
    stmt = (select(PaymentRequest, Test)
            .outerjoin(Test, Test.id == PaymentRequest.test_id)
            .where(PaymentRequest.file_path.is_not(None), PaymentRequest.status != "pending"))
    now = now_uz()
    removed = 0
    for payment, test in (await db.execute(stmt)).all():
        expires = receipt_expires_at(payment, test)
        if expires is None or now < expires:
            continue
        try:
            if payment.file_path and os.path.exists(payment.file_path):
                os.remove(payment.file_path)
        except OSError as e:
            logger.warning(f"[PAYMENTS] Chekni o'chirib bo'lmadi {payment.file_path}: {e}")
            continue
        payment.file_path = None
        payment.file_deleted_at = now
        removed += 1
    if removed:
        await db.commit()
        logger.info(f"[PAYMENTS] {removed} ta eski chek o'chirildi")
    return removed


# ---------------------------------------------------------------------------
# Sozlamalar (karta rekvizitlari)
# ---------------------------------------------------------------------------
async def get_payment_settings(db: AsyncSession) -> Dict[str, str]:
    keys = [f"payment.{k}" for k in PAYMENT_SETTING_KEYS]
    rows = (await db.execute(select(AppSetting).where(AppSetting.key.in_(keys)))).scalars().all()
    values = {row.key.split(".", 1)[1]: row.value or "" for row in rows}
    return {k: values.get(k, "") for k in PAYMENT_SETTING_KEYS}


async def save_payment_settings(db: AsyncSession, data: Dict[str, str]) -> Dict[str, str]:
    for k in PAYMENT_SETTING_KEYS:
        if k not in data or data[k] is None:
            continue
        key = f"payment.{k}"
        row = (await db.execute(select(AppSetting).where(AppSetting.key == key))).scalars().first()
        value = str(data[k]).strip()[:500]
        if row:
            row.value = value
        else:
            db.add(AppSetting(key=key, value=value))
    await db.commit()
    return await get_payment_settings(db)


# ---------------------------------------------------------------------------
# Talabaga bot orqali xabar
# ---------------------------------------------------------------------------
def format_sum(value: int) -> str:
    return f"{int(value):,}".replace(",", " ") + " so'm"


def send_telegram_message(chat_id: int, text: str) -> bool:
    """Bot API orqali xabar (sinxron; run_in_threadpool bilan chaqiriladi)."""
    token = settings.BOT_TOKEN
    if not token:
        return False
    data = json.dumps({"chat_id": chat_id, "text": text, "parse_mode": "HTML"}).encode()
    request = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data,
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status == 200
    except Exception as e:  # tarmoq xatosi admin amalini to'xtatmasligi kerak
        logger.warning(f"[PAYMENTS] Telegram xabari yuborilmadi ({chat_id}): {e}")
        return False


async def build_review_notifications(db: AsyncSession, payments: List[PaymentRequest]) -> List[Tuple[int, str]]:
    """Tasdiqlangan/rad etilgan to'lovlar uchun (telegram_id, matn) ro'yxati."""
    messages = []
    for payment in payments:
        user = (await db.execute(select(User).where(User.id == payment.user_id))).scalars().first()
        if not user:
            continue
        test = None
        if payment.test_id:
            test = (await db.execute(select(Test).where(Test.id == payment.test_id))).scalars().first()
        if payment.status == "approved":
            balance = await get_balance(db, user.id)
            text = (f"✅ <b>To'lovingiz tasdiqlandi!</b>\n\n"
                    f"➕ {format_sum(payment.amount)} balansga qo'shildi.\n"
                    f"💰 Balans: <b>{format_sum(balance)}</b>")
            if test:
                text += f"\n\n📝 Endi <b>{test.test_code}</b> test kodini botga qayta yuboring."
        else:
            text = (f"❌ <b>To'lovingiz tasdiqlanmadi.</b>\n\n"
                    f"Summa: {format_sum(payment.amount)}")
            if payment.note:
                text += f"\nSabab: {payment.note}"
            text += "\n\nSavollar bo'lsa, o'quv markazi administratoriga murojaat qiling."
        messages.append((user.telegram_id, text))
    return messages
