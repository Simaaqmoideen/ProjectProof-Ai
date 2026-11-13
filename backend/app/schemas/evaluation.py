"""Pydantic schemas for deliverables, evaluations, and appeals."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CreateSubmissionRequest(BaseModel):
    repo_url: str | None = Field(None, max_length=500)
    file_key: str | None = Field(None, max_length=500)
    notes: str | None = Field(None, max_length=3000)

    @model_validator(mode="after")
    def check_at_least_one_deliverable(self):
        if not self.repo_url and not self.file_key:
            raise ValueError("At least one of repo_url or file_key must be provided")
        return self


class SubmissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: uuid.UUID
    version: int
    repo_url: str | None = None
    file_key: str | None = None
    notes: str | None = None
    similarity_score: float | None = None
    similarity_report: dict | None = None
    ai_prereview: dict | None = None
    submitted_at: datetime


class CreateEvaluationRequest(BaseModel):
    rubric_scores: dict[str, int] | None = None
    overall_score: int = Field(..., ge=0, le=100)
    feedback: str = Field(..., min_length=10, max_length=5000)
    public_summary: str | None = Field(None, max_length=1000)
    decision: Literal["approved", "changes_requested", "rejected"]
    used_ai_draft: bool = False


class CertificateSummary(BaseModel):
    id: uuid.UUID | None = None
    verification_id: str
    qr_token: str | None = None
    xp_awarded: int
    status: str


class EvaluationDecisionResponse(BaseModel):
    evaluation_id: uuid.UUID
    application_status: str
    decision: str
    certificate: CertificateSummary | None = None


class EvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    submission_id: uuid.UUID
    reviewer_id: uuid.UUID
    rubric_scores: dict | None = None
    overall_score: int
    feedback: str
    public_summary: str | None = None
    used_ai_draft: bool = False
    decision: str
    evaluated_at: datetime


class CreateAppealRequest(BaseModel):
    reason: str = Field(..., min_length=10, max_length=3000)


class AppealResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    evaluation_id: uuid.UUID
    student_id: uuid.UUID
    reason: str
    status: str
    resolved_by: uuid.UUID | None = None
    resolution_note: str | None = None
    created_at: datetime
    resolved_at: datetime | None = None
