import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import create_access_token, get_current_admin, verify_password
from app.models import Admin, Team, TeamMember
from app.schemas.admin import AdminLoginRequest, AdminLoginResponse

router = APIRouter(prefix="/api/admin")


async def admin_dependency(request: Request, session: AsyncSession = Depends(get_db)) -> Admin:
    return await get_current_admin(request, session)


@router.post("/auth/login", response_model=AdminLoginResponse)
async def login(payload: AdminLoginRequest, response: Response, session: AsyncSession = Depends(get_db)):
    admin = await session.scalar(select(Admin).where(func.lower(Admin.email) == payload.email.lower(), Admin.is_active.is_(True)))
    if admin is None or not verify_password(payload.password, admin.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"code": "INVALID_CREDENTIALS", "message": "Invalid email or password"})
    admin.last_login_at = datetime.now(timezone.utc)
    await session.commit()
    token = create_access_token(admin)
    response.set_cookie("access_token", token, httponly=True, secure=True, samesite="lax", max_age=3600 * 4, path="/")
    return AdminLoginResponse(access_token=token)


@router.get("/me")
async def me(admin: Admin = Depends(admin_dependency)):
    return {"success": True, "data": {"email": admin.email, "name": admin.name, "role": admin.role.value}}


@router.get("/statistics")
async def statistics(_: Admin = Depends(admin_dependency), session: AsyncSession = Depends(get_db)):
    total_teams = await session.scalar(select(func.count(Team.id))) or 0
    total_participants = await session.scalar(select(func.count(TeamMember.id))) or 0
    internal = await session.scalar(select(func.count(Team.id)).where(Team.college_type == "internal")) or 0
    external = await session.scalar(select(func.count(Team.id)).where(Team.college_type == "external")) or 0
    four_member = await session.scalar(select(func.count(Team.id)).where(Team.member_count == 4)) or 0
    five_member = await session.scalar(select(func.count(Team.id)).where(Team.member_count == 5)) or 0
    hostellers = await session.scalar(select(func.count(TeamMember.id)).where(TeamMember.accommodation_type == "hosteller")) or 0
    day_scholars = await session.scalar(select(func.count(TeamMember.id)).where(TeamMember.accommodation_type == "day_scholar")) or 0
    return {"success": True, "data": {"totalTeams": total_teams, "totalParticipants": total_participants, "internalTeams": internal, "externalTeams": external, "fourMemberTeams": four_member, "fiveMemberTeams": five_member, "hostellers": hostellers, "dayScholars": day_scholars}}


def _member_to_dict(m: TeamMember) -> dict:
    return {"memberNumber": m.member_number, "isTeamLead": m.is_team_lead, "name": m.name, "registrationNumber": m.registration_number, "email": m.email, "phone": m.phone, "gender": m.gender, "year": m.year, "branch": m.branch, "section": m.section, "euphoriaId": m.euphoria_id, "accommodationType": m.accommodation_type.value if m.accommodation_type else None, "hostelName": m.hostel_name, "roomNumber": m.room_number, "wardenName": m.warden_name, "wardenPhone": m.warden_phone}


@router.get("/registrations")
async def registrations(
    search: str | None = None,
    college_type: str | None = None,
    team_size: int | None = Query(default=None, ge=4, le=5),
    accommodation: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    _: Admin = Depends(admin_dependency),
    session: AsyncSession = Depends(get_db),
):
    query = select(Team).order_by(Team.submitted_at.desc())
    if college_type in ("internal", "external"):
        query = query.where(Team.college_type == college_type)
    if team_size:
        query = query.where(Team.member_count == team_size)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.join(TeamMember, TeamMember.team_id == Team.id, isouter=True).where(or_(Team.registration_id.ilike(pattern), Team.team_name.ilike(pattern), TeamMember.name.ilike(pattern), TeamMember.email.ilike(pattern), TeamMember.phone.ilike(pattern), TeamMember.euphoria_id.ilike(pattern), TeamMember.registration_number.ilike(pattern))).distinct()
    if accommodation in ("hosteller", "day_scholar"):
        query = query.join(TeamMember, TeamMember.team_id == Team.id).where(TeamMember.accommodation_type == accommodation).distinct()
    count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query) or 0
    result = await session.execute(query.offset((page - 1) * page_size).limit(page_size))
    return {"success": True, "data": [{"registrationId": team.registration_id, "teamName": team.team_name, "collegeType": team.college_type.value, "collegeName": team.college_name, "memberCount": team.member_count, "submittedAt": team.submitted_at} for team in result.scalars().all()], "pagination": {"page": page, "pageSize": page_size, "total": total}}


@router.get("/registrations/export")
async def export_registrations(_: Admin = Depends(admin_dependency), session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Team).order_by(Team.submitted_at.desc()).options(selectinload(Team.members)))
    teams = result.scalars().all()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Registration ID", "Team Name", "College Type", "College Name", "Member Number", "Team Lead", "Member Name", "Registration Number", "Email", "Phone", "Gender", "Year", "Branch", "Section", "Euphoria ID", "Accommodation", "Hostel Name", "Room Number", "Warden Name", "Warden Phone", "Submitted At", "Status"])
    for team in teams:
        for m in team.members:
            writer.writerow([team.registration_id, team.team_name, team.college_type.value, team.college_name or "", m.member_number, "Yes" if m.is_team_lead else "No", m.name, m.registration_number, m.email, m.phone, m.gender, m.year, m.branch, m.section, m.euphoria_id, m.accommodation_type.value if m.accommodation_type else "", m.hostel_name or "", m.room_number or "", m.warden_name or "", m.warden_phone or "", team.submitted_at.isoformat(), team.status.value])
    buffer.seek(0)
    filename = f"euphoria-registrations-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.csv"
    return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/registrations/{registration_id}")
async def registration_detail(registration_id: str, _: Admin = Depends(admin_dependency), session: AsyncSession = Depends(get_db)):
    team = await session.scalar(select(Team).where(Team.registration_id == registration_id).options(selectinload(Team.members)))
    if team is None:
        raise HTTPException(status_code=404, detail={"code": "REGISTRATION_NOT_FOUND", "message": "Registration not found."})
    return {"success": True, "data": {"registrationId": team.registration_id, "teamName": team.team_name, "collegeType": team.college_type.value, "collegeName": team.college_name, "memberCount": team.member_count, "submittedAt": team.submitted_at, "status": team.status.value, "members": [_member_to_dict(m) for m in team.members]}}
