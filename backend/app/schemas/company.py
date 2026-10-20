import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CompanyRegisterRequest(BaseModel):
    name: str
    website: str | None = None
    description: str | None = None


class CompanyUpdateRequest(BaseModel):
    website: str | None = None
    description: str | None = None


class CompanyResponse(BaseModel):
    id: uuid.UUID
    name: str
    website: str | None = None
    email_domain: str | None = None
    description: str | None = None
    registration_doc_key: str | None = None
    status: str
    trust_score: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CompanyStatsResponse(BaseModel):
    projects_posted: int = 0
    students_selected: int = 0
    projects_completed: int = 0
    active_projects: int = 0
    pending_reviews: int = 0
