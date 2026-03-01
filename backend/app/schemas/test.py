"""
Test schemas for request/response validation.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import Dict, Optional


class AnswerKeyCreate(BaseModel):
    """Schema for creating answer key."""
    mcq_answers: Dict[str, str] = Field(..., description="MCQ answers (1-35): {'1': 'A', '2': 'B', ...}")
    written_questions: Dict[str, Dict[str, str]] | None = Field(None, description="Written questions (36-37) with a/b parts: {'36': {'a': 'answer', 'b': 'answer'}}")


class TestCreate(BaseModel):
    """Schema for creating a new test."""
    test_code: str = Field(..., min_length=1, max_length=50)
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    start_time: Optional[datetime] = None   # Test boshlanish vaqti
    end_time: Optional[datetime] = None     # Test tugash vaqti
    test_type: str = Field(default='sertifikat', description="'sertifikat' or 'prezident'")
    answer_key: AnswerKeyCreate


class TestResponse(BaseModel):
    """Schema for test response."""
    id: UUID
    test_code: str
    title: str
    description: str | None
    pdf_file_path: str | None
    is_active: bool
    start_time: datetime | None = None
    end_time: datetime | None = None
    extra_minutes: int = 0
    test_type: str = 'sertifikat'
    created_at: datetime
    
    class Config:
        from_attributes = True


class TestWithAnswerKey(TestResponse):
    """Schema for test with answer key (admin only)."""
    answer_key: Dict | None = None


class TestUpdate(BaseModel):
    """Schema for updating test."""
    test_code: str | None = None
    title: str | None = None
    description: str | None = None
    is_active: bool | None = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    test_type: str | None = None
    answer_key: AnswerKeyCreate | None = None
