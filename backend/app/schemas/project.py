import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    description: str | None = Field(None, max_length=1000)


class TaskResponse(BaseModel):
    id: uuid.UUID
    position: int
    title: str
    description: str | None = None

    model_config = {"from_attributes": True}


class MilestoneCreate(BaseModel):
    position: int = Field(..., ge=1, le=8)
    title: str = Field(..., min_length=2, max_length=200)
    description: str | None = Field(None, max_length=1000)
    due_day_offset: int = Field(..., ge=1)
    tasks: list[TaskCreate] = Field(default_factory=list, max_length=10)


class MilestoneResponse(BaseModel):
    id: uuid.UUID
    position: int
    title: str
    description: str | None = None
    due_day_offset: int
    tasks: list[TaskResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ProjectCompanyInfo(BaseModel):
    id: uuid.UUID
    name: str
    website: str | None = None
    status: str
    trust_score: int = 50

    model_config = {"from_attributes": True}


class ProjectCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=10)
    category: Literal["development", "data", "design", "other"] = "development"
    difficulty: Literal["beginner", "intermediate", "advanced"]
    duration_days: int = Field(..., ge=1, le=120)
    max_selected: int = Field(1, ge=1, le=50)
    application_deadline: datetime | None = None
    skills: list[str] = Field(default_factory=list)
    milestones: list[MilestoneCreate] = Field(default_factory=list, max_length=8)
    xp_max: int | None = None  # Read-only; rejected if supplied (T-PRJ-01, FR-PRJ-3)


class ProjectUpdateRequest(BaseModel):
    title: str | None = Field(None, min_length=3, max_length=200)
    description: str | None = Field(None, min_length=10)
    category: Literal["development", "data", "design", "other"] | None = None
    difficulty: Literal["beginner", "intermediate", "advanced"] | None = None
    duration_days: int | None = Field(None, ge=1, le=120)
    max_selected: int | None = Field(None, ge=1, le=50)
    application_deadline: datetime | None = None
    skills: list[str] | None = None
    xp_max: int | None = None  # Read-only; rejected if supplied


class MilestoneReplaceRequest(BaseModel):
    milestones: list[MilestoneCreate] = Field(..., min_length=1, max_length=8)


class ProjectResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    category: str
    difficulty: str
    duration_days: int
    xp_max: int
    max_selected: int
    status: str
    application_deadline: datetime | None = None
    published_at: datetime | None = None
    company: ProjectCompanyInfo
    skills: list[str] = Field(default_factory=list)
    milestones: list[MilestoneResponse] = Field(default_factory=list)
    created_at: datetime
    match: dict | None = None  # Populated for student viewers (FR-APP-3)

    model_config = {"from_attributes": True}


class PaginatedProjectsResponse(BaseModel):
    items: list[ProjectResponse]
    total: int
    page: int
    page_size: int


class RecommendedProjectItem(BaseModel):
    project: ProjectResponse
    recommendation_score: int
    reason: str
    match_score: int
    match_breakdown: dict
    missing_skills: list[str] = Field(default_factory=list)


class ReportProjectRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=100)
    note: str | None = Field(None, max_length=1000)
