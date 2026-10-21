"""
Admin endpoints - grading, student management, and exports.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Response, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import List
import os

from app.database import get_db
from app.api.deps import get_current_admin
from app.models.admin import AdminUser
from app.models.user import User
from app.models.result import WrittenAnswer
from app.schemas.result import WrittenAnswerGrade, WrittenAnswerResponse
from app.schemas.user import UserResponse
from app.services.grading_service import grade_written_answer, get_ungraded_written_answers
from app.services.export_service import export_results_to_excel, export_results_to_pdf
from app.config import settings


router = APIRouter()


@router.get("/students", response_model=List[UserResponse])
async def get_all_students(
    skip: int = 0,
    limit: int = 5000,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """
    Get all registered students (admin only).
    """
    stmt = select(User).offset(skip).limit(limit).order_by(User.created_at.desc())
    result = await db.execute(stmt)
    users = result.scalars().all()
    
    return users


@router.get("/written-answers/pending", response_model=List[WrittenAnswerResponse])
async def get_pending_written_answers(
    test_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """
    Get all ungraded written answers (admin only).
    Optionally filter by test_id.
    """
    written_answers = await get_ungraded_written_answers(db, test_id)
    return written_answers


@router.post("/grade-written", response_model=WrittenAnswerResponse)
async def grade_written_answer_endpoint(
    grade_data: WrittenAnswerGrade,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """
    Grade a written answer (admin only).
    """
    written_answer = await grade_written_answer(
        db,
        grade_data.written_answer_id,
        current_admin.id,
        grade_data.score,
        grade_data.comments
    )
    
    if not written_answer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Written answer not found"
        )
    
    return WrittenAnswerResponse.model_validate(written_answer)


@router.get("/reports/{test_id}/excel")
async def export_test_results_excel(
    test_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """
    Export test results to Excel (admin only).
    """
    # Generate filename
    export_dir = settings.EXPORT_DIR
    os.makedirs(export_dir, exist_ok=True)
    filepath = os.path.join(export_dir, f"test_{test_id}_results.xlsx")
    
    # Generate Excel
    await export_results_to_excel(db, test_id, filepath)
    
    if not os.path.exists(filepath):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate export"
        )
    
    # Read file
    with open(filepath, "rb") as f:
        content = f.read()
    
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=test_results.xlsx"}
    )


@router.get("/reports/{test_id}/pdf")
async def export_test_results_pdf(
    test_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """
    Export test results to PDF (admin only).
    """
    # Generate filename
    export_dir = settings.EXPORT_DIR
    os.makedirs(export_dir, exist_ok=True)
    filepath = os.path.join(export_dir, f"test_{test_id}_results.pdf")
    
    # Generate PDF
    await export_results_to_pdf(db, test_id, filepath)
    
    if not os.path.exists(filepath):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate export"
        )
    
    # Read file
    with open(filepath, "rb") as f:
        content = f.read()
    
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=test_results.pdf"}
    )


async def _rasch_report_or_404(db: AsyncSession, test_id: UUID):
    from app.services.rasch_report_service import build_rasch_report

    report = await build_rasch_report(db, test_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test topilmadi"
        )
    return report


@router.get("/reports/{test_id}/rasch")
async def get_rasch_results(
    test_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """
    Rasch modeli asosidagi natijalar (JSON) - milliy sertifikat uslubida (admin only).
    """
    report = await _rasch_report_or_404(db, test_id)
    analysis = report.analysis
    return {
        "test_id": str(report.test.id),
        "test_code": report.test.test_code,
        "title": report.test.title,
        "participants": len(report.rows),
        "source_counts": report.source_counts(),
        "items": len(report.item_labels),
        "reliability": analysis.reliability,
        "grade_counts": report.grade_counts(),
        "warnings": analysis.warnings,
        "results": [
            {
                "rank": r.rank,
                "source": r.source,
                "user_id": str(r.user_id) if r.user_id else None,
                "name": r.name,
                "region": r.region,
                "correct": r.correct,
                "theta": round(r.theta, 4),
                "rasch_score": r.score,
                "percent": r.percent,
                "grade": r.grade,
                "fan1": r.fan1,
                "fan2": r.fan2,
            }
            for r in report.rows
        ],
        "item_analysis": [
            {
                "item": label,
                "correct_count": item.correct_count,
                "difficulty": round(item.difficulty, 4),
                "extreme": item.extreme,
            }
            for label, item in zip(report.item_labels, analysis.items)
        ],
    }


@router.get("/reports/{test_id}/rasch/pdf")
async def export_rasch_pdf(
    test_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """
    Rasch natijalari PDF (rangli jadval, milliy sertifikat ko'rinishida) - admin only.
    """
    from app.services.rasch_report_service import export_rasch_to_pdf

    report = await _rasch_report_or_404(db, test_id)
    filepath = os.path.join(settings.EXPORT_DIR, f"test_{test_id}_rasch.pdf")
    export_rasch_to_pdf(report, filepath)

    with open(filepath, "rb") as f:
        content = f.read()

    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=rasch_natijalar.pdf"}
    )


@router.get("/reports/{test_id}/rasch/excel")
async def export_rasch_excel(
    test_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """
    Rasch natijalari Excel (natijalar, savollar tahlili, 0/1 matritsa) - admin only.
    """
    from app.services.rasch_report_service import export_rasch_to_excel

    report = await _rasch_report_or_404(db, test_id)
    filepath = os.path.join(settings.EXPORT_DIR, f"test_{test_id}_rasch.xlsx")
    export_rasch_to_excel(report, filepath)

    with open(filepath, "rb") as f:
        content = f.read()

    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=rasch_natijalar.xlsx"}
    )


# ---------------------------------------------------------------------------
# Offline natijalar (qog'ozda o'tkazilgan imtihon, Excel 0/1)
# ---------------------------------------------------------------------------
MAX_OFFLINE_FILE_BYTES = 10 * 1024 * 1024


async def _test_or_404(db: AsyncSession, test_id: UUID):
    from app.models.test import Test

    test = (await db.execute(select(Test).where(Test.id == test_id))).scalars().first()
    if not test:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test topilmadi")
    return test


@router.get("/tests/{test_id}/offline/template")
async def download_offline_template(
    test_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """Offline natijalarni kiritish uchun Excel shablon (admin only)."""
    from app.services.offline_service import build_template

    test = await _test_or_404(db, test_id)
    content = build_template(test, test.test_type or "sertifikat")
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=offline_shablon.xlsx"}
    )


@router.post("/tests/{test_id}/offline/upload")
async def upload_offline_results(
    test_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """
    To'ldirilgan shablonni yuklash (admin only).
    Testning oldingi offline natijalari yangisi bilan almashtiriladi.
    """
    from app.services.offline_service import parse_offline_excel, replace_offline_results, OfflineImportError

    test = await _test_or_404(db, test_id)
    content = await file.read(MAX_OFFLINE_FILE_BYTES + 1)
    if len(content) > MAX_OFFLINE_FILE_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail={"message": "Fayl juda katta (maksimal 10 MB)", "errors": []})
    try:
        rows = parse_offline_excel(content, test.test_type or "sertifikat")
    except OfflineImportError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail={"message": e.message, "errors": e.errors})

    imported, replaced = await replace_offline_results(db, test_id, rows)
    return {
        "message": f"{imported} ta offline natija yuklandi",
        "imported": imported,
        "replaced": replaced,
    }


@router.get("/tests/{test_id}/offline")
async def get_offline_results(
    test_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """Yuklangan offline natijalar ro'yxati (admin only)."""
    from app.services.offline_service import list_offline_results

    await _test_or_404(db, test_id)
    items = await list_offline_results(db, test_id)
    return {
        "count": len(items),
        "results": [
            {"id": str(o.id), "name": o.full_name, "region": o.region,
             "correct": sum(1 for v in (o.answers or []) if v)}
            for o in items
        ],
    }


@router.delete("/tests/{test_id}/offline")
async def remove_offline_results(
    test_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """Testning barcha offline natijalarini o'chirish (admin only)."""
    from app.services.offline_service import delete_offline_results

    await _test_or_404(db, test_id)
    deleted = await delete_offline_results(db, test_id)
    return {"message": f"{deleted} ta offline natija o'chirildi", "deleted": deleted}


@router.delete("/sessions/{test_id}", status_code=status.HTTP_200_OK)
async def clear_test_sessions(
    test_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """
    Clear all sessions for a test (admin only).
    This allows students to retake the test.
    Also deletes associated results.
    """
    from app.models.session import TestSession
    from app.models.result import Result
    
    # Delete results first (foreign key constraint)
    stmt = select(Result).where(Result.test_id == test_id)
    result = await db.execute(stmt)
    results = result.scalars().all()
    for r in results:
        await db.delete(r)
    
    # Delete sessions
    stmt = select(TestSession).where(TestSession.test_id == test_id)
    result = await db.execute(stmt)
    sessions = result.scalars().all()
    for s in sessions:
        await db.delete(s)
    
    await db.commit()
    
    return {
        "message": f"Cleared {len(sessions)} sessions and {len(results)} results for test",
        "sessions_deleted": len(sessions),
        "results_deleted": len(results)
    }


@router.get("/sessions/{test_id}/list")
async def list_test_sessions(
    test_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """
    List all sessions for a test with user info (admin only).
    Shows each student's session so admin can extend individually.
    """
    from app.models.session import TestSession
    from sqlalchemy.orm import selectinload
    
    stmt = select(TestSession).options(
        selectinload(TestSession.user)
    ).where(
        TestSession.test_id == test_id
    ).order_by(TestSession.started_at.desc())
    
    result = await db.execute(stmt)
    sessions = result.scalars().all()
    
    session_list = []
    for s in sessions:
        session_list.append({
            "id": str(s.id),
            "user_name": f"{s.user.full_name} {s.user.surname}" if s.user else "Noma'lum",
            "user_region": s.user.region if s.user else "",
            "started_at": s.started_at.isoformat() if s.started_at else None,
            "expires_at": s.expires_at.isoformat() if s.expires_at else None,
            "is_submitted": s.is_submitted,
            "is_expired": s.is_expired,
            "extra_minutes": s.extra_minutes,
            "extensions_left": max(0, 3 - (s.extra_minutes // 5))
        })
    
    return session_list


@router.post("/sessions/{session_id}/extend")
async def extend_session_endpoint(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """
    Extend a specific session by 5 minutes (admin only).
    Maximum 3 extensions (15 minutes total) per session.
    """
    from app.services.session_service import extend_session
    
    try:
        session = await extend_session(db, session_id)
    except ValueError as e:
        error_msg = str(e)
        if error_msg == "SESSION_ALREADY_SUBMITTED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bu session allaqachon topshirilgan"
            )
        elif error_msg == "MAX_EXTENSIONS_REACHED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maksimal uzaytirish chegarasiga yetildi (3 marta)"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session topilmadi"
        )
    
    return {
        "message": f"Session 5 daqiqa uzaytirildi",
        "new_expires_at": session.expires_at.isoformat(),
        "extra_minutes": session.extra_minutes,
        "extensions_left": max(0, 3 - (session.extra_minutes // 5))
    }


@router.post("/tests/{test_id}/extend-all")
async def extend_all_sessions_endpoint(
    test_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """
    Extend ALL active sessions for a test by 5 minutes (admin only).
    Each session has its own max of 15 minutes (3 extensions).
    """
    from app.models.session import TestSession
    from datetime import datetime, timedelta
    
    stmt = select(TestSession).where(
        TestSession.test_id == test_id,
        TestSession.is_submitted == False,
        TestSession.is_expired == False
    )
    result = await db.execute(stmt)
    sessions = result.scalars().all()
    
    extended = 0
    skipped = 0
    for s in sessions:
        if s.extra_minutes >= 15:
            skipped += 1
            continue
        s.extra_minutes += 5
        s.expires_at = s.expires_at + timedelta(minutes=5)
        extended += 1
    
    await db.commit()
    
    return {
        "message": f"{extended} ta sessiya 5 daqiqa uzaytirildi",
        "extended": extended,
        "skipped": skipped,
        "total": len(sessions)
    }
