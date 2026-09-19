from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class AdminLoginResponse(BaseModel):
    success: bool = True
    access_token: str
    token_type: str = "bearer"


class AdminRegistrationQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=100)
    search: str | None = None
    college_type: str | None = None
    team_size: int | None = Field(default=None, ge=4, le=5)
    submitted_from: datetime | None = None
    submitted_to: datetime | None = None