"""Evaluation API routes: deliverable submissions, evaluations, appeals.
See docs/04-api-specification.md Section 7 and FR-EVL-1 to 7.
"""
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.evaluation import (
    AppealResponse,
    CreateAppealRequest,
    CreateEvaluationRequest,
    CreateSubmissionRequest,
    EvaluationDecisionResponse,
    EvaluationResponse,
    SubmissionResponse,
)
from app.services.evaluation_service import EvaluationService

router = APIRouter(tags=["evaluations"])


@router.post(
    "/applications/{application_id}/submissions",
    response_model=SubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit deliverable version (FR-EVL-1, T-EVL-01, T-EVL-05)",
)
def submit_deliverable(
    application_id: uuid.UUID,
    req: CreateSubmissionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = EvaluationService(db)
    return service.submit_deliverable(current_user, application_id, req)


@router.get(
    "/submissions/{submission_id}",
    response_model=SubmissionResponse,
    summary="Get submission details (FR-EVL-1)",
)
def get_submission(
    submission_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = EvaluationService(db)
    return service.get_submission(current_user, submission_id)


@router.post(
    "/submissions/{submission_id}/evaluation",
    response_model=EvaluationDecisionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Evaluate submission (FR-EVL-4, T-EVL-03, T-EVL-04, FR-CRT-1)",
)
def evaluate_submission(
    submission_id: uuid.UUID,
    req: CreateEvaluationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = EvaluationService(db)
    return service.evaluate_submission(current_user, submission_id, req)


@router.get(
    "/evaluations/{evaluation_id}",
    response_model=EvaluationResponse,
    summary="Get evaluation details (FR-EVL-4)",
)
def get_evaluation(
    evaluation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = EvaluationService(db)
    return service.get_evaluation(current_user, evaluation_id)


@router.post(
    "/evaluations/{evaluation_id}/appeal",
    response_model=AppealResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Appeal an evaluation within 7 days (FR-EVL-7, BR-7, T-EVL-07, T-EVL-08)",
)
def create_appeal(
    evaluation_id: uuid.UUID,
    req: CreateAppealRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = EvaluationService(db)
    return service.create_appeal(current_user, evaluation_id, req)
