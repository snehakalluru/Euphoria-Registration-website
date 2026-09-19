import asyncio
import os
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_async_database_url


TABLES = ("admins", "clubs", "hackathons", "teams", "team_members")

REQUIRED_COLUMNS = {
    "teams": (
        "id",
        "hackathon_id",
        "registration_id",
        "team_name",
        "team_name_normalized",
        "college_type",
        "college_name",
        "member_count",
        "status",
        "confirmation_accepted",
        "submitted_at",
        "created_at",
        "updated_at",
    ),
    "team_members": (
        "id",
        "team_id",
        "hackathon_id",
        "member_number",
        "is_team_lead",
        "name",
        "registration_number",
        "registration_number_normalized",
        "email",
        "email_normalized",
        "phone",
        "phone_normalized",
        "gender",
        "year",
        "branch",
        "section",
        "euphoria_id",
        "euphoria_id_normalized",
        "accommodation_type",
        "hostel_name",
        "room_number",
        "warden_name",
        "warden_phone",
        "id_proof_path",
        "id_proof_filename",
        "id_proof_content_type",
        "created_at",
        "updated_at",
    ),
}

CONFLICT_QUERIES = (
    (
        "duplicate registration_id",
        """
        SELECT registration_id, COUNT(*) AS count
        FROM teams
        GROUP BY registration_id
        HAVING COUNT(*) > 1
        """,
    ),
    (
        "duplicate team_name_normalized per hackathon",
        """
        SELECT hackathon_id, team_name_normalized, COUNT(*) AS count
        FROM teams
        GROUP BY hackathon_id, team_name_normalized
        HAVING COUNT(*) > 1
        """,
    ),
    (
        "invalid team member_count",
        """
        SELECT id, registration_id, team_name, member_count
        FROM teams
        WHERE member_count NOT BETWEEN 4 AND 5
        """,
    ),
    (
        "confirmation not accepted",
        """
        SELECT id, registration_id, team_name, confirmation_accepted
        FROM teams
        WHERE confirmation_accepted IS DISTINCT FROM TRUE
        """,
    ),
    (
        "external team missing college_name",
        """
        SELECT id, registration_id, team_name, college_type, college_name
        FROM teams
        WHERE college_type = 'external'
          AND NULLIF(TRIM(college_name), '') IS NULL
        """,
    ),
    (
        "team_members pointing to missing/mismatched team",
        """
        SELECT tm.id, tm.team_id, tm.hackathon_id
        FROM team_members tm
        LEFT JOIN teams t ON t.id = tm.team_id AND t.hackathon_id = tm.hackathon_id
        WHERE t.id IS NULL
        """,
    ),
    (
        "duplicate member_number per team",
        """
        SELECT team_id, member_number, COUNT(*) AS count
        FROM team_members
        GROUP BY team_id, member_number
        HAVING COUNT(*) > 1
        """,
    ),
    (
        "invalid member_number",
        """
        SELECT id, team_id, member_number
        FROM team_members
        WHERE member_number NOT BETWEEN 1 AND 5
        """,
    ),
    (
        "invalid team lead position",
        """
        SELECT id, team_id, member_number, is_team_lead
        FROM team_members
        WHERE NOT ((member_number = 1 AND is_team_lead IS TRUE) OR (member_number > 1 AND is_team_lead IS FALSE))
        """,
    ),
    (
        "team without exactly one lead",
        """
        SELECT team_id, COUNT(*) FILTER (WHERE is_team_lead IS TRUE) AS lead_count
        FROM team_members
        GROUP BY team_id
        HAVING COUNT(*) FILTER (WHERE is_team_lead IS TRUE) <> 1
        """,
    ),
    (
        "duplicate euphoria_id_normalized per hackathon",
        """
        SELECT hackathon_id, euphoria_id_normalized, COUNT(*) AS count
        FROM team_members
        GROUP BY hackathon_id, euphoria_id_normalized
        HAVING COUNT(*) > 1
        """,
    ),
    (
        "duplicate email_normalized per hackathon",
        """
        SELECT hackathon_id, email_normalized, COUNT(*) AS count
        FROM team_members
        GROUP BY hackathon_id, email_normalized
        HAVING COUNT(*) > 1
        """,
    ),
    (
        "duplicate phone_normalized per hackathon",
        """
        SELECT hackathon_id, phone_normalized, COUNT(*) AS count
        FROM team_members
        GROUP BY hackathon_id, phone_normalized
        HAVING COUNT(*) > 1
        """,
    ),
    (
        "duplicate registration_number_normalized per hackathon",
        """
        SELECT hackathon_id, registration_number_normalized, COUNT(*) AS count
        FROM team_members
        GROUP BY hackathon_id, registration_number_normalized
        HAVING COUNT(*) > 1
        """,
    ),
    (
        "invalid accommodation fields",
        """
        SELECT id, team_id, member_number, accommodation_type, hostel_name, room_number, warden_name, warden_phone
        FROM team_members
        WHERE NOT (
            (accommodation_type IS NULL AND hostel_name IS NULL AND room_number IS NULL AND warden_name IS NULL AND warden_phone IS NULL)
            OR (accommodation_type = 'day_scholar' AND hostel_name IS NULL AND room_number IS NULL AND warden_name IS NULL AND warden_phone IS NULL)
            OR (
                accommodation_type = 'hosteller'
                AND NULLIF(TRIM(hostel_name), '') IS NOT NULL
                AND NULLIF(TRIM(room_number), '') IS NOT NULL
                AND NULLIF(TRIM(warden_name), '') IS NOT NULL
                AND NULLIF(TRIM(warden_phone), '') IS NOT NULL
            )
        )
        """,
    ),
)


