import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=10)
    role: Literal["student", "company", "recruiter"]
    full_name: str | None = None
    organization: str | None = None  # for company/recruiter if provided at signup


class UserRegisterResponse(BaseModel):
    id: uuid.UUID
    role: str
    email_verified: bool


class EmailVerifyRequest(BaseModel):
    token: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserSummary(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    email_verified: bool
    is_active: bool


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserSummary


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=10)


class CurrentUserResponse(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    is_active: bool
    email_verified: bool
    created_at: datetime
    profile: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)
