import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.core.config import is_sqlite
from app.core.database import get_engine, get_session_factory
from app.core.security import hash_password
from app.models import Admin, Base, Club, Hackathon
from app.routes.public import router as public_router
from app.routes.admin import router as admin_router


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
    {"name": "[CLUB_01]", "slug": "club-01", "display_order": 1, "description": "Collaborating partner · placeholder"},
    {"name": "[CLUB_02]", "slug": "club-02", "display_order": 2, "description": "Collaborating partner · placeholder"},
    {"name": "[CLUB_03]", "slug": "club-03", "display_order": 3, "description": "Collaborating partner · placeholder"},
    {"name": "[CLUB_04]", "slug": "club-04", "display_order": 4, "description": "Collaborating partner · placeholder"},
    {"name": "[CLUB_05]", "slug": "club-05", "display_order": 5, "description": "Collaborating partner · placeholder"},
]


async def seed_dev_data():
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
        existing_clubs = (await session.scalars(select(Club).where(Club.hackathon_id == hackathon.id))).all()
        if len(existing_clubs) < 5:
            existing_orders = {c.display_order for c in existing_clubs}
            for club in DEV_CLUBS:
                if club["display_order"] in existing_orders:
                    continue
                session.add(Club(hackathon_id=hackathon.id, name=club["name"], slug=club["slug"], display_order=club["display_order"], description=club["description"], is_visible=True))
        admin_email = os.getenv("ADMIN_EMAIL", "admin@euphoria.dev").strip().lower()
        admin_password = os.getenv("ADMIN_PASSWORD", "Admin@12345")
        existing_admin = await session.scalar(select(Admin).where(Admin.email == admin_email))
        if existing_admin is None:
            session.add(Admin(email=admin_email, password_hash=hash_password(admin_password), name=os.getenv("ADMIN_NAME", "Euphoria Admin"), is_active=True))
        await session.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    engine = get_engine()
    if is_sqlite():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    await seed_dev_data()
    yield
    await engine.dispose()


app = FastAPI(title="Euphoria Hackathon Registration API", version="1.0.0", lifespan=lifespan)

origins_raw = os.getenv("CORS_ORIGINS", "*")
origins = ["*"] if origins_raw.strip() == "*" else [origin.strip() for origin in origins_raw.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True if origins != ["*"] else False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(public_router)
app.include_router(admin_router)


@app.get("/api/health")
async def health():
    return {"success": True, "service": "euphoria-registration-api"}
