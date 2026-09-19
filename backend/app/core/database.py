from collections.abc import AsyncIterator

from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_async_database_url, is_sqlite

_engine = None
_factory = None


def _build_engine():
    if is_sqlite():
        return create_async_engine(get_async_database_url(), echo=False, connect_args={"check_same_thread": False})
    return create_async_engine(
        get_async_database_url(),
        pool_size=10,
        max_overflow=5,
        pool_timeout=30,
        pool_recycle=1800,
        pool_pre_ping=True,
        echo=False,
        connect_args={"statement_cache_size": 0, "command_timeout": 30},
    )


def get_engine():
    global _engine, _factory
    if _engine is None:
        _engine = _build_engine()
        _factory = async_sessionmaker(bind=_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)
    return _engine


def get_session_factory():
    if _factory is None:
        get_engine()
    return _factory


async def get_db() -> AsyncIterator[AsyncSession]:
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
        finally:
            if session.in_transaction():
                try:
                    await session.rollback()
                except DBAPIError:
                    pass
            await session.close()
