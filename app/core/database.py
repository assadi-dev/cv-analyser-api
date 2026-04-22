"""
Async database engine and session factory.

Uses SQLAlchemy 2.x with asyncpg driver.
All database interactions must use async sessions.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

engine = create_async_engine(
    settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_pre_ping=True,          # Test connections before use
    echo=settings.debug,         # Log SQL queries in debug mode
    future=True,
)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------

AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

# ---------------------------------------------------------------------------
# Base declarative class
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    """
    Base class for all ORM models.
    All models must inherit from this class.
    """
    pass


# ---------------------------------------------------------------------------
# Dependency — FastAPI DI
# ---------------------------------------------------------------------------

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session per request.

    Usage:
        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception as exc:
            await session.rollback()
            logger.error(
                "Database session error — rolling back",
                exc_info=exc,
                extra={"session": str(session)},
            )
            raise


# ---------------------------------------------------------------------------
# Startup / shutdown helpers
# ---------------------------------------------------------------------------

async def connect_db() -> None:
    """Called on application startup to verify DB connectivity."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(lambda _: None)
        logger.info("Database connection established", extra={"url": settings.database_url[:30] + "..."})
    except Exception as exc:
        logger.critical("Failed to connect to database", exc_info=exc)
        raise


async def disconnect_db() -> None:
    """Called on application shutdown to dispose the engine pool."""
    await engine.dispose()
    logger.info("Database connection pool disposed")
