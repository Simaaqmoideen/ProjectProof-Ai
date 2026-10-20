import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AutomatedCompanyChecks(BaseModel):
    domain_matches_website: bool
    document_uploaded: bool
    domain_conflict: bool  # True if another active (not rejected) company already has this domain
    is_free_email: bool


class CompanyApprovalItem(BaseModel):
    id: uuid.UUID
    name: str
    website: str | None = None
    email_domain: str | None = None
    description: str | None = None
    registration_doc_key: str | None = None
    status: str
    trust_score: int
    created_at: datetime
    owner_email: str | None = None
    automated_checks: AutomatedCompanyChecks

    model_config = ConfigDict(from_attributes=True)


class RecruiterApprovalItem(BaseModel):
    user_id: uuid.UUID
    full_name: str
    organization: str
    work_email_domain: str | None = None
    email: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminDecisionRequest(BaseModel):
    reason: str | None = None
    note: str | None = None


class AdminRequestInfoRequest(BaseModel):
    message: str


class AuditLogItem(BaseModel):
    id: int
    actor_id: uuid.UUID | None = None
    actor_email: str | None = None
    action: str
    entity_type: str | None = None
    entity_id: str | None = None
    detail: dict[str, Any] | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedAuditLog(BaseModel):
    items: list[AuditLogItem]
    page: int
    page_size: int
    total: int
