# Euphoria Admin Authentication Testing

Authentication uses PostgreSQL `admins`, bcrypt password hashes, and JWT access tokens.

## Required environment

Set `DATABASE_URL`, `SECRET_KEY`, `ADMIN_EMAIL`, and `ADMIN_PASSWORD` only in the local environment. Never commit them.

For production Supabase, also set `APP_ENV=production`. The backend refuses to boot with SQLite in production mode.

Before production boot, run Alembic from `backend/` with the Supabase `DATABASE_URL` set:

```bash
alembic upgrade head
```

To inspect the live Supabase schema without printing credentials:

```bash
python scripts/inspect_db_schema.py
```

## Checks

1. Seed one development admin with a bcrypt password hash.
2. `POST /api/admin/auth/login` with valid credentials returns an access token and secure HTTP-only cookie.
3. Invalid credentials return HTTP 401 without revealing which field failed.
4. `/api/admin/statistics` returns HTTP 401 without a token.
5. `/api/admin/statistics` succeeds with a valid bearer token.
6. Expired or malformed tokens return HTTP 401.
7. Inactive admins cannot authenticate.
8. No API response includes `password_hash`.
