from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import Club, Hackathon, Team
from app.schemas.registration import PublicRegistrationResponse, RegistrationCreatedResponse, RegistrationSubmission
from app.services.registration_service import RegistrationServiceError, create_registration

router = APIRouter(prefix="/api")


@router.get("/hackathon")
async def get_hackathon(session: AsyncSession = Depends(get_db)):
    hackathon = await session.scalar(select(Hackathon).where(Hackathon.is_active.is_(True)).limit(1))
    if hackathon is None:
        raise HTTPException(status_code=404, detail={"code": "HACKATHON_NOT_CONFIGURED", "message": "Hackathon content is not configured."})
    return {"success": True, "data": {"name": hackathon.name, "tagline": hackathon.tagline, "description": hackathon.description, "logoUrl": hackathon.logo_url, "rules": hackathon.rules or [], "eligibility": hackathon.eligibility or [], "instructions": hackathon.instructions or [], "sdgGoals": hackathon.sdg_goals or [], "whatsappUrl": hackathon.whatsapp_url}}


@router.get("/clubs")
async def get_clubs(session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Club).where(Club.is_visible.is_(True)).order_by(Club.display_order))
    clubs = result.scalars().all()
    if len(clubs) != 5:
        raise HTTPException(status_code=503, detail={"code": "CLUB_CONFIGURATION_INVALID", "message": "Exactly five collaborating clubs must be configured."})
    return {"success": True, "data": [{"name": club.name, "slug": club.slug, "logoUrl": club.logo_url, "description": club.description, "displayOrder": club.display_order} for club in clubs]}


@router.post("/registrations", response_model=RegistrationCreatedResponse, status_code=status.HTTP_201_CREATED)
async def post_registration(payload: RegistrationSubmission, session: AsyncSession = Depends(get_db)):
    try:
        created = await create_registration(session, payload)
    except RegistrationServiceError as exc:
        raise HTTPException(status_code=409 if exc.code.endswith(("EXISTS", "REGISTERED")) else 400, detail={"code": exc.code, "message": exc.message}) from exc
    public = PublicRegistrationResponse(registration_id=created.team.registration_id, team_name=created.team.team_name, member_count=created.team.member_count, submitted_at=created.team.submitted_at, whatsapp_url=created.hackathon.whatsapp_url)
    return RegistrationCreatedResponse(data=public)


@router.get("/registrations/{registration_id}", response_model=RegistrationCreatedResponse)
async def get_registration(registration_id: str, session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Team, Hackathon.whatsapp_url).join(Hackathon, Hackathon.id == Team.hackathon_id).where(Team.registration_id == registration_id))
    row = result.first()
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "REGISTRATION_NOT_FOUND", "message": "Registration not found."})
    team, whatsapp_url = row
    public = PublicRegistrationResponse(registration_id=team.registration_id, team_name=team.team_name, member_count=team.member_count, submitted_at=team.submitted_at, whatsapp_url=whatsapp_url)
    return RegistrationCreatedResponse(data=public)