"""
Results endpoints - submitting and retrieving test results.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import List
import json
import re

from app.database import get_db
from app.schemas.result import ResultSubmit, ResultResponse, UserResultSummary, MCQAnswerResponse, WrittenAnswerResponse
from app.services.session_service import get_session_by_token, mark_session_submitted
from app.services.grading_service import grade_and_save_result, get_user_results
from app.models.result import Result, MCQAnswer, WrittenAnswer
from app.models.test import Test, AnswerKey


def _normalize(s):
    """Normalize answer string for comparison."""
    if not s:
        return ''
    s = str(s).strip().lower()
    s = re.sub(r'\s+', ' ', s)
    s = s.replace('\\left(', '(').replace('\\right)', ')')
    s = s.replace('\\left[', '[').replace('\\right]', ']')
    s = s.replace('\\cdot', '*').replace('\\times', '*')
    return s


async def _build_written_responses(db, written_answers_list, test_id):
    """Build WrittenAnswerResponse list with per-sub-part scores (score_a, score_b)."""
    # Load answer key
    stmt = select(AnswerKey).where(AnswerKey.test_id == test_id)
    ak_result = await db.execute(stmt)
    answer_key = ak_result.scalars().first()
    written_key = (answer_key.written_questions or {}) if answer_key else {}
    
    responses = []
    for a in written_answers_list:
        correct_ans = written_key.get(str(a.question_number), {})
        
        # Parse student answer JSON
        student = {}
        if a.student_answer:
            try:
                student = json.loads(a.student_answer)
            except (ValueError, TypeError):
                student = {}
        
        # Compare sub-parts
        s_a = _normalize(student.get('a', ''))
        c_a = _normalize(correct_ans.get('a', ''))
        sa_correct = 1 if (s_a and c_a and (s_a == c_a or c_a in s_a)) else 0
        
        s_b = _normalize(student.get('b', ''))
        c_b = _normalize(correct_ans.get('b', ''))
        sb_correct = 1 if (s_b and c_b and (s_b == c_b or c_b in s_b)) else 0
        
        responses.append(WrittenAnswerResponse(
            id=a.id,
            question_number=a.question_number,
            student_answer=a.student_answer,
            score=a.score,
            score_a=sa_correct,
            score_b=sb_correct,
            reviewed_at=a.reviewed_at
        ))
    return responses


router = APIRouter()


@router.post("/submit", response_model=ResultResponse, status_code=status.HTTP_201_CREATED)
async def submit_test(
    submission: ResultSubmit,
    db: AsyncSession = Depends(get_db)
):
    """
    Submit test answers for grading.
    MCQ answers are auto-graded, written answers stored for manual review.
    Idempotent: if already submitted, returns existing result.
    """
    # Get session
    session = await get_session_by_token(db, submission.session_token)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # If already submitted, return existing result instead of error
    if session.is_submitted:
        stmt = select(Result).where(Result.session_id == session.id)
        existing = await db.execute(stmt)
        existing_result = existing.scalars().first()
        
        if existing_result:
            # Load answers for existing result
            stmt = select(MCQAnswer).where(MCQAnswer.result_id == existing_result.id)
            mcq_result = await db.execute(stmt)
            mcq_answers_list = mcq_result.scalars().all()
            
            stmt = select(WrittenAnswer).where(WrittenAnswer.result_id == existing_result.id)
            written_result = await db.execute(stmt)
            written_answers_list = written_result.scalars().all()
            
            written_responses = await _build_written_responses(db, written_answers_list, existing_result.test_id)
            
            return ResultResponse(
                id=existing_result.id,
                user_id=existing_result.user_id,
                test_id=existing_result.test_id,
                mcq_score=existing_result.mcq_score,
                written_score=existing_result.written_score,
                total_score=existing_result.total_score,
                submitted_at=existing_result.submitted_at,
                mcq_answers=[MCQAnswerResponse.model_validate(a) for a in mcq_answers_list],
                written_answers=written_responses
            )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Test already submitted but result not found"
        )
    
    # Note: we don't block expired sessions from submitting
    # because the timer auto-submits right when/after the session expires
    
    # Grade and save result
    try:
        result = await grade_and_save_result(db, session, submission)
        
        # Mark session as submitted
        await mark_session_submitted(db, session.id)
        
        # Load MCQ answers and written answers with explicit queries (avoid lazy loading)
        stmt = select(MCQAnswer).where(MCQAnswer.result_id == result.id)
        mcq_result = await db.execute(stmt)
        mcq_answers_list = mcq_result.scalars().all()
        
        stmt = select(WrittenAnswer).where(WrittenAnswer.result_id == result.id)
        written_result = await db.execute(stmt)
        written_answers_list = written_result.scalars().all()
        
        # Build response manually to avoid lazy loading issues
        written_responses = await _build_written_responses(db, written_answers_list, result.test_id)
        
        return ResultResponse(
            id=result.id,
            user_id=result.user_id,
            test_id=result.test_id,
            mcq_score=result.mcq_score,
            written_score=result.written_score,
            total_score=result.total_score,
            submitted_at=result.submitted_at,
            mcq_answers=[MCQAnswerResponse.model_validate(a) for a in mcq_answers_list],
            written_answers=written_responses
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error: {str(e)}"
        )


@router.get("/user/{user_id}", response_model=List[UserResultSummary])
async def get_user_results_endpoint(
    user_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all results for a user (for Telegram bot).
    """
    results = await get_user_results(db, user_id)
    
    # Build summaries with test info
    summaries = []
    for result in results:
        stmt = select(Test).where(Test.id == result.test_id)
        test_result = await db.execute(stmt)
        test = test_result.scalars().first()
        
        summaries.append(UserResultSummary(
            test_title=test.title if test else "Unknown Test",
            test_code=test.test_code if test else "",
            mcq_score=result.mcq_score,
            written_score=result.written_score,
            total_score=result.total_score,
            submitted_at=result.submitted_at
        ))
    
    return summaries


