import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def get_database_url() -> str:
    value = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./euphoria_dev.db").strip()
    if not value:
        raise RuntimeError("DATABASE_URL is required")
    return value


def is_sqlite() -> bool:
    return get_database_url().startswith("sqlite")


def get_async_database_url() -> str:
    url = get_database_url()
    if url.startswith("sqlite:") and not url.startswith("sqlite+aiosqlite"):
        return url.replace("sqlite:", "sqlite+aiosqlite:", 1)
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def get_sync_database_url() -> str:
    url = get_database_url()
    if url.startswith("sqlite+aiosqlite"):
        return url.replace("sqlite+aiosqlite", "sqlite", 1)
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)
