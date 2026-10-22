"""Pydantic output models for every AI feature.

All models are validated after the LLM call; extra fields are rejected.
See docs/06-ai-modules-specification.md section 6.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# ── Shared ────────────────────────────────────────────────────────────────────


class AIMeta(BaseModel):
    """Injected alongside every AI result before returning to the caller."""

    model_config = ConfigDict(extra="ignore")
    label: str = "AI draft"
    confidence: Literal["low", "medium", "high"] = "medium"
    log_id: str | None = None


# ── 6.1 Resume analysis (FR-STU-4) ───────────────────────────────────────────


class ResumeSkill(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    evidence: str


class ResumeEducation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    institution: str
    degree: str
    year: int | None = None


class ResumeProject(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str
    summary: str
    technologies: list[str] = Field(default_factory=list)


class ResumeExperience(BaseModel):
    model_config = ConfigDict(extra="forbid")
    organization: str
    role: str
    summary: str


class ResumeCertification(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    issuer: str


class ResumeAnalysisOutput(BaseModel):
    """LLM output for FR-STU-4 resume analysis."""

    model_config = ConfigDict(extra="forbid")
    skills: list[ResumeSkill] = Field(default_factory=list)
    education: list[ResumeEducation] = Field(default_factory=list)
    projects: list[ResumeProject] = Field(default_factory=list)
    experience: list[ResumeExperience] = Field(default_factory=list)
    certifications: list[ResumeCertification] = Field(default_factory=list)


# ── 6.2 Project brief generator (FR-PRJ-5) ───────────────────────────────────


class BriefMilestone(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str
    description: str
    due_day_offset: int


class BriefOutput(BaseModel):
    """LLM output for FR-PRJ-5 brief generator."""

    model_config = ConfigDict(extra="forbid")
    title: str
    description: str
    category: str
    difficulty: Literal["beginner", "intermediate", "advanced"]
    duration_days: int = Field(ge=7, le=365)
    required_skills: list[str] = Field(default_factory=list)
    milestones: list[BriefMilestone] = Field(default_factory=list)
    deliverables_checklist: list[str] = Field(default_factory=list)


# ── 6.3 Match explanation / applicant ranking (FR-APP-3, FR-APP-5) ───────────


class ApplicantExplanation(BaseModel):
    """Per-applicant explanation from LLM (FR-APP-3)."""

    model_config = ConfigDict(extra="forbid")
    application_id: str
    strengths: str  # up to 2 sentences
    gaps: str  # up to 1 sentence


class RankingOutput(BaseModel):
    """LLM output for FR-APP-5 applicant ranking reasons."""

    model_config = ConfigDict(extra="forbid")
    explanations: list[ApplicantExplanation] = Field(default_factory=list)


# ── 6.4 Submission pre-review (FR-EVL-3) ─────────────────────────────────────


class PreReviewItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    checklist_item: str
    status: Literal["met", "not_met", "unclear"]
    evidence: str
    file: str


class PreReviewOutput(BaseModel):
    """LLM output for FR-EVL-3 submission pre-review."""

    model_config = ConfigDict(extra="forbid")
    items: list[PreReviewItem] = Field(default_factory=list)
    overall_note: str


# ── 6.7 Recruiter plain-text search (FR-REC-3) ───────────────────────────────


class RecruiterSearchFilter(BaseModel):
    """LLM output for FR-REC-3 natural-language filter interpretation."""

    model_config = ConfigDict(extra="forbid")
    skills: list[str] = Field(default_factory=list)
    min_xp: int | None = None
    min_verified_projects: int | None = None
    category: str | None = None
    verified_only: bool = False


# ── 6.8 Skill gap (FR-APP-9) ─────────────────────────────────────────────────


class SkillGapItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    skill: str
    resource_type: Literal["documentation", "tutorial", "practice_project"]
    why: str


class SkillGapOutput(BaseModel):
    """LLM output for FR-APP-9 skill gap suggestions."""

    model_config = ConfigDict(extra="forbid")
    order_reason: str
    items: list[SkillGapItem] = Field(default_factory=list)


# ── 6.9 GitHub repo analysis (FR-STU-11) ─────────────────────────────────────


class GitHubSkillSuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    skill: str
    evidence: str  # must be a repo name or language from input


class GitHubAnalysisOutput(BaseModel):
    """LLM output for FR-STU-11 GitHub repo analysis."""

    model_config = ConfigDict(extra="forbid")
    summary: str
    skills: list[GitHubSkillSuggestion] = Field(default_factory=list)


# ── Accept-draft request (shared) ─────────────────────────────────────────────


class AcceptAIDraftRequest(BaseModel):
    """Body for POST .../ai/<feature>/accept — references a log_id."""

    model_config = ConfigDict(extra="forbid")
    log_id: str
    accepted_items: list[Any] = Field(default_factory=list)


# ── Phase 7: Stretch Schemas ──────────────────────────────────────────────────


class MentorChatOutput(BaseModel):
    """LLM output for FR-WRK-5 AI Mentor chatbot."""

    model_config = ConfigDict(extra="forbid")
    response: str
    contains_code: bool = False
    suggested_next_steps: list[str] = Field(default_factory=list)


class FeedbackDraftOutput(BaseModel):
    """LLM output for FR-EVL-5 evaluation feedback drafter."""

    model_config = ConfigDict(extra="forbid")
    strengths: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    suggested_public_summary: str


class ResumeBulletOutput(BaseModel):
    """LLM output for FR-RWD-4 verified record resume bullet rewriter."""

    model_config = ConfigDict(extra="forbid")
    bullets: list[str] = Field(min_length=1, max_length=5)