@router.get("/user/{user_id}/test-code/{test_code}")
async def get_user_result_by_test_code(
    user_id: UUID,
    test_code: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed result for a user by test code (for Telegram bot per-question view).
    """
    # Find test by code
    stmt = select(Test).where(Test.test_code == test_code.upper())
    test_result = await db.execute(stmt)
    test = test_result.scalars().first()
    
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test topilmadi"
        )
    
    # Find result for this user + test
    stmt = select(Result).where(
        Result.user_id == user_id,
        Result.test_id == test.id
    )
    result = await db.execute(stmt)
    result_record = result.scalars().first()
    
    if not result_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Natija topilmadi"
        )
    
    # Load MCQ answers
    stmt = select(MCQAnswer).where(MCQAnswer.result_id == result_record.id).order_by(MCQAnswer.question_number)
    mcq_result = await db.execute(stmt)
    mcq_answers_list = mcq_result.scalars().all()
    
    # Load written answers
    stmt = select(WrittenAnswer).where(WrittenAnswer.result_id == result_record.id).order_by(WrittenAnswer.question_number)
    written_result = await db.execute(stmt)
    written_answers_list = written_result.scalars().all()
    
    return {
        "test_title": test.title,
        "test_code": test.test_code,
        "mcq_score": result_record.mcq_score,
        "written_score": result_record.written_score,
        "total_score": result_record.total_score,
        "submitted_at": result_record.submitted_at.isoformat(),
        "mcq_answers": [
            {
                "question_number": a.question_number,
                "student_answer": a.student_answer,
                "correct_answer": a.correct_answer,
                "is_correct": a.is_correct
            }
            for a in mcq_answers_list
        ],
        "written_answers": [
            {
                "question_number": a.question_number,
                "student_answer": a.student_answer,
                "score": a.score
            }
            for a in written_answers_list
        ]
    }



@router.get("/{result_id}", response_model=ResultResponse)
async def get_result(
    result_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed result by ID.
    """
    stmt = select(Result).where(Result.id == result_id)
    result = await db.execute(stmt)
    result_record = result.scalars().first()
    
    if not result_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result not found"
        )
    
    # Load relationships
    stmt = select(MCQAnswer).where(MCQAnswer.result_id == result_id)
    mcq_result = await db.execute(stmt)
    result_record.mcq_answers = mcq_result.scalars().all()
    
    stmt = select(WrittenAnswer).where(WrittenAnswer.result_id == result_id)
    written_result = await db.execute(stmt)
    result_record.written_answers = written_result.scalars().all()
    
    return ResultResponse.model_validate(result_record)
