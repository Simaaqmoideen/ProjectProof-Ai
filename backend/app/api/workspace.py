"""Workspace API routes: workspace view, milestone check-ins, task progress and personal sub-tasks.
See docs/04-api-specification.md Section 7 and FR-WRK-1 to 8.
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.workspace import (
    CreateCheckinRequest,
    CreatePersonalTaskRequest,
    ReviewCheckinRequest,
    UpdateTaskProgressRequest,
    WorkspaceViewResponse,
)
from app.services.workspace_service import WorkspaceService

router = APIRouter(tags=["workspace"])


@router.get(
    "/applications/{application_id}/workspace",
    response_model=WorkspaceViewResponse,
    summary="Get application workspace (FR-WRK-1, FR-WRK-7)",
)
def get_workspace(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = WorkspaceService(db)
    return service.get_workspace(current_user, application_id)


@router.post(
    "/applications/{application_id}/checkins",
    status_code=status.HTTP_201_CREATED,
    summary="Post milestone check-in (FR-WRK-2, T-WRK-02)",
)
def create_checkin(
    application_id: uuid.UUID,
    req: CreateCheckinRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = WorkspaceService(db)
    checkin_id = service.create_checkin(current_user, application_id, req)
    return {"id": checkin_id, "status": "submitted"}


@router.post(
    "/checkins/{checkin_id}/review",
    status_code=status.HTTP_200_OK,
    summary="Review milestone check-in (FR-WRK-3)",
)
def review_checkin(
    checkin_id: uuid.UUID,
    req: ReviewCheckinRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = WorkspaceService(db)
    service.review_checkin(current_user, checkin_id, req)
    return {"status": req.status}


@router.put(
    "/applications/{application_id}/tasks/{task_id}/progress",
    status_code=status.HTTP_200_OK,
    summary="Update task progress (FR-WRK-7)",
)
def update_task_progress(
    application_id: uuid.UUID,
    task_id: uuid.UUID,
    req: UpdateTaskProgressRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = WorkspaceService(db)
    service.update_task_progress(current_user, application_id, task_id, req.status)
    return {"status": req.status}


@router.post(
    "/applications/{application_id}/milestones/{milestone_id}/tasks",
    status_code=status.HTTP_201_CREATED,
    summary="Add student personal sub-task (FR-WRK-8)",
)
def create_personal_task(
    application_id: uuid.UUID,
    milestone_id: uuid.UUID,
    req: CreatePersonalTaskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = WorkspaceService(db)
    task_id = service.create_personal_task(current_user, application_id, milestone_id, req)
    return {"id": task_id, "title": req.title, "status": "todo", "is_personal": True}


@router.delete(
    "/applications/{application_id}/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete personal sub-task (FR-WRK-8)",
)
def delete_personal_task(
    application_id: uuid.UUID,
    task_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = WorkspaceService(db)
    service.delete_personal_task(current_user, application_id, task_id)
