"""
Session schemas for request/response validation.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID


class SessionCreate(BaseModel):
    """Schema for creating a test session."""
    user_id: UUID
    test_id: UUID


class SessionResponse(BaseModel):
    """Schema for session response."""
    id: UUID
    user_id: UUID
    test_id: UUID
    session_token: str
    started_at: datetime
    expires_at: datetime
    is_submitted: bool
    is_expired: bool
    is_valid: bool  # Computed property
    time_remaining_seconds: int
    test_title: str | None = None  # Test title for frontend
    test_type: str | None = None   # 'sertifikat' or 'prezident'
    
    class Config:
        from_attributes = True


class SessionStatusResponse(BaseModel):
    """Schema for session status check."""
    is_valid: bool
    time_remaining_seconds: int
    is_submitted: bool
    is_expired: bool