async def main() -> None:
    if not os.getenv("DATABASE_URL"):
        raise RuntimeError("Set DATABASE_URL in the environment before running Supabase preflight.")

    table_list = ", ".join(f"'{table}'" for table in TABLES)
    engine = create_async_engine(get_async_database_url(), connect_args={"statement_cache_size": 0, "command_timeout": 30})
    has_conflicts = False
    async with engine.connect() as conn:
        print("Supabase preflight: checking required tables")
        existing = {
            row[0]
            for row in (
                await conn.execute(
                    text(
                        f"""
                        SELECT table_name
                        FROM information_schema.tables
                        WHERE table_schema = 'public'
                          AND table_name IN ({table_list})
                        """
                    )
                )
            )
        }
        missing_tables = sorted(set(TABLES) - existing)
        if missing_tables:
            has_conflicts = True
            print(f"Missing tables: {missing_tables}")
        else:
            print("Required tables: OK")

        print("\nSupabase preflight: checking required columns")
        for table, columns in REQUIRED_COLUMNS.items():
            result = await conn.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = :table
                    """
                ),
                {"table": table},
            )
            existing_columns = {row[0] for row in result}
            missing_columns = sorted(set(columns) - existing_columns)
            if missing_columns:
                has_conflicts = True
                print(f"{table}: missing columns {missing_columns}")
            else:
                print(f"{table}: OK")

        if missing_tables:
            print("\nSkipping data-conflict checks because required tables are missing.")
        else:
            print("\nSupabase preflight: checking data that would conflict with constraints")
            for label, sql in CONFLICT_QUERIES:
                result = await conn.execute(text(sql))
                rows = [dict(row) for row in result.mappings()]
                if rows:
                    has_conflicts = True
                    print(f"\nCONFLICT: {label}")
                    for row in rows[:25]:
                        print(row)
                    if len(rows) > 25:
                        print(f"... {len(rows) - 25} more row(s)")
                else:
                    print(f"{label}: OK")

    await engine.dispose()
    if has_conflicts:
        raise SystemExit("Supabase preflight found conflicts. Do not run migrations until these are reviewed.")
    print("\nSupabase preflight passed. It is safe to proceed to Alembic inspection/migration.")


if __name__ == "__main__":
    asyncio.run(main())
