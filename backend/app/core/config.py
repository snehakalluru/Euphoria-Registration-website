import os
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def get_app_env() -> str:
    return os.getenv("APP_ENV", "development").strip().lower()


def is_production() -> bool:
    return get_app_env() in {"production", "prod"}


def get_database_url() -> str:
    value = os.getenv("DATABASE_URL", "").strip()
    if not value and not is_production():
        value = "sqlite+aiosqlite:///./euphoria_dev.db"
    if not value:
        raise RuntimeError("DATABASE_URL is required when APP_ENV=production")
    if is_production() and value.startswith("sqlite"):
        raise RuntimeError("Production registrations require PostgreSQL DATABASE_URL; SQLite is only allowed for local development")
    return value


def is_sqlite() -> bool:
    return get_database_url().startswith("sqlite")


def _with_query_default(url: str, key: str, value: str, aliases: set[str] | None = None) -> str:
    aliases = aliases or set()
    parsed = urlsplit(url)
    query = parse_qsl(parsed.query, keep_blank_values=True)
    existing = {item_key.lower() for item_key, _ in query}
    if key.lower() in existing or any(alias.lower() in existing for alias in aliases):
        return url
    query.append((key, value))
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment))


def _rename_query_key(url: str, old_key: str, new_key: str) -> str:
    parsed = urlsplit(url)
    query = parse_qsl(parsed.query, keep_blank_values=True)
    has_new_key = any(item_key.lower() == new_key.lower() for item_key, _ in query)
    normalized = []
    for item_key, item_value in query:
        if item_key.lower() == old_key.lower():
            if not has_new_key:
                normalized.append((new_key, item_value))
                has_new_key = True
            continue
        normalized.append((item_key, item_value))
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(normalized), parsed.fragment))


def get_async_database_url() -> str:
    url = get_database_url()
    if url.startswith("sqlite:") and not url.startswith("sqlite+aiosqlite"):
        return url.replace("sqlite:", "sqlite+aiosqlite:", 1)
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql+asyncpg://"):
        url = _rename_query_key(url, "sslmode", "ssl")
        return _with_query_default(url, "ssl", "require")
    return url


def get_sync_database_url() -> str:
    url = get_database_url()
    if url.startswith("sqlite+aiosqlite"):
        return url.replace("sqlite+aiosqlite", "sqlite", 1)
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    if url.startswith("postgresql://"):
        url = _rename_query_key(url, "ssl", "sslmode")
        return _with_query_default(url, "sslmode", "require")
    return url
