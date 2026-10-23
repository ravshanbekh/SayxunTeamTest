"""
Ro'yxatdan o'tgan o'quvchilar ro'yxati: hammasi yoki bitta test bo'yicha,
qidiruv, viloyat va holat filtri, sahifalash. Faqat o'qiydi — ma'lumot o'zgartirmaydi.
"""
import math
from typing import Optional
from uuid import UUID

from sqlalchemy import String, and_, case, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import BalanceTransaction
from app.models.result import Result
from app.models.session import TestSession
from app.models.user import User
from app.utils.timer import now_uz

MAX_PAGE_SIZE = 200
SESSION_STATUSES = ("submitted", "in_progress", "expired")

USER_SORTS = {
    "newest": (User.created_at.desc(),),
    "oldest": (User.created_at.asc(),),
    "name": (User.surname.asc(), User.full_name.asc()),
}
SESSION_SORTS = {
    "newest": (TestSession.started_at.desc(),),
    "oldest": (TestSession.started_at.asc(),),
    "name": (User.surname.asc(), User.full_name.asc()),
    "score": (Result.total_score.desc().nulls_last(), User.surname.asc()),
}


def _search_filter(q: Optional[str]):
    """Har bir so'z ism, familiya yoki Telegram ID ichida uchrashi kerak."""
    conditions = []
    for word in (q or "").split()[:5]:
        pattern = f"%{word}%"
        conditions.append(or_(
            User.full_name.ilike(pattern),
            User.surname.ilike(pattern),
            cast(User.telegram_id, String).like(pattern),
        ))
    return and_(*conditions) if conditions else None


def _session_status_expr(now):
    return case(
        (TestSession.is_submitted.is_(True), "submitted"),
        (or_(TestSession.is_expired.is_(True), TestSession.expires_at <= now), "expired"),
        else_="in_progress",
    )


def _page_info(total: int, page: int, page_size: int) -> dict:
    pages = max(1, math.ceil(total / page_size))
    return {"total": total, "page": min(page, pages), "page_size": page_size, "pages": pages}


async def list_students(
    db: AsyncSession,
    test_id: Optional[UUID] = None,
    q: Optional[str] = None,
    region: Optional[str] = None,
    status: Optional[str] = None,
    sort: str = "newest",
    page: int = 1,
    page_size: int = 20,
) -> dict:
    page = max(1, page)
    page_size = max(1, min(page_size, MAX_PAGE_SIZE))
    search = _search_filter(q)
    if test_id is None:
        return await _list_all(db, search, region, sort, page, page_size)
    return await _list_for_test(db, test_id, search, region, status, sort, page, page_size)


async def _list_all(db, search, region, sort, page, page_size) -> dict:
    tests_count = (select(TestSession.user_id, func.count().label("n"))
                   .group_by(TestSession.user_id).subquery())
    balance = (select(BalanceTransaction.user_id, func.sum(BalanceTransaction.amount).label("b"))
               .group_by(BalanceTransaction.user_id).subquery())

    filters = [f for f in (search, User.region == region if region else None) if f is not None]
    total = (await db.execute(select(func.count()).select_from(User).where(*filters))).scalar_one()
    info = _page_info(total, page, page_size)

    order = (tests_count.c.n.desc().nulls_last(), User.created_at.desc()) if sort == "tests" \
        else USER_SORTS.get(sort, USER_SORTS["newest"])
    stmt = (select(User, func.coalesce(tests_count.c.n, 0), func.coalesce(balance.c.b, 0))
            .outerjoin(tests_count, tests_count.c.user_id == User.id)
            .outerjoin(balance, balance.c.user_id == User.id)
            .where(*filters).order_by(*order, User.id)
            .offset((info["page"] - 1) * page_size).limit(page_size))
    rows = (await db.execute(stmt)).all()

    regions = (await db.execute(
        select(User.region).distinct().order_by(User.region))).scalars().all()

    items = [{
        "user_id": str(user.id),
        "telegram_id": user.telegram_id,
        "full_name": user.full_name,
        "surname": user.surname,
        "region": user.region,
        # created_at UTC'da saqlanadi ("Z" bilan brauzer mahalliy vaqtga o'giradi);
        # sessiya vaqtlari esa allaqachon Toshkent vaqtida
        "registered_at": user.created_at.isoformat() + "Z" if user.created_at else None,
        "tests_taken": int(n),
        "balance": int(bal),
    } for user, n, bal in rows]
    return {**info, "items": items, "regions": [r for r in regions if r], "summary": {"users": total}}


async def _list_for_test(db, test_id, search, region, status, sort, page, page_size) -> dict:
    now = now_uz()
    status_expr = _session_status_expr(now)
    base = [TestSession.test_id == test_id]
    if search is not None:
        base.append(search)
    if region:
        base.append(User.region == region)

    # Holatlar bo'yicha sonlar (holat filtrisiz) — tablarda ko'rsatiladi
    counts = (await db.execute(
        select(*[func.sum(case((status_expr == s, 1), else_=0)) for s in SESSION_STATUSES])
        .select_from(TestSession).join(User, User.id == TestSession.user_id)
        .where(*base))).one()
    summary = {s: int(n or 0) for s, n in zip(SESSION_STATUSES, counts)}
    summary["all"] = sum(summary.values())

    filters = list(base)
    if status in SESSION_STATUSES:
        filters.append(status_expr == status)
    total = summary[status] if status in SESSION_STATUSES else summary["all"]
    info = _page_info(total, page, page_size)

    stmt = (select(TestSession, User, Result, status_expr)
            .join(User, User.id == TestSession.user_id)
            .outerjoin(Result, Result.session_id == TestSession.id)
            .where(*filters)
            .order_by(*SESSION_SORTS.get(sort, SESSION_SORTS["newest"]), TestSession.id)
            .offset((info["page"] - 1) * page_size).limit(page_size))
    rows = (await db.execute(stmt)).all()

    regions = (await db.execute(
        select(User.region).distinct()
        .join(TestSession, TestSession.user_id == User.id)
        .where(TestSession.test_id == test_id).order_by(User.region))).scalars().all()

    items = [{
        "user_id": str(user.id),
        "session_id": str(session.id),
        "telegram_id": user.telegram_id,
        "full_name": user.full_name,
        "surname": user.surname,
        "region": user.region,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "status": st,
        "score": result.total_score if result else None,
        "mcq_score": result.mcq_score if result else None,
        "written_score": result.written_score if result else None,
    } for session, user, result, st in rows]
    return {**info, "items": items, "regions": [r for r in regions if r], "summary": summary}
