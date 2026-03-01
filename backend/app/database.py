"""
Database configuration and session management.
Supports both PostgreSQL (production) and SQLite (local development).
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings


# Check if using SQLite
is_sqlite = settings.DATABASE_URL.startswith("sqlite")

# Create async engine with conditional pool settings  
if is_sqlite:
    # SQLite doesn't support pool settings
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        future=True,
    )
else:
    # PostgreSQL with connection pooling
    # Fix for Railway providing postgres:// but asyncpg needing postgresql+asyncpg://
    database_url = settings.DATABASE_URL
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(
        database_url,
        echo=False,
        future=True,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20
    )

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


async def get_db() -> AsyncSession:
    """
    Dependency for getting database sessions.
    Automatically handles session cleanup.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables and run migrations."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        # Run migrations for new columns on existing tables
        if not is_sqlite:
            from sqlalchemy import text
            migrations = [
                # Test table - time scheduling columns
                "ALTER TABLE tests ADD COLUMN IF NOT EXISTS start_time TIMESTAMP",
                "ALTER TABLE tests ADD COLUMN IF NOT EXISTS end_time TIMESTAMP",
                "ALTER TABLE tests ADD COLUMN IF NOT EXISTS extra_minutes INTEGER DEFAULT 0",
                # Test table - test type column (sertifikat or prezident)
                "ALTER TABLE tests ADD COLUMN IF NOT EXISTS test_type VARCHAR(20) DEFAULT 'sertifikat' NOT NULL",
                # TestSession table - per-session extension tracking
                "ALTER TABLE test_sessions ADD COLUMN IF NOT EXISTS extra_minutes INTEGER DEFAULT 0",
            ]
            for sql in migrations:
                try:
                    await conn.execute(text(sql))
                except Exception:
                    pass  # Column already exists or table doesn't exist yet


async def close_db():
    """Close database connections."""
    await engine.dispose()
