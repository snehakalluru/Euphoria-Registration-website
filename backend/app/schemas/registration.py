from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class HostelDetails(BaseModel):
    hostel_name: str = Field(min_length=1, max_length=160)
    room_number: str = Field(min_length=1, max_length=60)
    warden_name: str = Field(min_length=1, max_length=160)
    warden_phone: str = Field(min_length=7, max_length=20)


class IdProofRef(BaseModel):
    path: str = Field(min_length=1, max_length=400)
    filename: str = Field(min_length=1, max_length=200)
    content_type: str = Field(min_length=1, max_length=80)


class MemberSubmission(BaseModel):
    member_number: int = Field(ge=1, le=5)
    name: str = Field(min_length=1, max_length=160)
    registration_number: str = Field(min_length=1, max_length=80)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=20)
    gender: str = Field(min_length=1, max_length=40)
    year: str = Field(min_length=1, max_length=40)
    branch: str = Field(min_length=1, max_length=80)
    section: str = Field(min_length=1, max_length=40)
    euphoria_id: str = Field(min_length=1, max_length=80)
    accommodation_type: Literal["day_scholar", "hosteller"] | None = None
    hostel: HostelDetails | None = None
    id_proof: IdProofRef | None = None

    @field_validator("name", "registration_number", "phone", "gender", "year", "branch", "section", "euphoria_id", mode="before")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_accommodation(self):
        if self.accommodation_type == "hosteller" and self.hostel is None:
            raise ValueError("HOSTEL_DETAILS_REQUIRED")
        if self.accommodation_type in (None, "day_scholar") and self.hostel is not None:
            raise ValueError("INVALID_ACCOMMODATION")
        return self


class RegistrationSubmission(BaseModel):
    team_name: str = Field(min_length=1, max_length=160)
    college_type: Literal["internal", "external"]
    college_name: str | None = Field(default=None, max_length=200)
    members: list[MemberSubmission] = Field(min_length=4, max_length=5)
    confirmation_accepted: bool

    @field_validator("team_name", "college_name", mode="before")
    @classmethod
    def strip_optional_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_submission(self):
        if not self.confirmation_accepted:
            raise ValueError("CONFIRMATION_REQUIRED")
        if self.college_type == "external" and not self.college_name:
            raise ValueError("COLLEGE_NAME_REQUIRED")
        if self.college_type == "internal":
            for member in self.members:
                if member.accommodation_type is None:
                    raise ValueError("INVALID_ACCOMMODATION")
        for member in self.members:
            if member.member_number == 1 and member.id_proof is None:
                raise ValueError("TEAM_LEAD_ID_PROOF_REQUIRED")
        numbers = sorted(member.member_number for member in self.members)
        if numbers != list(range(1, len(self.members) + 1)):
            raise ValueError("INVALID_MEMBER_SEQUENCE")
        if len({member.email.lower() for member in self.members}) != len(self.members):
            raise ValueError("EMAIL_ALREADY_REGISTERED")
        if len({member.euphoria_id.strip().upper() for member in self.members}) != len(self.members):
            raise ValueError("EUPHORIA_ID_ALREADY_REGISTERED")
        return self


class PublicRegistrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    registration_id: str
    team_name: str
    member_count: int
    submitted_at: datetime
    whatsapp_url: str | None = None


class RegistrationCreatedResponse(BaseModel):
    success: bool = True
    data: PublicRegistrationResponse