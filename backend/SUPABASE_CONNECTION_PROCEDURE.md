# Supabase PostgreSQL Connection Procedure

Use this only after code-side preparation is complete. Do not commit `backend/.env`.
Do not print `DATABASE_URL` in logs, screenshots, issues, or chat messages.

## 1. Configure Environment

Create `backend/.env` locally:

```env
APP_ENV=production
DATABASE_URL=<MY_SUPABASE_CONNECTION_STRING>
SECRET_KEY=<MY_SECRET_KEY>
ADMIN_EMAIL=<ADMIN_EMAIL>
ADMIN_PASSWORD=<ADMIN_PASSWORD>
```

`DATABASE_URL` may be a Supabase Transaction Pooler URL. Runtime converts `postgresql://` to `postgresql+asyncpg://` and disables asyncpg prepared statement caching with `statement_cache_size=0`. Runtime and inspection scripts also use `command_timeout=30`.

## 2. Inspect Before Migration

From `backend/`:

```powershell
python scripts/inspect_db_schema.py
python scripts/supabase_preflight.py
```

If preflight reports missing tables, missing columns, duplicates, invalid team/member rows, mismatched `team_members.hackathon_id`, invalid accommodation data, or any other conflict, stop. Do not run migrations and do not modify production data automatically.

## 3. Review Migration SQL

```powershell
alembic upgrade head --sql
```

Review the generated SQL. It must not contain `DROP TABLE`, `DELETE`, or `TRUNCATE`.

## 4. Run Migrations Only After Inspection Passes And SQL Review Is Safe

```powershell
alembic upgrade head
```

## 5. Inspect After Migration

```powershell
python scripts/inspect_db_schema.py
python scripts/supabase_preflight.py
```

## 6. Start Backend Against PostgreSQL

```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## 7. Verify New Registration

Submit a new test team through the existing website. Use a new team name and new participant identifiers that do not match local SQLite test data. Then verify in Supabase SQL editor or psql:

```sql
SELECT id, hackathon_id, registration_id, team_name, member_count, confirmation_accepted, submitted_at
FROM teams
WHERE registration_id = '<NEW_REGISTRATION_ID>';
```

```sql
SELECT team_id, hackathon_id, member_number, is_team_lead, name, email_normalized, phone_normalized, registration_number_normalized, euphoria_id_normalized
FROM team_members
WHERE team_id = (
    SELECT id FROM teams WHERE registration_id = '<NEW_REGISTRATION_ID>'
)
ORDER BY member_number;
```

Expected:

- one row in `teams`
- four or five rows in `team_members`
- matching `team_members.team_id = teams.id`
- matching `team_members.hackathon_id = teams.hackathon_id`
- no new rows in local SQLite

Do not copy local SQLite test registrations into Supabase.

## 8. Verify SQLite Was Not Used

With `APP_ENV=production`, the backend refuses SQLite. If a local `euphoria_dev.db` file exists from development, it should not receive the new Supabase test registration.
