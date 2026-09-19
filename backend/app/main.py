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
from app.routes.uploads import router as uploads_router
from app.services.storage import init_storage


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
        admin_email = os.getenv("ADMIN_EMAIL", "admin@euphoria.dev").strip().lower()
        admin_password = os.getenv("ADMIN_PASSWORD", "Admin@12345")
        existing_admin = await session.scalar(select(Admin).where(Admin.email == admin_email))
        if existing_admin is None:
            session.add(Admin(email=admin_email, password_hash=hash_password(admin_password), name=os.getenv("ADMIN_NAME", "Euphoria Admin"), is_active=True))
        await session.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_dev_data()
    try:
        init_storage()
    except Exception as exc:  # storage not fatal for boot
        import logging
        logging.getLogger(__name__).warning("Storage init failed at startup: %s", exc)
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
app.include_router(uploads_router)


@app.get("/api/health")
async def health():
    return {"success": True, "service": "euphoria-registration-api"}
