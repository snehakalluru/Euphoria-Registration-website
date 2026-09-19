import asyncio
import os
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_async_database_url


SCHEMA_SQL = """
SELECT
    c.table_name,
    c.column_name,
    c.data_type,
    c.udt_name,
    c.is_nullable,
    c.column_default
FROM information_schema.columns c
WHERE c.table_schema = 'public'
  AND c.table_name IN ('admins', 'clubs', 'hackathons', 'teams', 'team_members')
ORDER BY c.table_name, c.ordinal_position;
"""

CONSTRAINT_SQL = """
SELECT
    tc.table_name,
    tc.constraint_name,
    tc.constraint_type,
    pg_get_constraintdef(con.oid) AS definition
FROM information_schema.table_constraints tc
JOIN pg_constraint con ON con.conname = tc.constraint_name
JOIN pg_namespace nsp ON nsp.oid = con.connamespace AND nsp.nspname = tc.table_schema
WHERE tc.table_schema = 'public'
  AND tc.table_name IN ('admins', 'clubs', 'hackathons', 'teams', 'team_members')
ORDER BY tc.table_name, tc.constraint_type, tc.constraint_name;
"""

INDEX_SQL = """
SELECT tablename, indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename IN ('admins', 'clubs', 'hackathons', 'teams', 'team_members')
ORDER BY tablename, indexname;
"""


async def main() -> None:
    if not os.getenv("DATABASE_URL"):
        raise RuntimeError("Set DATABASE_URL before inspecting Supabase PostgreSQL")
    engine = create_async_engine(get_async_database_url(), connect_args={"statement_cache_size": 0, "command_timeout": 30})
    async with engine.connect() as conn:
        for title, sql in (("COLUMNS", SCHEMA_SQL), ("CONSTRAINTS", CONSTRAINT_SQL), ("INDEXES", INDEX_SQL)):
            print(f"\n## {title}")
            result = await conn.execute(text(sql))
            for row in result.mappings():
                print(dict(row))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
