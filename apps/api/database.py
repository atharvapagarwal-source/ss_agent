"""
Async SQLAlchemy database engine and session management.
Uses asyncpg driver for non-blocking PostgreSQL access.
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from config import settings
import structlog

logger = structlog.get_logger(__name__)

# Async engine for FastAPI request handlers
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    echo=settings.DEBUG,
)

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
    Must be called at the start of every authenticated request.
    """
    await session.execute(
        text("SELECT set_config('app.current_tenant_id', :tid, TRUE), "
             "set_config('app.current_user_role', :role, TRUE)"),
        {"tid": str(tenant_id), "role": user_role},
    )
