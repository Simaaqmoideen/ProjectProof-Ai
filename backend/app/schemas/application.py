import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.project import ProjectResponse


class ApplyRequest(BaseModel):
    cover_note: str | None = Field(None, max_length=2000)


class StudentSkillItem(BaseModel):
    name: str
    proficiency: int
    source: str


class ApplicationStudentInfo(BaseModel):
    user_id: uuid.UUID
    full_name: str
    headline: str | None = None
    college: str | None = None
    graduation_year: int | None = None
    github_username: str | None = None
    github_summary: dict | None = None
    skills: list[StudentSkillItem] = Field(default_factory=list)
    verified_projects_count: int = 0
    xp: int = 0

    model_config = {"from_attributes": True}


class ApplicationResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    student_id: uuid.UUID
    status: str
    cover_note: str | None = None
    match_score: float | None = None
    match_breakdown: dict | None = None
    applied_at: datetime
    decided_at: datetime | None = None
    status_reason: str | None = None
    started_at: datetime | None = None
    due_at: datetime | None = None
    completed_at: datetime | None = None
    project: ProjectResponse | None = None
    student: ApplicationStudentInfo | None = None

    model_config = {"from_attributes": True}


class PaginatedApplicationsResponse(BaseModel):
    items: list[ApplicationResponse]
    total: int
    page: int
    page_size: int


class SelectApplicationResponse(BaseModel):
    message: str
    application_id: uuid.UUID
    status: str
    started_at: datetime
    due_at: datetime


class RejectApplicationRequest(BaseModel):
    reason: str | None = Field(None, max_length=500)


class ApplicantComparisonItem(BaseModel):
    application_id: uuid.UUID
    status: str
    student: ApplicationStudentInfo
    cover_note: str | None = None
    match_score: int
    match_breakdown: dict
    missing_skills: list[str] = Field(default_factory=list)
    verified_projects_count: int
    xp: int
    github_summary: dict | None = None


class ApplicantComparisonResponse(BaseModel):
    project_id: uuid.UUID
    project_title: str
    applicants: list[ApplicantComparisonItem]
