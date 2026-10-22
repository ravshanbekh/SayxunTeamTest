"""
To'lov endpointlari (Telegram bot uchun): karta rekvizitlari, balans, chek yuborish.
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.payment_service import (
    MAX_RECEIPT_BYTES, PaymentError, get_balance, get_payment_settings, pending_amount, submit_payment,
)

router = APIRouter()


async def _user_by_telegram(db: AsyncSession, telegram_id: int) -> User:
    user = (await db.execute(select(User).where(User.telegram_id == telegram_id))).scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Foydalanuvchi topilmadi")
    return user


@router.get("/info")
async def payment_info(db: AsyncSession = Depends(get_db)):
    """To'lov uchun karta rekvizitlari."""
    return await get_payment_settings(db)


@router.get("/balance/{telegram_id}")
async def user_balance(telegram_id: int, db: AsyncSession = Depends(get_db)):
    user = await _user_by_telegram(db, telegram_id)
    return {
        "balance": await get_balance(db, user.id),
        "pending_amount": await pending_amount(db, user.id),
    }


@router.post("/submit", status_code=status.HTTP_201_CREATED)
async def submit_receipt(
    telegram_id: int = Form(...),
    amount: int = Form(...),
    test_id: Optional[UUID] = Form(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Talaba chekini (rasm yoki PDF) yuboradi - admin tasdiqlashini kutadi."""
    user = await _user_by_telegram(db, telegram_id)
    content = await file.read(MAX_RECEIPT_BYTES + 1)
    try:
        payment = await submit_payment(db, user, amount, content, test_id)
    except PaymentError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return {"id": str(payment.id), "status": payment.status, "amount": payment.amount}
