"""Schemas for Certificates and Public Verification.
See docs/04-api-specification.md section 8 and docs/01 FR-CRT-1 to 6.
"""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

RevocationReasonType = Literal[
    "fraud", "plagiarism", "evaluation_overturned", "company_error", "other"
]


class PublicVerificationProject(BaseModel):
    title: str
    difficulty: str
    duration_days: int


class PublicVerificationCompany(BaseModel):
    name: str
    approved: bool


class PublicVerificationStudent(BaseModel):
    display_name: str


class PublicVerificationEvaluation(BaseModel):
    summary: str | None = None
    evaluated_at: str | None = None


class PublicVerificationTimeline(BaseModel):
    applied_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None


class PublicVerificationResponse(BaseModel):
    verification_id: str
    status: str
    project: PublicVerificationProject
    company: PublicVerificationCompany
    student: PublicVerificationStudent
    evaluation: PublicVerificationEvaluation
    skills: list[str] = Field(default_factory=list)
    timeline: PublicVerificationTimeline
    checked_at: str
    qr_code_data_uri: str
    disclaimer: str = (
        "This is a ProjectProof verification record. It is not formal employment experience."
    )
    revoked_at: str | None = None
    revocation_reason: str | None = None


class RevocationRequestCreate(BaseModel):
    reason: str
    note: str | None = None


class AdminRevocationCreate(BaseModel):
    reason: RevocationReasonType
    note: str | None = None


class CertificateResponse(BaseModel):
    id: uuid.UUID
    application_id: uuid.UUID
    verification_id: str
    qr_token: str
    status: str
    xp_awarded: int
    project_title: str | None = None
    company_name: str | None = None
    issued_at: datetime
    revoked_at: datetime | None = None
    revocation_reason: str | None = None
