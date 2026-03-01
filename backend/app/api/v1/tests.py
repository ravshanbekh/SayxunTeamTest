"""
Test endpoints - test management and retrieval.
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List
import os
import shutil

from app.database import get_db
from app.api.deps import get_current_admin
from app.models.admin import AdminUser
from app.schemas.test import TestCreate, TestResponse, TestUpdate, TestWithAnswerKey
from app.services.test_service import (
    create_test,
    get_test_by_code,
    get_test_by_id,
    get_all_tests,
    update_test,
    update_test_with_answers,
    delete_test,
    get_answer_key
)
from app.config import settings


router = APIRouter()


@router.post("/", response_model=TestResponse, status_code=status.HTTP_201_CREATED)
async def create_new_test(
    test_data: TestCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """
    Create a new test with answer key (admin only).
    """
    test = await create_test(db, test_data, current_admin.id)
    return test


@router.post("/{test_id}/upload-pdf")
async def upload_test_pdf(
    test_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """
    Upload PDF file for a test (admin only).
    """
    test = await get_test_by_id(db, test_id)
    
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )
    
    # Save file
    upload_dir = settings.UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, f"{test_id}.pdf")
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Update test record
    test.pdf_file_path = file_path
    await db.commit()
    
    return {"message": "PDF uploaded successfully", "file_path": file_path}


@router.get("/code/{test_code}", response_model=TestResponse)
async def get_test_by_code_endpoint(
    test_code: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get test by code (public - for students).
    """
    test = await get_test_by_code(db, test_code)
    
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found or inactive"
        )
    
    return test


@router.get("/{test_id}", response_model=TestWithAnswerKey)
async def get_test_with_key(
    test_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """
    Get test with answer key (admin only).
    """
    test = await get_test_by_id(db, test_id)
    
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )
    
    # Get answer key
    answer_key = await get_answer_key(db, test_id)
    
    # Build response dict manually to avoid lazy-loading ORM relationships
    test_dict = {
        "id": test.id,
        "test_code": test.test_code,
        "title": test.title,
        "description": test.description,
        "pdf_file_path": test.pdf_file_path,
        "is_active": test.is_active,
        "start_time": test.start_time,
        "end_time": test.end_time,
        "extra_minutes": test.extra_minutes,
        "test_type": test.test_type or 'sertifikat',
        "created_at": test.created_at,
        "answer_key": None
    }
    
    if answer_key:
        test_dict["answer_key"] = {
            "mcq_answers": answer_key.mcq_answers,
            "written_questions": answer_key.written_questions
        }
    
    return test_dict


@router.get("/", response_model=List[TestResponse])
async def list_tests(
    skip: int = 0,
    limit: int = 100,
    test_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """
    List all tests (admin only). Filter by test_type if provided.
    """
    tests = await get_all_tests(db, skip, limit, test_type=test_type)
    return tests


@router.patch("/{test_id}", response_model=TestResponse)
async def update_test_endpoint(
    test_id: UUID,
    test_data: TestUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """
    Update test information (admin only).
    """
    test = await update_test_with_answers(db, test_id, test_data)
    
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )
    
    return test


@router.delete("/{test_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_test_endpoint(
    test_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """
    Delete a test and all related data (admin only).
    """
    deleted = await delete_test(db, test_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )
