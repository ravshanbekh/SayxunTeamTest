"""
Test management service.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from uuid import UUID
import os

from app.models.test import Test, AnswerKey
from app.schemas.test import TestCreate, TestUpdate
from app.config import settings


async def create_test(
    db: AsyncSession,
    test_data: TestCreate,
    admin_id: UUID,
    pdf_filename: Optional[str] = None
) -> Test:
    """
    Create a new test with answer key.
    
    Args:
        db: Database session
        test_data: Test creation data
        admin_id: ID of admin creating the test
        pdf_filename: Name of uploaded PDF file
    
    Returns:
        Created Test instance
    """
    # Create test
    test = Test(
        test_code=test_data.test_code.upper(),
        title=test_data.title,
        description=test_data.description,
        pdf_file_path=pdf_filename,
        created_by_admin=admin_id,
        is_active=True,
        start_time=test_data.start_time,
        end_time=test_data.end_time,
        test_type=test_data.test_type
    )
    
    db.add(test)
    await db.flush()  # Get test ID before creating answer key
    
    # Create answer key
    answer_key = AnswerKey(
        test_id=test.id,
        mcq_answers=test_data.answer_key.mcq_answers,
        written_questions=test_data.answer_key.written_questions or {}
    )
    
    db.add(answer_key)
    await db.commit()
    await db.refresh(test)
    
    return test


async def get_test_by_code(db: AsyncSession, test_code: str) -> Optional[Test]:
    """
    Get test by test code.
    
    Args:
        db: Database session
        test_code: Test code
    
    Returns:
        Test if found, None otherwise
    """
    stmt = select(Test).where(Test.test_code == test_code.upper(), Test.is_active == True)
    result = await db.execute(stmt)
    return result.scalars().first()


async def get_test_by_id(db: AsyncSession, test_id: UUID) -> Optional[Test]:
    """
    Get test by ID.
    
    Args:
        db: Database session
        test_id: Test UUID
    
    Returns:
        Test if found, None otherwise
    """
    stmt = select(Test).where(Test.id == test_id)
    result = await db.execute(stmt)
    return result.scalars().first()


async def get_all_tests(db: AsyncSession, skip: int = 0, limit: int = 100, test_type: str | None = None) -> List[Test]:
    """
    Get all tests with pagination, optionally filtered by test_type.
    """
    stmt = select(Test)
    if test_type:
        stmt = stmt.where(Test.test_type == test_type)
    stmt = stmt.offset(skip).limit(limit).order_by(Test.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


async def update_test(db: AsyncSession, test_id: UUID, test_data: TestUpdate) -> Optional[Test]:
    """
    Update test information.
    
    Args:
        db: Database session
        test_id: Test UUID
        test_data: Update data
    
    Returns:
        Updated Test if found, None otherwise
    """
    test = await get_test_by_id(db, test_id)
    
    if not test:
        return None
    
    if test_data.title is not None:
        test.title = test_data.title
    if test_data.description is not None:
        test.description = test_data.description
    if test_data.is_active is not None:
        test.is_active = test_data.is_active
    
    await db.commit()
    await db.refresh(test)
    
    return test


async def get_answer_key(db: AsyncSession, test_id: UUID) -> Optional[AnswerKey]:
    """
    Get answer key for a test.
    
    Args:
        db: Database session
        test_id: Test UUID
    
    Returns:
        AnswerKey if found, None otherwise
    """
    stmt = select(AnswerKey).where(AnswerKey.test_id == test_id)
    result = await db.execute(stmt)
    return result.scalars().first()


async def delete_test(db: AsyncSession, test_id: UUID) -> bool:
    """
    Delete a test and all related records (cascade).
    
    Args:
        db: Database session
        test_id: Test UUID
    
    Returns:
        True if deleted, False if not found
    """
    test = await get_test_by_id(db, test_id)
    
    if not test:
        return False
    
    await db.delete(test)
    await db.commit()
    
    return True


async def update_test_with_answers(
    db: AsyncSession,
    test_id: UUID,
    test_data: TestUpdate
) -> Optional[Test]:
    """
    Update test information including answer key.
    """
    test = await get_test_by_id(db, test_id)
    
    if not test:
        return None
    
    if test_data.title is not None:
        test.title = test_data.title
    if test_data.description is not None:
        test.description = test_data.description
    if test_data.is_active is not None:
        test.is_active = test_data.is_active
    if test_data.test_code is not None:
        test.test_code = test_data.test_code.upper()
    if test_data.start_time is not None:
        test.start_time = test_data.start_time
    if test_data.end_time is not None:
        test.end_time = test_data.end_time
    
    # Update answer key if provided
    if test_data.answer_key is not None:
        answer_key = await get_answer_key(db, test_id)
        if answer_key:
            answer_key.mcq_answers = test_data.answer_key.mcq_answers
            if test_data.answer_key.written_questions is not None:
                answer_key.written_questions = test_data.answer_key.written_questions
    
    await db.commit()
    await db.refresh(test)
    
    return test
