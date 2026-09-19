from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import Club, Hackathon, Team
from app.schemas.registration import PublicRegistrationResponse, RegistrationCreatedResponse, RegistrationSubmission
from app.services.registration_service import RegistrationServiceError, check_registration_availability, create_registration
from app.services.storage import StorageError, get_object

router = APIRouter(prefix="/api")


def _logo_url(path: str | None) -> str | None:
    if not path:
        return None
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return f"/api/media/{path}"


@router.get("/hackathon")
async def get_hackathon(session: AsyncSession = Depends(get_db)):
    import os
    hackathon = await session.scalar(select(Hackathon).where(Hackathon.is_active.is_(True)).limit(1))
    if hackathon is None:
        raise HTTPException(status_code=404, detail={"code": "HACKATHON_NOT_CONFIGURED", "message": "Hackathon content is not configured."})
    return {"success": True, "data": {
        "name": hackathon.name,
        "tagline": hackathon.tagline,
        "description": hackathon.description,
        "logoUrl": _logo_url(hackathon.logo_url),
        "rules": hackathon.rules or [],
        "eligibility": hackathon.eligibility or [],
        "instructions": hackathon.instructions or [],
        "sdgGoals": hackathon.sdg_goals or [],
        "whatsappUrl": hackathon.whatsapp_url,
        "startsAt": os.getenv("HACKATHON_START_AT"),
        "endsAt": os.getenv("HACKATHON_END_AT"),
        "venue": os.getenv("HACKATHON_VENUE"),
        "mode": os.getenv("HACKATHON_MODE"),
        "fee": os.getenv("HACKATHON_FEE"),
        "prizePool": os.getenv("HACKATHON_PRIZE_POOL"),
        "sponsoredBy": os.getenv("HACKATHON_SPONSORED_BY"),
        "host": os.getenv("HACKATHON_HOST"),
    }}


@router.get("/clubs")
async def get_clubs(session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Club).where(Club.is_visible.is_(True)).order_by(Club.display_order))
    clubs = result.scalars().all()
    if len(clubs) != 5:
        raise HTTPException(status_code=503, detail={"code": "CLUB_CONFIGURATION_INVALID", "message": "Exactly five collaborating clubs must be configured."})
    return {"success": True, "data": [{"name": club.name, "slug": club.slug, "logoUrl": _logo_url(club.logo_url), "description": club.description, "displayOrder": club.display_order, "facultyInCharge": club.faculty_in_charge, "studentInCharge": club.student_in_charge} for club in clubs]}


@router.get("/media/{path:path}")
async def public_media(path: str):
    """Public proxy for logo/branding assets. Only serves image content-types."""
    try:
        data, ctype = get_object(path)
    except StorageError:
        raise HTTPException(status_code=404, detail={"code": "MEDIA_NOT_FOUND", "message": "Media not found."})
    if not ctype.startswith("image/"):
        raise HTTPException(status_code=403, detail={"code": "MEDIA_FORBIDDEN", "message": "Non-image files are not publicly accessible."})
    return Response(content=data, media_type=ctype, headers={"Cache-Control": "public, max-age=86400"})


@router.post("/registrations", response_model=RegistrationCreatedResponse, status_code=status.HTTP_201_CREATED)
async def post_registration(payload: RegistrationSubmission, session: AsyncSession = Depends(get_db)):
    try:
        created = await create_registration(session, payload)
    except RegistrationServiceError as exc:
        http_status = status.HTTP_409_CONFLICT if exc.code.startswith("DUPLICATE_") else status.HTTP_503_SERVICE_UNAVAILABLE if exc.code == "DATABASE_UNAVAILABLE" else status.HTTP_400_BAD_REQUEST
        error = {"code": exc.code, "message": exc.message}
        if exc.field:
            error["field"] = exc.field
        if exc.member_number:
            error["memberNumber"] = exc.member_number
        return JSONResponse(status_code=http_status, content={"error": error, "detail": error})
    public = PublicRegistrationResponse(registration_id=created.team.registration_id, team_name=created.team.team_name, member_count=created.team.member_count, submitted_at=created.team.submitted_at, whatsapp_url=created.hackathon.whatsapp_url)
    return RegistrationCreatedResponse(data=public)


@router.get("/registrations/check-availability")
async def check_availability(
    type: str = Query(..., pattern="^(team_name|email|phone|registration_number)$"),
    value: str = Query(..., min_length=1, max_length=255),
    session: AsyncSession = Depends(get_db),
):
    try:
        available = await check_registration_availability(session, type, value)
    except RegistrationServiceError as exc:
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE if exc.code == "DATABASE_UNAVAILABLE" else status.HTTP_400_BAD_REQUEST
        error = {"code": exc.code, "message": exc.message}
        return JSONResponse(status_code=http_status, content={"success": False, "error": error, "detail": error})
    except SQLAlchemyError:
        error = {"code": "DATABASE_UNAVAILABLE", "message": "The registration service is temporarily unavailable. Please try again."}
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"success": False, "error": error, "detail": error})
    return {"success": True, "available": available}


@router.get("/registrations/{registration_id}", response_model=RegistrationCreatedResponse)
async def get_registration(registration_id: str, session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Team, Hackathon.whatsapp_url).join(Hackathon, Hackathon.id == Team.hackathon_id).where(Team.registration_id == registration_id))
    row = result.first()
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "REGISTRATION_NOT_FOUND", "message": "Registration not found."})
    team, whatsapp_url = row
    public = PublicRegistrationResponse(registration_id=team.registration_id, team_name=team.team_name, member_count=team.member_count, submitted_at=team.submitted_at, whatsapp_url=whatsapp_url)
    return RegistrationCreatedResponse(data=public)
