"""Pydantic schemas for student workspace, tasks, and milestone check-ins."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TaskProgressItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    milestone_id: uuid.UUID
    title: str
    description: str | None = None
    order_index: int = 0
    is_personal: bool = False
    status: Literal["todo", "in_progress", "done"] = "todo"
    completed_at: datetime | None = None


class CheckinItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    milestone_id: uuid.UUID
    note: str | None = None
    evidence_url: str | None = None
    status: Literal["submitted", "accepted", "needs_work"] = "submitted"
    submitted_at: datetime
    reviewed_by: uuid.UUID | None = None
    reviewed_at: datetime | None = None
    review_note: str | None = None


class MilestoneWorkspaceItem(BaseModel):
    id: uuid.UUID
    title: str
    due_day_offset: int
    due_date: datetime | None = None
    is_overdue: bool = False
    tasks: list[TaskProgressItem] = []
    checkins: list[CheckinItem] = []


class SubmissionSummaryItem(BaseModel):
    id: uuid.UUID
    version: int
    repo_url: str | None = None
    file_key: str | None = None
    notes: str | None = None
    submitted_at: datetime


class WorkspaceViewResponse(BaseModel):
    application_id: uuid.UUID
    project_id: uuid.UUID
    project_title: str
    project_difficulty: str
    project_duration_days: int
    company_id: uuid.UUID
    company_name: str
    student_id: uuid.UUID
    student_name: str
    status: str
    started_at: datetime | None = None
    due_at: datetime | None = None
    completed_at: datetime | None = None
    milestones: list[MilestoneWorkspaceItem] = []
    submissions: list[SubmissionSummaryItem] = []


class CreateCheckinRequest(BaseModel):
    milestone_id: uuid.UUID
    note: str | None = Field(None, max_length=2000)
    evidence_url: str | None = Field(None, max_length=500)


class ReviewCheckinRequest(BaseModel):
    status: Literal["accepted", "needs_work"]
    review_note: str | None = Field(None, max_length=2000)


class UpdateTaskProgressRequest(BaseModel):
    status: Literal["todo", "in_progress", "done"]


class CreatePersonalTaskRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    description: str | None = Field(None, max_length=2000)
