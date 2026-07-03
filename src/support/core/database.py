"""Dual engine SQLAlchemy: async (asyncpg, padrão) + sync (psycopg, jobstore/scripts)."""

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from src.support.core.settings import settings

# --- Engine assíncrono (padrão: HTTP, seeds, maioria dos jobs) ---
engine = create_async_engine(
    settings.database_url_async,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# --- Engine síncrono (APScheduler jobstore, scripts síncronos) ---
sync_engine = create_engine(
    settings.database_url_sync,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(bind=sync_engine, class_=Session, expire_on_commit=False)


async def dispose_engines() -> None:
    """Fecha os pools de conexão (chamado no shutdown)."""
    await engine.dispose()
    sync_engine.dispose()
