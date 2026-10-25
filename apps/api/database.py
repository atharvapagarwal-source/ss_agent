"""
Async SQLAlchemy database engine and session management.
Uses asyncpg driver for non-blocking PostgreSQL access,
or SQLite fallback stored in /tmp/app.db for serverless environments.
"""
import os
import sys
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from config import settings
import structlog

logger = structlog.get_logger(__name__)

# Determine clean database URL
raw_db_url = settings.DATABASE_URL or ""
if not raw_db_url or "localhost" in raw_db_url:
    # Safe non-blocking serverless fallback in /tmp
    db_url = "sqlite+aiosqlite:////tmp/app.db"
elif raw_db_url.startswith("postgresql://"):
    db_url = raw_db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif raw_db_url.startswith("postgres://"):
    db_url = raw_db_url.replace("postgres://", "postgresql+asyncpg://", 1)
else:
    db_url = raw_db_url

engine_kwargs = {
    "echo": settings.DEBUG,
}

if "sqlite" in db_url:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 5
    engine_kwargs["pool_pre_ping"] = True

try:
    engine = create_async_engine(db_url, **engine_kwargs)
except Exception as e:
    logger.warning("Failed to create primary engine, falling back to /tmp/app.db", error=str(e))
    engine = create_async_engine("sqlite+aiosqlite:////tmp/app.db", connect_args={"check_same_thread": False})

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency that provides a scoped async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def set_tenant_context(session: AsyncSession, tenant_id: str, user_role: str) -> None:
    """
    Sets PostgreSQL session-level variables for RLS enforcement.
    Safely ignores if running on SQLite fallback.
    """
    try:
        await session.execute(
            text("SELECT set_config('app.current_tenant_id', :tid, TRUE), "
                 "set_config('app.current_user_role', :role, TRUE)"),
            {"tid": str(tenant_id), "role": user_role},
        )
    except Exception as e:
        logger.debug("set_tenant_context skipped (non-PostgreSQL)", error=str(e))
