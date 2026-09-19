# Euphoria Hackathon Registration Platform — PRD

## Problem statement (verbatim)
Production-quality, secure, scalable and premium platform for the ONE Euphoria Hackathon co-hosted by FIVE collaborating clubs. Central team registration only — no payments, no event selection, no participant login, no public editing after submit. Cinematic dark-brown/gold aesthetic. Built by GDG On Campus · KARE.

## Stack
- Frontend: React SPA (CRA + craco) at /app/frontend — user opted for SPA over Next.js
- Backend: FastAPI + SQLAlchemy 2 async at /app/backend
- Database: SQLite dev fallback (aiosqlite) at `euphoria_dev.db`; Supabase Postgres pluggable via `DATABASE_URL`
- Auth: JWT + bcrypt admin login (seeded via ENV)
- Storage: **Emergent Object Storage** via `emergentintegrations` proxy (init at startup)

## What's implemented (2026-02-19)
- Landing page (cinematic intro, hero, five collaborating clubs with logos, rules/eligibility accordions, six SDG goals, register CTA)
- "Built by GDG On Campus · KARE" fixed corner badge
- 3-step registration (details → review → success) with sessionStorage draft persistence
- Team lead ID proof upload during registration (PNG/JPG/WEBP/PDF · max 5 MB)
- 4–5 member team enforcement, conditional Internal (day scholar / hosteller + hostel fields) vs External college
- Duplicate detection (team name / email / phone / registration number / Euphoria ID) with normalisation + IntegrityError catch
- Registration ID generator (EUH26-XXXXXX), atomic transaction, confirmation checkbox
- Success page with WhatsApp CTA
- Admin dashboard (statistics grid, paginated + filterable registration table, detail modal, CSV export, ID proof download)
- Admin branding tab (upload hackathon logo + 5 club logos, rename clubs + faculty/student in-charge)
- Public `/api/media/{path}` proxy for image assets (images only)
- Backend fully tested: 27 base + 17 upload = **44 pytest cases at 100%**

## Personas
- Student team leads registering the team (Team Lead) — needs frictionless 4/5 member entry with ID proof upload
- Team members — data collected via lead's form
- Organiser admin — logs into `/admin/login`, monitors stats, filters registrations, exports CSV, uploads branding

## Core requirements (static)
- One hackathon, exactly five clubs, no multi-event
- Team size 4-5, Member 1 = Team Lead (only), sequential numbering
- Global uniqueness across the hackathon (team name normalized, phone digits, email lowercase, IDs uppercase)
- No public editing after submit
- Ingress: backend routes under `/api/*`; frontend uses `REACT_APP_BACKEND_URL`

## Prioritised backlog
- P0 (pending): Provide Supabase Postgres connection string; swap `DATABASE_URL` and run Alembic (`0001_initial_euphoria_schema.py` already committed)
- P1: Faculty/student contact rendering on landing (hidden by default, admin toggle)
- P1: Email confirmation (Resend integration) sending the Registration ID to the team lead
- P1: Rate limit + brute-force lockout on `/api/admin/auth/login`
- P2: Storage sync helper — after upload use `await asyncio.to_thread(requests.put, ...)` to keep event loop responsive under load
- P2: Orphan ID-proof cleanup cron (files uploaded but registration never submitted)
- P2: SVG logo sanitization or restrict to raster
- P2: Alembic migration to add `id_proof_*` columns for prod (currently only created via `create_all` on SQLite)

## Test credentials
- `/app/memory/test_credentials.md` — Admin `admin@euphoria.dev / Admin@12345`

## Key files
- Backend entrypoint: `/app/backend/server.py` → `app.main:app`
- Storage service: `/app/backend/app/services/storage.py`
- Registration service: `/app/backend/app/services/registration_service.py`
- Frontend root: `/app/frontend/src/App.js`
- Styles: `/app/frontend/src/App.css`
