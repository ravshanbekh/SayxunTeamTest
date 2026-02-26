"""
Result schemas for request/response validation.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import Dict, List


class MCQAnswerSubmit(BaseModel):
    """Schema for submitting MCQ answer."""
    question_number: int = Field(..., ge=1, le=35)
    answer: str | None = Field(None, pattern="^[ABCDEF]$")  # Q1-32: A-D, Q33-35: A-F


class WrittenAnswerSubmit(BaseModel):
    """Schema for submitting written answer with a/b sub-parts."""
    question_number: int = Field(..., ge=36, le=45)  # Q36-45
    answer: Dict[str, str] | None = None  # {'a': 'answer', 'b': 'answer'}


class ResultSubmit(BaseModel):
    """Schema for submitting complete test results."""
    session_token: str
    mcq_answers: List[MCQAnswerSubmit] = Field(..., min_length=35, max_length=35)
    written_answers: List[WrittenAnswerSubmit] = Field(..., min_length=10, max_length=10)  # Q36-45


class MCQAnswerResponse(BaseModel):
    """Schema for MCQ answer response."""
    question_number: int
    student_answer: str | None
    correct_answer: str
    is_correct: bool
    
    class Config:
        from_attributes = True


class WrittenAnswerResponse(BaseModel):
    """Schema for written answer response."""
    id: UUID
    question_number: int
    student_answer: str | None
    score: int
    score_a: int | None = None
    score_b: int | None = None
    reviewed_at: datetime | None
    
    class Config:
        from_attributes = True


class ResultResponse(BaseModel):
    """Schema for result response."""
    id: UUID
    user_id: UUID
    test_id: UUID
    mcq_score: int
    written_score: int
    total_score: int
    submitted_at: datetime
    mcq_answers: List[MCQAnswerResponse] = []
    written_answers: List[WrittenAnswerResponse] = []
    
    class Config:
        from_attributes = True


class WrittenAnswerGrade(BaseModel):
    """Schema for grading written answer."""
    written_answer_id: UUID
    score: int = Field(..., ge=0)
    comments: str | None = None


class UserResultSummary(BaseModel):
    """Schema for user's test result summary (for Telegram bot)."""
    test_title: str
    test_code: str = ""
    mcq_score: int
    mcq_total: int = 35
    written_score: int
    written_total: int = 10  # Q36-45 (each with a/b parts, total 20 sub-parts)
    total_score: int
    submitted_at: datetime
