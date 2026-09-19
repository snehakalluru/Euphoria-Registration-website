import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum as SqlEnum, ForeignKey, ForeignKeyConstraint, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class CollegeType(str, Enum):
    INTERNAL = "internal"
    EXTERNAL = "external"


class RegistrationStatus(str, Enum):
    SUBMITTED = "submitted"


class AccommodationType(str, Enum):
    DAY_SCHOLAR = "day_scholar"
    HOSTELLER = "hosteller"


class AdminRole(str, Enum):
    ADMIN = "admin"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class Hackathon(TimestampMixin, Base):
    __tablename__ = "hackathons"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    tagline: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    logo_url: Mapped[str | None] = mapped_column(Text)
    rules: Mapped[dict | list | None] = mapped_column(JSON)
    eligibility: Mapped[dict | list | None] = mapped_column(JSON)
    instructions: Mapped[dict | list | None] = mapped_column(JSON)
    sdg_goals: Mapped[list | None] = mapped_column(JSON)
    whatsapp_url: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    clubs: Mapped[list["Club"]] = relationship(back_populates="hackathon", cascade="all, delete-orphan")
    teams: Mapped[list["Team"]] = relationship(back_populates="hackathon", cascade="all, delete-orphan")


class Club(TimestampMixin, Base):
    __tablename__ = "clubs"
    __table_args__ = (UniqueConstraint("hackathon_id", "slug", name="uq_clubs_hackathon_slug"), UniqueConstraint("hackathon_id", "display_order", name="uq_clubs_hackathon_display_order"))
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hackathon_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hackathons.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    logo_url: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    faculty_in_charge: Mapped[str | None] = mapped_column(String(160))
    student_in_charge: Mapped[str | None] = mapped_column(String(160))
    contact_details: Mapped[dict | None] = mapped_column(JSON)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    hackathon: Mapped[Hackathon] = relationship(back_populates="clubs")


class Team(TimestampMixin, Base):
    __tablename__ = "teams"
    __table_args__ = (
        UniqueConstraint("id", "hackathon_id", name="uq_teams_id_hackathon_id"),
        UniqueConstraint("hackathon_id", "team_name_normalized", name="uq_teams_hackathon_team_name"),
        CheckConstraint("member_count BETWEEN 4 AND 5", name="ck_teams_member_count"),
        CheckConstraint("confirmation_accepted IS TRUE", name="ck_teams_confirmation_accepted"),
        CheckConstraint("(college_type = 'external' AND NULLIF(TRIM(college_name), '') IS NOT NULL) OR college_type = 'internal'", name="ck_teams_college_rules"),
        Index("ix_teams_submitted_at", "submitted_at"), Index("ix_teams_college_type", "college_type"), Index("ix_teams_member_count", "member_count"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hackathon_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hackathons.id", ondelete="RESTRICT"), nullable=False)
    registration_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    team_name: Mapped[str] = mapped_column(String(160), nullable=False)
    team_name_normalized: Mapped[str] = mapped_column(String(160), nullable=False)
    college_type: Mapped[CollegeType] = mapped_column(SqlEnum(CollegeType, name="college_type"), nullable=False)
    college_name: Mapped[str | None] = mapped_column(String(200))
    member_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[RegistrationStatus] = mapped_column(SqlEnum(RegistrationStatus, name="registration_status"), default=RegistrationStatus.SUBMITTED, nullable=False)
    confirmation_accepted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    hackathon: Mapped[Hackathon] = relationship(back_populates="teams")
    members: Mapped[list["TeamMember"]] = relationship(back_populates="team", cascade="all, delete-orphan", order_by="TeamMember.member_number")


class TeamMember(TimestampMixin, Base):
    __tablename__ = "team_members"
    __table_args__ = (
        ForeignKeyConstraint(["team_id", "hackathon_id"], ["teams.id", "teams.hackathon_id"], ondelete="CASCADE", name="fk_team_members_team_hackathon"),
        UniqueConstraint("team_id", "member_number", name="uq_team_members_team_member_number"), UniqueConstraint("hackathon_id", "euphoria_id_normalized", name="uq_team_members_hackathon_euphoria"), UniqueConstraint("hackathon_id", "email_normalized", name="uq_team_members_hackathon_email"), UniqueConstraint("hackathon_id", "phone_normalized", name="uq_team_members_hackathon_phone"), UniqueConstraint("hackathon_id", "registration_number_normalized", name="uq_team_members_hackathon_registration"),
        CheckConstraint("member_number BETWEEN 1 AND 5", name="ck_team_members_member_number"), CheckConstraint("(member_number = 1 AND is_team_lead IS TRUE) OR (member_number > 1 AND is_team_lead IS FALSE)", name="ck_team_members_lead_position"),
        CheckConstraint("(accommodation_type IS NULL AND hostel_name IS NULL AND room_number IS NULL AND warden_name IS NULL AND warden_phone IS NULL) OR (accommodation_type = 'day_scholar' AND hostel_name IS NULL AND room_number IS NULL AND warden_name IS NULL AND warden_phone IS NULL) OR (accommodation_type = 'hosteller' AND NULLIF(TRIM(hostel_name), '') IS NOT NULL AND NULLIF(TRIM(room_number), '') IS NOT NULL AND NULLIF(TRIM(warden_name), '') IS NOT NULL AND NULLIF(TRIM(warden_phone), '') IS NOT NULL)", name="ck_team_members_accommodation_rules"),
        Index("ix_team_members_name", "name"), Index("ix_team_members_email_normalized", "email_normalized"), Index("ix_team_members_phone_normalized", "phone_normalized"), Index("ix_team_members_euphoria_id_normalized", "euphoria_id_normalized"), Index("ix_team_members_registration_number_normalized", "registration_number_normalized"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    hackathon_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    member_number: Mapped[int] = mapped_column(Integer, nullable=False)
    is_team_lead: Mapped[bool] = mapped_column(Boolean, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    registration_number: Mapped[str] = mapped_column(String(80), nullable=False)
    registration_number_normalized: Mapped[str] = mapped_column(String(80), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    email_normalized: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    phone_normalized: Mapped[str] = mapped_column(String(20), nullable=False)
    gender: Mapped[str] = mapped_column(String(40), nullable=False)
    year: Mapped[str] = mapped_column(String(40), nullable=False)
    branch: Mapped[str] = mapped_column(String(80), nullable=False)
    section: Mapped[str] = mapped_column(String(40), nullable=False)
    euphoria_id: Mapped[str] = mapped_column(String(80), nullable=False)
    euphoria_id_normalized: Mapped[str] = mapped_column(String(80), nullable=False)
    accommodation_type: Mapped[AccommodationType | None] = mapped_column(SqlEnum(AccommodationType, name="accommodation_type"))
    hostel_name: Mapped[str | None] = mapped_column(String(160))
    room_number: Mapped[str | None] = mapped_column(String(60))
    warden_name: Mapped[str | None] = mapped_column(String(160))
    warden_phone: Mapped[str | None] = mapped_column(String(20))
    team: Mapped[Team] = relationship(back_populates="members")


class Admin(TimestampMixin, Base):
    __tablename__ = "admins"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str | None] = mapped_column(String(120))
    role: Mapped[AdminRole] = mapped_column(SqlEnum(AdminRole, name="admin_role"), default=AdminRole.ADMIN, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))