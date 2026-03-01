"""
Test and AnswerKey models.
"""
from sqlalchemy import Column, String, Text, Boolean, DateTime, JSON, ForeignKey, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base
from app.models.types import UUID


class Test(Base):
    """Test model - represents an exam with questions."""
    
    __tablename__ = "tests"
    
    id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    test_code = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    pdf_file_path = Column(String(500))
    created_by_admin = Column(UUID(), ForeignKey("admin_users.id"))
    is_active = Column(Boolean, default=True, nullable=False)
    start_time = Column(DateTime, nullable=True)   # Test boshlanish vaqti
    end_time = Column(DateTime, nullable=True)       # Test tugash vaqti
    extra_minutes = Column(Integer, default=0, nullable=False)  # Admin qo'shgan daqiqalar (max 15)
    test_type = Column(String(20), default='sertifikat', nullable=False)  # 'sertifikat' or 'prezident'
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    creator = relationship("AdminUser", back_populates="tests_created")
    answer_key = relationship("AnswerKey", back_populates="test", uselist=False, cascade="all, delete-orphan")
    sessions = relationship("TestSession", back_populates="test", cascade="all, delete-orphan")
    results = relationship("Result", back_populates="test", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Test {self.test_code}: {self.title}>"


class AnswerKey(Base):
    """Answer key model - stores correct answers for a test."""
    
    __tablename__ = "answer_keys"
    
    id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    test_id = Column(UUID(), ForeignKey("tests.id", ondelete="CASCADE"), unique=True, nullable=False)
    mcq_answers = Column(JSON, nullable=False)  # {"1": "A", "2": "B", ..., "35": "D"}
    written_questions = Column(JSON)  # {"36": "Question text", ..., "45": "Question text"}
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    test = relationship("Test", back_populates="answer_key")
    
    def __repr__(self):
        return f"<AnswerKey for Test {self.test_id}>"
