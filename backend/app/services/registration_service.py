import secrets
import string
from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import DBAPIError, IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AccommodationType, CollegeType, Hackathon, RegistrationStatus, Team, TeamMember
from app.schemas.registration import RegistrationSubmission
from app.services.normalization import normalize_email, normalize_identifier, normalize_phone, normalize_team_name


class RegistrationServiceError(Exception):
    def __init__(self, code: str, message: str, field: str | None = None, member_number: int | None = None):
        self.code = code
        self.message = message
        self.field = field
        self.member_number = member_number
        super().__init__(message)


@dataclass
class CreatedRegistration:
    team: Team
    hackathon: Hackathon


def generate_registration_id() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "EUH26-" + "".join(secrets.choice(alphabet) for _ in range(6))


CONSTRAINT_ERRORS = {
    "uq_teams_hackathon_team_name": ("DUPLICATE_TEAM", "Team name already exists. Please choose a different team name."),
    "uq_team_members_hackathon_euphoria": ("DUPLICATE_EUPHORIA_ID", "This Euphoria ID has already been registered."),
    "uq_team_members_hackathon_email": ("DUPLICATE_EMAIL", "This email has already been registered."),
    "uq_team_members_hackathon_phone": ("DUPLICATE_PHONE", "This phone number has already been registered."),
    "uq_team_members_hackathon_registration": ("DUPLICATE_REGISTRATION_NUMBER", "This registration/roll number is already registered."),
    "uq_team_members_team_member_number": ("DUPLICATE_MEMBER_POSITION", "This team member position is duplicated."),
}
REGISTRATION_ID_CONSTRAINTS = {"teams_registration_id_key", "uq_teams_registration_id"}
SQLITE_UNIQUE_ERRORS = {
    ("teams.hackathon_id", "teams.team_name_normalized"): "uq_teams_hackathon_team_name",
    ("team_members.hackathon_id", "team_members.euphoria_id_normalized"): "uq_team_members_hackathon_euphoria",
    ("team_members.hackathon_id", "team_members.email_normalized"): "uq_team_members_hackathon_email",
    ("team_members.hackathon_id", "team_members.phone_normalized"): "uq_team_members_hackathon_phone",
    ("team_members.hackathon_id", "team_members.registration_number_normalized"): "uq_team_members_hackathon_registration",
    ("team_members.team_id", "team_members.member_number"): "uq_team_members_team_member_number",
    ("teams.registration_id",): "uq_teams_registration_id",
}


def _constraint_name(exc: IntegrityError) -> str:
    details = []
    current = exc.orig
    seen = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        details.append(str(current))
        constraint = getattr(getattr(current, "diag", None), "constraint_name", None)
        if constraint:
            return constraint
        constraint = getattr(current, "constraint_name", None)
        if constraint:
            return constraint
        current = getattr(current, "__cause__", None) or getattr(current, "__context__", None)
    details.append(str(exc))
    detail = " ".join(details).lower()
    for name in (*CONSTRAINT_ERRORS.keys(), *REGISTRATION_ID_CONSTRAINTS):
        if name.lower() in detail:
            return name
    for columns, name in SQLITE_UNIQUE_ERRORS.items():
        if all(column.lower() in detail for column in columns):
            return name
    return ""


def _duplicate_error(code: str, message: str, field: str | None = None, member_number: int | None = None) -> RegistrationServiceError:
    return RegistrationServiceError(code, message, field=field, member_number=member_number)


async def check_registration_availability(session: AsyncSession, field_type: str, value: str) -> bool:
    hackathon = await session.scalar(select(Hackathon).where(Hackathon.is_active.is_(True)).limit(1))
    if hackathon is None:
        raise RegistrationServiceError("HACKATHON_NOT_CONFIGURED", "The active hackathon is not configured.")

    check_value = value.strip()
    if not check_value:
        raise RegistrationServiceError("INVALID_AVAILABILITY_CHECK", "A value is required.")

    if field_type == "team_name":
        normalized = normalize_team_name(check_value)
        existing = await session.scalar(
            select(Team.id).where(Team.hackathon_id == hackathon.id, Team.team_name_normalized == normalized).limit(1)
        )
    elif field_type == "email":
        normalized = normalize_email(check_value)
        existing = await session.scalar(
            select(TeamMember.id).where(TeamMember.hackathon_id == hackathon.id, TeamMember.email_normalized == normalized).limit(1)
        )
    elif field_type == "phone":
        normalized = normalize_phone(check_value)
        if not normalized.isdigit() or len(normalized) != 10:
            raise RegistrationServiceError("INVALID_PHONE", "Phone number must contain exactly 10 digits.")
        existing = await session.scalar(
            select(TeamMember.id).where(TeamMember.hackathon_id == hackathon.id, TeamMember.phone_normalized == normalized).limit(1)
        )
    elif field_type == "registration_number":
        normalized = normalize_identifier(check_value)
        existing = await session.scalar(
            select(TeamMember.id).where(TeamMember.hackathon_id == hackathon.id, TeamMember.registration_number_normalized == normalized).limit(1)
        )
    else:
        raise RegistrationServiceError("INVALID_AVAILABILITY_CHECK", "Unsupported availability check type.")
    return existing is None


async def _rollback_safely(session: AsyncSession) -> None:
    if session.in_transaction():
        try:
            await session.rollback()
        except Exception:
            pass


