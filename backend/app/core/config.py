import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def get_database_url() -> str:
    value = os.getenv("DATABASE_URL", "").strip()
    if not value:
        raise RuntimeError("DATABASE_URL is required for PostgreSQL operations")
    return value


def get_sync_database_url() -> str:
    return get_database_url().replace("postgresql+asyncpg://", "postgresql://", 1)


def get_async_database_url() -> str:
    url = get_database_url()
    return url if url.startswith("postgresql+asyncpg://") else url.replace("postgresql://", "postgresql+asyncpg://", 1)