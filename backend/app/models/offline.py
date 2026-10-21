"""
Offline (qog'ozda) topshirilgan imtihon natijalari - o'qituvchi Excel orqali
0/1 ko'rinishida yuklaydi va ular Rasch hisobiga onlayn natijalar bilan birga kiradi.
"""
from sqlalchemy import Column, String, DateTime, JSON, ForeignKey
from datetime import datetime
import uuid

from app.database import Base
from app.models.types import UUID


class OfflineResult(Base):
    """Bitta offline talabaning natijasi."""

    __tablename__ = "offline_results"

    id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    test_id = Column(UUID(), ForeignKey("tests.id", ondelete="CASCADE"), nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    region = Column(String(255))
    answers = Column(JSON, nullable=False)  # [1, 0, 1, ...] - topshiriqlar tartibida
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<OfflineResult {self.full_name} (Test: {self.test_id})>"
