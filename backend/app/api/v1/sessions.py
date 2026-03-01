"""
Session endpoints - test session management.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.database import get_db
from app.schemas.session import SessionCreate, SessionResponse, SessionStatusResponse
from app.services.session_service import (
    create_session,
    get_session_by_token,
    check_user_attempted_test
)


router = APIRouter()


@router.post("/start", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def start_session(
    session_data: SessionCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Start a new test session for a user.
    Returns session token for accessing the test.
    """
    # Check if user already attempted
    attempted = await check_user_attempted_test(db, session_data.user_id, session_data.test_id)
    
    if attempted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has already attempted this test"
        )
    
    try:
        session = await create_session(db, session_data.user_id, session_data.test_id)
    except ValueError as e:
        error_msg = str(e)
        if error_msg == "TEST_NOT_STARTED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Test hali boshlanmadi"
            )
        elif error_msg == "TEST_ENDED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Test vaqti tugagan"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not create session"
        )
    
    return SessionResponse.model_validate(session)


@router.get("/{session_token}", response_model=SessionResponse)
async def get_session(
    session_token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get session by token.
    Used by frontend to validate session and get test info.
    """
    from sqlalchemy.orm import selectinload
    from sqlalchemy import select as sa_select
    from app.models.session import TestSession
    
    # Get session with test relationship loaded
    stmt = sa_select(TestSession).options(
        selectinload(TestSession.test)
    ).where(TestSession.session_token == session_token)
    
    result = await db.execute(stmt)
    session = result.scalars().first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Auto-expire if time has passed
    if not session.is_submitted and not session.is_expired:
        from app.utils.timer import now_uz
        if now_uz() >= session.expires_at:
            session.is_expired = True
            await db.commit()
            await db.refresh(session)
    
    # Build response with test title
    response_data = {
        "id": session.id,
        "user_id": session.user_id,
        "test_id": session.test_id,
        "session_token": session.session_token,
        "started_at": session.started_at,
        "expires_at": session.expires_at,
        "is_submitted": session.is_submitted,
        "is_expired": session.is_expired,
        "is_valid": session.is_valid,
        "time_remaining_seconds": session.time_remaining_seconds,
        "test_title": session.test.title if session.test else None,
        "test_type": (session.test.test_type or 'sertifikat') if session.test else 'sertifikat'
    }
    
    return SessionResponse(**response_data)


@router.get("/{session_token}/status", response_model=SessionStatusResponse)
async def get_session_status(
    session_token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Check session status - for timer validation.
    """
    session = await get_session_by_token(db, session_token)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    return SessionStatusResponse(
        is_valid=session.is_valid,
        time_remaining_seconds=session.time_remaining_seconds,
        is_submitted=session.is_submitted,
        is_expired=session.is_expired
    )
