import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_cors_origins, is_sqlite
from app.core.database import get_engine, get_session_factory
from app.core.security import hash_password
from app.models import Admin, Base, Club, Hackathon
from app.routes.public import router as public_router
from app.routes.admin import router as admin_router
from app.routes.uploads import router as uploads_router
from app.services.storage import init_storage

logger = logging.getLogger(__name__)


DEV_RULES = [
    {"title": "Team size", "body": "Every team must have a minimum of four members and a maximum of five."},
    {"title": "Original work", "body": "All submissions must be original work created during the hackathon window."},
    {"title": "Conduct", "body": "Participants must follow the official code of conduct at all times."},
]
DEV_ELIGIBILITY = [
    {"title": "Enrolment", "body": "Students actively enrolled at a recognised institution."},
    {"title": "Euphoria registration", "body": "Every team member must have completed the individual Euphoria registration and hold an Euphoria ID."},
]
DEV_INSTRUCTIONS = [
    {"title": "Bring your ID", "body": "Carry your college ID and Euphoria ID confirmation on the event day."},
    {"title": "Ideate early", "body": "Discuss your problem statement with your team before arriving."},
]
DEV_SDG_GOALS = [
    {"code": "SDG 2", "title": "Zero Hunger & Sustainable Agriculture"},
    {"code": "SDG 3", "title": "Good Health & Well-being Innovation"},
    {"code": "SDG 4", "title": "Quality Education & Lifelong Learning"},
    {"code": "SDG 6", "title": "Clean Water & Sanitation"},
    {"code": "SDG 11", "title": "Sustainable Cities & Communities"},
    {"code": "SDG 13", "title": "Climate Action & Environmental Monitoring"},
]
DEV_CLUBS = [
    {"name": "GFG Campus Body · KARE", "slug": "gfg-kare", "display_order": 1, "description": "GeeksforGeeks Campus Body at KARE — flagship organiser", "logo_url": "https://customer-assets-eiarnc6j.emergentagent.net/job_12145b8e-9780-481f-b432-98049080e6cc/artifacts/kwb4jxde_GFG%20LOGO.webp"},
    {"name": "KARE ACM Student Chapter", "slug": "acm-kare", "display_order": 2, "description": "Association for Computing Machinery · KARE student chapter", "logo_url": "https://customer-assets-eiarnc6j.emergentagent.net/job_12145b8e-9780-481f-b432-98049080e6cc/artifacts/8f6z2auc_WhatsApp%20Image%202026-09-09%20at%209.58.21%20PM.jpeg"},
    {"name": "KARE IEEE Education Society", "slug": "ieee-eds", "display_order": 3, "description": "IEEE Education Society · KARE chapter", "logo_url": "https://customer-assets-eiarnc6j.emergentagent.net/job_12145b8e-9780-481f-b432-98049080e6cc/artifacts/zaogaxa6_WhatsApp%20Image%202026-09-09%20at%209.58.21%20PM%20%282%29.jpeg"},
    {"name": "KARE ACM-W", "slug": "acm-w-kare", "display_order": 4, "description": "ACM's committee for women in computing at KARE", "logo_url": "https://customer-assets-eiarnc6j.emergentagent.net/job_12145b8e-9780-481f-b432-98049080e6cc/artifacts/qop5o1eu_WhatsApp%20Image%202026-09-09%20at%209.58.21%20PM%20%281%29.jpeg"},
    {"name": "GDG On Campus · KARE", "slug": "gdg-kare", "display_order": 5, "description": "Google Developer Groups On Campus at KARE", "logo_url": "https://customer-assets-eiarnc6j.emergentagent.net/job_12145b8e-9780-481f-b432-98049080e6cc/artifacts/oje6iuak_image.png"},
]


OFFICIAL_CLUB_LABELS = {
    "gfg-kare": ("GFG Campus Body-KARE", "GeeksforGeeks Campus Body at KARE"),
    "acm-kare": ("KARE ACM Student-Chapter", "Association for Computing Machinery student chapter at KARE"),
    "ieee-eds": ("KARE IEEE Education Society", "IEEE Education Society at KARE"),
    "acm-w-kare": ("KARE ACM-W", "ACM's committee for women in computing at KARE"),
    "gdg-kare": ("Google Developers-KARE", "Google Developers community at KARE"),
}
for club in DEV_CLUBS:
    label = OFFICIAL_CLUB_LABELS.get(club["slug"])
    if label:
        club["name"], club["description"] = label


