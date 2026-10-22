"""
To'lov tizimi: talaba plastik kartaga pul o'tkazib, chekini botga yuboradi,
admin saytda tasdiqlaydi, balans to'ldiriladi va pullik testga kirishda yechiladi.
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from datetime import datetime
import uuid

from app.database import Base
from app.models.types import UUID


class PaymentRequest(Base):
    """Talabaning chek (skrinshot yoki PDF) bilan yuborgan to'lov so'rovi."""

    __tablename__ = "payment_requests"

    id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    test_id = Column(UUID(), ForeignKey("tests.id", ondelete="SET NULL"), nullable=True, index=True)
    amount = Column(Integer, nullable=False)                 # so'm
    status = Column(String(20), nullable=False, default="pending", index=True)  # pending/approved/rejected
    file_path = Column(String(500))                          # chek fayli (muddati o'tgach o'chiriladi)
    content_type = Column(String(100))
    note = Column(Text)                                      # rad etish sababi
    created_at = Column(DateTime, nullable=False)
    reviewed_at = Column(DateTime)
    reviewed_by = Column(UUID(), ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True)
    file_deleted_at = Column(DateTime)


class BalanceTransaction(Base):
    """Balans harakatlari: + to'ldirish, - test uchun to'lov."""

    __tablename__ = "balance_transactions"

    id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Integer, nullable=False)                 # musbat - kirim, manfiy - chiqim
    kind = Column(String(20), nullable=False)                # topup / test_fee
    payment_id = Column(UUID(), ForeignKey("payment_requests.id", ondelete="SET NULL"), nullable=True)
    test_id = Column(UUID(), ForeignKey("tests.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AppSetting(Base):
    """Oddiy kalit-qiymat sozlamalar (masalan, to'lov kartasi rekvizitlari)."""

    __tablename__ = "app_settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text)
