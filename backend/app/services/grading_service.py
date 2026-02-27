"""
Grading service for automatic MCQ grading and result calculation.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID
from datetime import datetime
import json  # For converting dict to JSON string

from app.models.result import Result, MCQAnswer, WrittenAnswer, WrittenReview
from app.utils.timer import now_uz
from app.models.test import AnswerKey
from app.models.session import TestSession
from app.schemas.result import ResultSubmit, MCQAnswerSubmit, WrittenAnswerSubmit


async def grade_and_save_result(
    db: AsyncSession,
    session: TestSession,
    submission: ResultSubmit
) -> Result:
    """
    Grade MCQ answers automatically and save complete result.
    
    Args:
        db: Database session
        session: TestSession instance
        submission: Student's submitted answers
    
    Returns:
        Created Result instance
    """
    # Get answer key
    stmt = select(AnswerKey).where(AnswerKey.test_id == session.test_id)
    result = await db.execute(stmt)
    answer_key = result.scalars().first()
    
    if not answer_key:
        raise ValueError("Answer key not found for this test")
    
    # Create result
    result_record = Result(
        user_id=session.user_id,
        test_id=session.test_id,
        session_id=session.id,
        mcq_score=0,
        written_score=0,
        total_score=0,
        submitted_at=now_uz()
    )
    
    db.add(result_record)
    await db.flush()  # Get result ID
    
    # Grade MCQ answers
    mcq_correct_count = 0
    for mcq_answer in submission.mcq_answers:
        correct_answer = answer_key.mcq_answers.get(str(mcq_answer.question_number))
        is_correct = mcq_answer.answer == correct_answer if mcq_answer.answer else False
        
        if is_correct:
            mcq_correct_count += 1
        
        mcq_record = MCQAnswer(
            result_id=result_record.id,
            question_number=mcq_answer.question_number,
            student_answer=mcq_answer.answer,
            correct_answer=correct_answer,
            is_correct=is_correct
        )
        db.add(mcq_record)
    
    # Grade written answers (auto-grade by comparing with answer key)
    written_correct_count = 0
    written_answers_data = answer_key.written_questions or {}
    
    for written_answer in submission.written_answers:
        # Student answer comes as dict like {"a": "12", "b": "12"}
        student_ans = written_answer.answer or {}
        
        # Correct answer from answer key like {"a": "correct_a", "b": "correct_b"}
        correct_ans = written_answers_data.get(str(written_answer.question_number), {})
        
        # Compare each sub-part (a, b) using shared comparison utility
        from app.utils.answer_compare import normalize, answers_match
        
        score = 0
        student_a = normalize(student_ans.get('a', ''))
        student_b = normalize(student_ans.get('b', ''))
        correct_a = normalize(correct_ans.get('a', ''))
        correct_b = normalize(correct_ans.get('b', ''))
        
        if answers_match(student_a, correct_a):
            score += 1
            written_correct_count += 1
        if answers_match(student_b, correct_b):
            score += 1
            written_correct_count += 1
        
        # Convert dict answer to JSON string for storage
        answer_str = json.dumps(written_answer.answer) if written_answer.answer else None
        
        written_record = WrittenAnswer(
            result_id=result_record.id,
            question_number=written_answer.question_number,
            student_answer=answer_str,  # Store as JSON string
            score=score,
            reviewed_at=now_uz()  # Auto-reviewed
        )
        db.add(written_record)
    
    # Update scores (MCQ + written)
    result_record.mcq_score = mcq_correct_count
    result_record.written_score = written_correct_count
    result_record.total_score = mcq_correct_count + written_correct_count
    
    await db.commit()
    await db.refresh(result_record)
    
    return result_record


async def grade_written_answer(
    db: AsyncSession,
    written_answer_id: UUID,
    admin_id: UUID,
    score: int,
    comments: Optional[str] = None
) -> Optional[WrittenAnswer]:
    """
    Grade a written answer manually.
    
    Args:
        db: Database session
        written_answer_id: WrittenAnswer UUID
        admin_id: Admin grading the answer
        score: Score to award
        comments: Optional comments
    
    Returns:
        Updated WrittenAnswer if found, None otherwise
    """
    stmt = select(WrittenAnswer).where(WrittenAnswer.id == written_answer_id)
    result = await db.execute(stmt)
    written_answer = result.scalars().first()
    
    if not written_answer:
        return None
    
    # Update written answer
    written_answer.score = score
    written_answer.reviewed_at = now_uz()
    
    # Create review record
    review = WrittenReview(
        written_answer_id=written_answer_id,
        reviewed_by_admin=admin_id,
        score_awarded=score,
        comments=comments,
        reviewed_at=datetime.utcnow()
    )
    db.add(review)
    
    # Update total score in result
    stmt = select(Result).where(Result.id == written_answer.result_id)
    result = await db.execute(stmt)
    result_record = result.scalars().first()
    
    if result_record:
        # Recalculate written score
        stmt = select(WrittenAnswer).where(WrittenAnswer.result_id == result_record.id)
        result = await db.execute(stmt)
        all_written = result.scalars().all()
        
        result_record.written_score = sum(ans.score for ans in all_written)
        result_record.total_score = result_record.mcq_score + result_record.written_score
    
    await db.commit()
    await db.refresh(written_answer)
    
    return written_answer


async def get_result_by_id(db: AsyncSession, result_id: UUID) -> Optional[Result]:
    """Get result by ID."""
    stmt = select(Result).where(Result.id == result_id)
    result = await db.execute(stmt)
    return result.scalars().first()


async def get_user_results(db: AsyncSession, user_id: UUID) -> List[Result]:
    """Get all results for a user."""
    stmt = select(Result).where(Result.user_id == user_id).order_by(Result.submitted_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_ungraded_written_answers(db: AsyncSession, test_id: Optional[UUID] = None) -> List[WrittenAnswer]:
    """
    Get all ungraded written answers, optionally filtered by test.
    
    Args:
        db: Database session
        test_id: Optional test ID to filter by
    
    Returns:
        List of WrittenAnswer instances
    """
    stmt = select(WrittenAnswer).where(WrittenAnswer.reviewed_at == None)
    
    if test_id:
        stmt = stmt.join(Result).where(Result.test_id == test_id)
    
    result = await db.execute(stmt)
    return result.scalars().all()
