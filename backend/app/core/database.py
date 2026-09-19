from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_async_database_url


def create_engine():
    return create_async_engine(
        get_async_database_url(),
        pool_size=10,
        max_overflow=5,
        pool_timeout=30,
        pool_recycle=1800,
        echo=False,
        connect_args={"statement_cache_size": 0, "command_timeout": 30},
    )


async def get_db() -> AsyncIterator[AsyncSession]:
    engine = create_engine()
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.close()
            await engine.dispose()