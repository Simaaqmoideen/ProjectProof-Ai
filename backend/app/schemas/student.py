"""Pydantic schemas for student profile, portfolio, dashboard, GitHub, notifications."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# ─── Student Profile ─────────────────────────────────────────────────────────


class StudentProfileUpdate(BaseModel):
    full_name: str | None = None
    headline: str | None = None
    bio: str | None = None
    college: str | None = None
    graduation_year: int | None = None


class StudentProfileResponse(BaseModel):
    user_id: uuid.UUID
    full_name: str
    headline: str | None
    bio: str | None
    college: str | None
    graduation_year: int | None
    github_username: str | None
    is_public: bool
    show_full_name_on_verification: bool
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class VisibilityUpdate(BaseModel):
    is_public: bool
    show_full_name_on_verification: bool | None = None


# ─── Skills ──────────────────────────────────────────────────────────────────


class SkillEntry(BaseModel):
    skill: str = Field(min_length=1, max_length=100)
    proficiency: int = Field(ge=1, le=5)


class SkillsUpdateRequest(BaseModel):
    skills: list[SkillEntry]


class SkillResponse(BaseModel):
    skill_id: int
    name: str
    proficiency: int
    source: str


# ─── Dashboard ───────────────────────────────────────────────────────────────


class StudentDashboardResponse(BaseModel):
    xp: int
    level: int
    level_name: str
    xp_to_next_level: int | None
    badges: list[dict[str, Any]]
    active_projects: int
    completed_projects: int
    verified_projects: int
    total_applications: int
    completion_rate: int


# ─── Portfolio ────────────────────────────────────────────────────────────────


class PortfolioItem(BaseModel):
    verification_id: str
    qr_token: str
    status: str
    xp_awarded: int | None
    issued_at: str | None
    revoked_at: str | None
    project_title: str
    category: str | None
    difficulty: str
    duration_days: int
    company_name: str
    completed_at: str | None
    public_summary: str | None
    skills: list[str]


class PortfolioResponse(BaseModel):
    items: list[PortfolioItem]
    total: int


# ─── GitHub ──────────────────────────────────────────────────────────────────


class GitHubLinkRequest(BaseModel):
    username: str = Field(min_length=1, max_length=39)


class GitHubSummaryResponse(BaseModel):
    username: str
    label: str
    summary: dict[str, Any]
    analyzed_at: str | None


# ─── Notifications ────────────────────────────────────────────────────────────


class NotificationResponse(BaseModel):
    id: uuid.UUID
    type: str
    title: str
    body: str | None
    link: str | None
    read_at: datetime | None
    is_read: bool = False
    created_at: datetime
    model_config = {"from_attributes": True}

    @classmethod
    def from_row(cls, r: any) -> "NotificationResponse":
        return cls(
            id=r[0],
            type=r[1],
            title=r[2],
            body=r[3],
            link=r[4],
            is_read=r[5] is not None,
            read_at=r[5],
            created_at=r[6],
        )


class PaginatedNotifications(BaseModel):
    items: list[NotificationResponse]
    page: int
    page_size: int
    total: int
    has_more: bool = False


# ─── Recruiter search ─────────────────────────────────────────────────────────


class RecruiterStudentResult(BaseModel):
    student_id: uuid.UUID
    display_name: str
    headline: str | None
    college: str | None
    graduation_year: int | None
    verified_projects: int
    xp: int
    level: int
    level_name: str
    top_skills: list[str]


class RecruiterSearchResponse(BaseModel):
    items: list[RecruiterStudentResult]
    page: int
    page_size: int
    total: int


# ─── Company stats ─────────────────────────────────────────────────────────────


class CompanyStatsResponse(BaseModel):
    projects_posted: int
    students_selected: int
    projects_completed: int
    active_projects: int
    pending_reviews: int


# ─── Platform stats ───────────────────────────────────────────────────────────


class PlatformStatsResponse(BaseModel):
    active_students: int
    approved_companies: int
    approved_recruiters: int
    open_projects: int
    removed_projects: int
    active_applications: int
    completed_applications: int
    certificates_issued: int
    certificates_revoked: int
    open_flags: int
    open_appeals: int
    lookups_30d: int


# ─── Recommendations ──────────────────────────────────────────────────────────


class RecommendationItem(BaseModel):
    project_id: str
    title: str
    category: str | None
    difficulty: str
    duration_days: int
    xp_max: int
    recommendation_score: int
    match_score: int
    match_breakdown: dict[str, Any]
    reason: str
    missing_skills: list[str]


class RecommendationsResponse(BaseModel):
    items: list[RecommendationItem]
    page: int
    page_size: int
    total: int


# ─── Project removal ─────────────────────────────────────────────────────────


class ProjectRemovalRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=200)
    note: str | None = Field(default=None, max_length=2000)


class ProjectRemovalResponse(BaseModel):
    project_id: str
    new_status: str
    applied_rejected: int
    active_withdrawn: int
    company_trust_score: int


# ─── Project report ──────────────────────────────────────────────────────────


class ProjectReportRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=200)
    note: str | None = Field(default=None, max_length=2000)
