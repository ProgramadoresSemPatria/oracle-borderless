import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.support.core.context import CurrentAsyncSessionContext
from src.support.core.settings import settings


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(settings.database_url_async_test, poolclass=None)
    maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        CurrentAsyncSessionContext.set(session)
        try:
            yield session
            await session.rollback()
        finally:
            CurrentAsyncSessionContext.clear()
    await engine.dispose()
