import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core import config


def test_async_postgres_url_converts_sslmode_to_asyncpg_ssl(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://user:pass@example.supabase.co:6543/postgres?sslmode=require",
    )

    assert config.get_async_database_url() == (
        "postgresql+asyncpg://user:pass@example.supabase.co:6543/postgres?ssl=require"
    )


def test_async_postgres_url_adds_ssl_when_missing(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@example.supabase.co:6543/postgres")

    assert config.get_async_database_url() == (
        "postgresql+asyncpg://user:pass@example.supabase.co:6543/postgres?ssl=require"
    )


def test_sync_postgres_url_converts_asyncpg_ssl_to_psycopg_sslmode(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://user:pass@example.supabase.co:6543/postgres?ssl=require",
    )

    assert config.get_sync_database_url() == (
        "postgresql://user:pass@example.supabase.co:6543/postgres?sslmode=require"
    )
