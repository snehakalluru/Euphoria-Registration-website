import secrets
import string
from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AccommodationType, CollegeType, Hackathon, Team, TeamMember
from app.schemas.registration import RegistrationSubmission
from app.services.normalization import normalize_email, normalize_identifier, normalize_phone, normalize_team_name


class RegistrationServiceError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass
class CreatedRegistration:
    team: Team
    hackathon: Hackathon


def generate_registration_id() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "EUH26-" + "".join(secrets.choice(alphabet) for _ in range(6))


async def create_registration(session: AsyncSession, payload: RegistrationSubmission) -> CreatedRegistration:
    hackathon_result = await session.execute(select(Hackathon).where(Hackathon.is_active.is_(True)).limit(1))
    hackathon = hackathon_result.scalar_one_or_none()
    if hackathon is None:
        raise RegistrationServiceError("HACKATHON_NOT_CONFIGURED", "The active hackathon is not configured.")

    team_name_normalized = normalize_team_name(payload.team_name)
    member_values = {
        "emails": [normalize_email(str(member.email)) for member in payload.members],
        "phones": [normalize_phone(member.phone) for member in payload.members],
        "registration_numbers": [normalize_identifier(member.registration_number) for member in payload.members],
        "euphoria_ids": [normalize_identifier(member.euphoria_id) for member in payload.members],
    }
    if any(len(values) != len(set(values)) for values in member_values.values()):
        raise RegistrationServiceError("PARTICIPANT_ALREADY_REGISTERED", "A participant appears more than once in this team.")

    duplicate_team = await session.scalar(select(Team.id).where(Team.hackathon_id == hackathon.id, Team.team_name_normalized == team_name_normalized))
    if duplicate_team:
        raise RegistrationServiceError("TEAM_NAME_ALREADY_EXISTS", "This team name is already registered.")

    for field_name, values, code, label in (
        ("email_normalized", member_values["emails"], "EMAIL_ALREADY_REGISTERED", "email"),
        ("phone_normalized", member_values["phones"], "PHONE_ALREADY_REGISTERED", "phone number"),
        ("registration_number_normalized", member_values["registration_numbers"], "REGISTRATION_NUMBER_ALREADY_REGISTERED", "registration number"),
        ("euphoria_id_normalized", member_values["euphoria_ids"], "EUPHORIA_ID_ALREADY_REGISTERED", "Euphoria ID"),
    ):
        existing = await session.scalar(
            select(TeamMember.id)
            .where(TeamMember.hackathon_id == hackathon.id, getattr(TeamMember, field_name).in_(values))
            .limit(1)
        )
        if existing:
            raise RegistrationServiceError(code, f"This {label} is already registered.")

    team = Team(
        id=uuid4(), hackathon_id=hackathon.id, registration_id=generate_registration_id(), team_name=payload.team_name,
        team_name_normalized=team_name_normalized, college_type=CollegeType(payload.college_type), college_name=payload.college_name,
        member_count=len(payload.members), confirmation_accepted=True,
    )
    session.add(team)
    for member in payload.members:
        hostel = member.hostel
        session.add(TeamMember(
            id=uuid4(), team_id=team.id, hackathon_id=hackathon.id, member_number=member.member_number,
            is_team_lead=member.member_number == 1, name=member.name, registration_number=member.registration_number,
            registration_number_normalized=normalize_identifier(member.registration_number), email=str(member.email),
            email_normalized=normalize_email(str(member.email)), phone=member.phone, phone_normalized=normalize_phone(member.phone),
            gender=member.gender, year=member.year, branch=member.branch, section=member.section, euphoria_id=member.euphoria_id,
            euphoria_id_normalized=normalize_identifier(member.euphoria_id), accommodation_type=AccommodationType(member.accommodation_type) if member.accommodation_type else None,
            hostel_name=hostel.hostel_name if hostel else None, room_number=hostel.room_number if hostel else None,
            warden_name=hostel.warden_name if hostel else None, warden_phone=hostel.warden_phone if hostel else None,
        ))
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        detail = str(exc.orig).lower()
        if "team_name" in detail:
            raise RegistrationServiceError("TEAM_NAME_ALREADY_EXISTS", "This team name is already registered.") from exc
        if "euphoria" in detail:
            raise RegistrationServiceError("EUPHORIA_ID_ALREADY_REGISTERED", "This Euphoria ID is already registered.") from exc
        if "email" in detail:
            raise RegistrationServiceError("EMAIL_ALREADY_REGISTERED", "This email is already registered.") from exc
        if "phone" in detail:
            raise RegistrationServiceError("PHONE_ALREADY_REGISTERED", "This phone number is already registered.") from exc
        if "registration" in detail:
            raise RegistrationServiceError("REGISTRATION_NUMBER_ALREADY_REGISTERED", "This registration number is already registered.") from exc
        raise RegistrationServiceError("REGISTRATION_FAILED", "The registration could not be completed.") from exc
    return CreatedRegistration(team=team, hackathon=hackathon)