"""
Admin foydalanuvchi yaratish.

Docker:  docker compose exec backend python create_admin.py <login>
         (parol so'raladi; yoki ADMIN_PASSWORD muhit o'zgaruvchisi orqali)
"""
import argparse
import asyncio
import getpass
import os
import sys

from sqlalchemy import select

from app.database import AsyncSessionLocal, init_db
from app.models import user, admin, test, session, result  # noqa: F401 - modellarni ro'yxatdan o'tkazish
from app.models.admin import AdminUser
from app.schemas.admin import AdminCreate
from app.services.auth_service import create_admin


async def main(username: str, password: str, role: str) -> int:
    await init_db()
    async with AsyncSessionLocal() as db:
        existing = (await db.execute(select(AdminUser).where(AdminUser.username == username))).scalars().first()
        if existing:
            print(f"✗ '{username}' nomli admin allaqachon mavjud")
            return 1
        created = await create_admin(db, AdminCreate(username=username, password=password, role=role))
        print(f"✓ Admin yaratildi: {created.username}")
        return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Admin foydalanuvchi yaratish")
    parser.add_argument("username", nargs="?", default=os.getenv("ADMIN_USERNAME", "admin"))
    parser.add_argument("--role", default="admin")
    args = parser.parse_args()

    password = os.getenv("ADMIN_PASSWORD") or getpass.getpass("Parol (kamida 6 belgi): ")
    if len(password) < 6:
        print("✗ Parol kamida 6 belgidan iborat bo'lishi kerak")
        sys.exit(1)
    sys.exit(asyncio.run(main(args.username, password, args.role)))