async def seed_initial_data():
    factory = get_session_factory()
    async with factory() as session:
        hackathon = await session.scalar(select(Hackathon).where(Hackathon.is_active.is_(True)))
        if hackathon is None:
            hackathon = Hackathon(
                name=os.getenv("HACKATHON_NAME", "[HACKATHON_NAME]"),
                slug="euphoria-hackathon",
                tagline=os.getenv("HACKATHON_TAGLINE", "One Hackathon. One Future."),
                description="Euphoria Hackathon is a centralized team-registration platform for the flagship annual hackathon.",
                logo_url=None,
                rules=DEV_RULES,
                eligibility=DEV_ELIGIBILITY,
                instructions=DEV_INSTRUCTIONS,
                sdg_goals=DEV_SDG_GOALS,
                whatsapp_url=os.getenv("HACKATHON_WHATSAPP_URL"),
                is_active=True,
            )
            session.add(hackathon)
            await session.flush()
        else:
            # keep DB in sync with env on every boot (name, tagline, whatsapp)
            hackathon.name = os.getenv("HACKATHON_NAME", hackathon.name)
            hackathon.tagline = os.getenv("HACKATHON_TAGLINE", hackathon.tagline)
            hackathon.whatsapp_url = os.getenv("HACKATHON_WHATSAPP_URL", hackathon.whatsapp_url)
        existing_clubs = (await session.scalars(select(Club).where(Club.hackathon_id == hackathon.id))).all()
        if len(existing_clubs) < 5:
            existing_orders = {c.display_order for c in existing_clubs}
            for club in DEV_CLUBS:
                if club["display_order"] in existing_orders:
                    continue
                session.add(Club(hackathon_id=hackathon.id, name=club["name"], slug=club["slug"], display_order=club["display_order"], description=club["description"], logo_url=club.get("logo_url"), is_visible=True))
        else:
            clubs_by_order = {club.display_order: club for club in existing_clubs}
            for official in DEV_CLUBS:
                club = clubs_by_order.get(official["display_order"])
                if club is None:
                    continue
                stale_partner = "partner" in club.slug.lower() or "collaboration" in club.name.lower()
                official_slot_changed = club.slug != official["slug"]
                official_text_changed = club.name != official["name"] or club.description != official["description"]
                if stale_partner or official_slot_changed or official_text_changed:
                    club.name = official["name"]
                    club.slug = official["slug"]
                    club.description = official["description"]
                    club.logo_url = official.get("logo_url")
                    club.is_visible = True
        admin_email = os.getenv("ADMIN_EMAIL", "admin@euphoria.dev").strip().lower()
        admin_password = os.getenv("ADMIN_PASSWORD", "Admin@12345")
        existing_admin = await session.scalar(select(Admin).where(Admin.email == admin_email))
        if existing_admin is None:
            session.add(Admin(email=admin_email, password_hash=hash_password(admin_password), name=os.getenv("ADMIN_NAME", "Euphoria Admin"), is_active=True))
        await session.commit()


async def prepare_database():
    """Create required tables and seed baseline content for fresh deployments.

    Alembic remains the preferred production migration path, but hosted previews often
    boot against an empty database. This keeps first deployment from accepting traffic
    with no active hackathon row, clubs, or admin account.
    """
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if not is_sqlite():
            await conn.execute(text("ALTER TABLE team_members ADD COLUMN IF NOT EXISTS id_proof_path text"))
            await conn.execute(text("ALTER TABLE team_members ADD COLUMN IF NOT EXISTS id_proof_filename varchar(200)"))
            await conn.execute(text("ALTER TABLE team_members ADD COLUMN IF NOT EXISTS id_proof_content_type varchar(80)"))
    await seed_initial_data()


@asynccontextmanager
async def lifespan(_: FastAPI):
    engine = None
    try:
        await prepare_database()
        engine = get_engine()
    except Exception as exc:
        logger.exception("Database bootstrap failed at startup: %s", exc)
    try:
        init_storage()
    except Exception as exc:  # storage not fatal for boot
        logger.warning("Storage init failed at startup: %s", exc)
    yield
    if engine is not None:
        await engine.dispose()


app = FastAPI(title="Euphoria Hackathon Registration API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(public_router)
app.include_router(admin_router)
app.include_router(uploads_router)


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(_, exc):
    logger.exception("Unhandled database error: %s", exc)
    error = {"code": "DATABASE_UNAVAILABLE", "message": "The registration service is temporarily unavailable. Please try again."}
    return JSONResponse(status_code=503, content={"success": False, "detail": error, "error": error})


@app.get("/")
async def root():
    return {"success": True, "service": "euphoria-registration-api", "health": "/api/health"}


@app.get("/api/health")
async def health():
    return {"success": True, "service": "euphoria-registration-api"}