async def create_registration(session: AsyncSession, payload: RegistrationSubmission) -> CreatedRegistration:
    team_name_normalized = normalize_team_name(payload.team_name)
    member_values = {
        "emails": [normalize_email(str(member.email)) for member in payload.members],
        "phones": [normalize_phone(member.phone) for member in payload.members],
        "registration_numbers": [normalize_identifier(member.registration_number) for member in payload.members],
        "euphoria_ids": [normalize_identifier(member.euphoria_id) for member in payload.members],
    }
    if any(len(values) != len(set(values)) for values in member_values.values()):
        raise RegistrationServiceError("PARTICIPANT_ALREADY_REGISTERED", "A participant appears more than once in this team.")

    last_registration_collision = None
    for _ in range(3):
        try:
            transaction = await session.begin()
            hackathon_result = await session.execute(select(Hackathon).where(Hackathon.is_active.is_(True)).limit(1))
            hackathon = hackathon_result.scalar_one_or_none()
            if hackathon is None:
                raise RegistrationServiceError("HACKATHON_NOT_CONFIGURED", "The active hackathon is not configured.")

            duplicate_team = await session.scalar(select(Team.id).where(Team.hackathon_id == hackathon.id, Team.team_name_normalized == team_name_normalized))
            if duplicate_team:
                raise _duplicate_error("DUPLICATE_TEAM", "Team name already exists. Please choose a different team name.", field="team_name")

            for field_name, values, code, message in (
                ("email_normalized", member_values["emails"], "DUPLICATE_EMAIL", "This email has already been registered."),
                ("phone_normalized", member_values["phones"], "DUPLICATE_PHONE", "This phone number has already been registered."),
                ("registration_number_normalized", member_values["registration_numbers"], "DUPLICATE_REGISTRATION_NUMBER", "This registration/roll number is already registered."),
                ("euphoria_id_normalized", member_values["euphoria_ids"], "DUPLICATE_EUPHORIA_ID", "This Euphoria ID has already been registered."),
            ):
                for value, member in zip(values, payload.members):
                    existing = await session.scalar(
                        select(TeamMember.id)
                        .where(TeamMember.hackathon_id == hackathon.id, getattr(TeamMember, field_name) == value)
                        .limit(1)
                    )
                    if existing:
                        field = {
                            "email_normalized": "email",
                            "phone_normalized": "phone",
                            "registration_number_normalized": "registration_number",
                            "euphoria_id_normalized": "euphoria_id",
                        }.get(field_name)
                        raise _duplicate_error(code, message, field=field, member_number=member.member_number)

            team = Team(
                id=uuid4(), hackathon_id=hackathon.id, registration_id=generate_registration_id(), team_name=payload.team_name,
                team_name_normalized=team_name_normalized, college_type=CollegeType(payload.college_type), college_name=payload.college_name,
                member_count=len(payload.members), confirmation_accepted=payload.confirmation_accepted, status=RegistrationStatus.SUBMITTED,
            )
            session.add(team)
            for member in payload.members:
                hostel = member.hostel
                proof = member.id_proof
                session.add(TeamMember(
                    id=uuid4(), team_id=team.id, hackathon_id=hackathon.id, member_number=member.member_number,
                    is_team_lead=member.member_number == 1, name=member.name, registration_number=member.registration_number,
                    registration_number_normalized=normalize_identifier(member.registration_number), email=str(member.email),
                    email_normalized=normalize_email(str(member.email)), phone=member.phone, phone_normalized=normalize_phone(member.phone),
                    gender=member.gender, year=member.year, branch=member.branch, section=member.section, euphoria_id=member.euphoria_id,
                    euphoria_id_normalized=normalize_identifier(member.euphoria_id), accommodation_type=AccommodationType(member.accommodation_type) if member.accommodation_type else None,
                    hostel_name=hostel.hostel_name if hostel else None, room_number=hostel.room_number if hostel else None,
                    warden_name=hostel.warden_name if hostel else None, warden_phone=hostel.warden_phone if hostel else None,
                    id_proof_path=proof.path if proof else None,
                    id_proof_filename=proof.filename if proof else None,
                    id_proof_content_type=proof.content_type if proof else None,
                ))
            await session.flush()
            await transaction.commit()
            return CreatedRegistration(team=team, hackathon=hackathon)
        except IntegrityError as exc:
            constraint = _constraint_name(exc)
            await _rollback_safely(session)
            if constraint in REGISTRATION_ID_CONSTRAINTS:
                last_registration_collision = exc
                continue
            code, message = CONSTRAINT_ERRORS.get(constraint, ("REGISTRATION_FAILED", "The registration could not be completed."))
            field = {
                "DUPLICATE_TEAM": "team_name",
                "DUPLICATE_EMAIL": "email",
                "DUPLICATE_PHONE": "phone",
                "DUPLICATE_REGISTRATION_NUMBER": "registration_number",
                "DUPLICATE_EUPHORIA_ID": "euphoria_id",
            }.get(code)
            raise RegistrationServiceError(code, message, field=field) from exc
        except RegistrationServiceError:
            await _rollback_safely(session)
            raise
        except DBAPIError as exc:
            await _rollback_safely(session)
            raise RegistrationServiceError("DATABASE_UNAVAILABLE", "The registration service is temporarily unavailable. Please try again.") from exc
        except (SQLAlchemyError, OSError, RuntimeError) as exc:
            await _rollback_safely(session)
            raise RegistrationServiceError("DATABASE_UNAVAILABLE", "The registration service is temporarily unavailable. Please try again.") from exc

    raise RegistrationServiceError("REGISTRATION_FAILED", "The registration could not be completed.") from last_registration_collision
