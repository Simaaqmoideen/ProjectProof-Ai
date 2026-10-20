"""Evaluation service: deliverable submissions, evaluations, appeals, and certificate issuance.
See docs/01 FR-EVL-1 to 7, BR-1, BR-7, docs/04 Section 7.
"""
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.models.user import User
from app.repositories.evaluation_repo import EvaluationRepository
from app.repositories.workspace_repo import WorkspaceRepository
from app.schemas.evaluation import (
    AppealResponse,
    CertificateSummary,
    CreateAppealRequest,
    CreateEvaluationRequest,
    CreateSubmissionRequest,
    EvaluationDecisionResponse,
    EvaluationResponse,
    SubmissionResponse,
)
from app.services.certificate import CertificateError, issue_certificate_for_application
from app.services.notifications import create_notification


class EvaluationService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = EvaluationRepository(db)
        self.workspace_repo = WorkspaceRepository(db)

    def submit_deliverable(
        self, current_user: User, application_id: uuid.UUID, req: CreateSubmissionRequest
    ) -> SubmissionResponse:
        """POST /applications/{id}/submissions (FR-EVL-1, T-EVL-01, T-EVL-05)."""
        app_data = self.workspace_repo.get_application_with_project(application_id)
        if not app_data:
            raise HTTPException(status_code=404, detail="Application not found")

        # Must be owner student
        if current_user.role != "student" or app_data["student_id"] != current_user.id:
            raise HTTPException(status_code=404, detail="Application not found")

        if app_data["status"] not in ("in_progress", "changes_requested"):
            raise HTTPException(
                status_code=409,
                detail=f"Cannot submit deliverables on application with status '{app_data['status']}'",
            )

        # Check version count limit (max 3 versions: T-EVL-01)
        current_version = self.repo.get_latest_submission_version(application_id)
        if current_version >= settings.max_submission_versions:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum {settings.max_submission_versions} submission versions reached",
            )

        new_version = current_version + 1
        sub_id = self.repo.create_submission(
            application_id=application_id,
            version=new_version,
            repo_url=req.repo_url,
            file_key=req.file_key,
            notes=req.notes,
        )

        # Notify company of new submission
        comp_member = self.db.execute(
            text("SELECT user_id FROM company_members WHERE company_id = :comp_id ORDER BY member_role = 'owner' DESC LIMIT 1"),
            {"comp_id": app_data["company_id"]},
        ).fetchone()
        if comp_member:
            create_notification(
                db=self.db,
                user_id=comp_member[0],
                type="submission_received",
                title=f"Submission received (v{new_version})",
                body=f"{app_data['student_name']} submitted deliverable version {new_version} for '{app_data['project_title']}'.",
                link=f"/company/submissions/{sub_id}/review",
            )


        self.db.commit()
        sub_data = self.repo.get_submission(sub_id)
        return SubmissionResponse(**sub_data)

    def get_submission(self, current_user: User, submission_id: uuid.UUID) -> SubmissionResponse:
        """GET /submissions/{id} (FR-EVL-1)."""
        sub_data = self.repo.get_submission(submission_id)
        if not sub_data:
            raise HTTPException(status_code=404, detail="Submission not found")

        # Check access: student owner, owning company, or admin
        if current_user.role == "student":
            if sub_data["student_id"] != current_user.id:
                raise HTTPException(status_code=404, detail="Submission not found")
        elif current_user.role == "company":
            membership = self.db.execute(
                text("SELECT member_role FROM company_members WHERE company_id = :comp_id AND user_id = :user_id"),
                {"comp_id": sub_data["company_id"], "user_id": current_user.id},
            ).fetchone()
            if not membership:
                raise HTTPException(status_code=404, detail="Submission not found")
        elif current_user.role != "admin":
            raise HTTPException(status_code=404, detail="Submission not found")

        return SubmissionResponse(**sub_data)

    def evaluate_submission(
        self, current_user: User, submission_id: uuid.UUID, req: CreateEvaluationRequest
    ) -> EvaluationDecisionResponse:
        """POST /submissions/{id}/evaluation (FR-EVL-4, T-EVL-03, T-EVL-04, FR-CRT-1)."""
        sub_data = self.repo.get_submission(submission_id)
        if not sub_data:
            raise HTTPException(status_code=404, detail="Submission not found")

        # Check reviewer belongs to project's company (T-EVL-04: Reviewer from another company evaluates -> 404)
        if current_user.role == "company":
            membership = self.db.execute(
                text("SELECT member_role FROM company_members WHERE company_id = :comp_id AND user_id = :user_id"),
                {"comp_id": sub_data["company_id"], "user_id": current_user.id},
            ).fetchone()
            if not membership:
                raise HTTPException(status_code=404, detail="Submission not found")
        elif current_user.role != "admin":
            raise HTTPException(status_code=404, detail="Submission not found")

        # Check if already evaluated
        existing_eval = self.repo.get_evaluation_by_submission(submission_id)
        if existing_eval:
            raise HTTPException(status_code=409, detail="This submission has already been evaluated")

        # Business rule check: overall_score < 60 cannot be approved (T-EVL-03)
        if req.decision == "approved" and req.overall_score < 60:
            raise HTTPException(
                status_code=409,
                detail="Overall score below 60 cannot be approved (must be at least 60)",
            )

        # Create evaluation record
        eval_id = self.repo.create_evaluation(
            submission_id=submission_id,
            reviewer_id=current_user.id,
            rubric_scores=req.rubric_scores,
            overall_score=req.overall_score,
            feedback=req.feedback,
            public_summary=req.public_summary,
            used_ai_draft=req.used_ai_draft,
            decision=req.decision,
        )

        cert_summary = None
        new_app_status = "submitted"

        if req.decision == "approved":
            # Call single-door certificate service (AGENTS.md rule 3)
            try:
                cert_result = issue_certificate_for_application(
                    db=self.db,
                    application_id=sub_data["application_id"],
                    reviewer_id=current_user.id,
                    overall_score=req.overall_score,
                    rubric_scores=req.rubric_scores,
                    feedback=req.feedback,
                    public_summary=req.public_summary,
                    used_ai_draft=req.used_ai_draft,
                )
                new_app_status = "completed"
                cert_summary = CertificateSummary(
                    id=cert_result["certificate_id"],
                    verification_id=cert_result["verification_id"],
                    qr_token=cert_result["qr_token"],
                    xp_awarded=cert_result["xp_awarded"],
                    status=cert_result["status"],
                )
            except CertificateError as e:
                raise HTTPException(status_code=e.status_code, detail=e.message)

        elif req.decision == "changes_requested":
            new_app_status = "changes_requested"
            self.repo.update_application_status(sub_data["application_id"], new_app_status)
            create_notification(
                db=self.db,
                user_id=sub_data["student_id"],
                type="changes_requested",
                title="Changes requested on your submission",
                body=f"Reviewer left feedback: {req.feedback[:100]}...",
                link=f"/student/applications/{sub_data['application_id']}/workspace",
            )

        elif req.decision == "rejected":
            new_app_status = "failed"
            self.repo.update_application_status(sub_data["application_id"], new_app_status)
            create_notification(
                db=self.db,
                user_id=sub_data["student_id"],
                type="submission_rejected",
                title="Submission evaluation decision: Rejected",
                body=f"Reviewer feedback: {req.feedback[:100]}...",
                link=f"/student/applications/{sub_data['application_id']}/workspace",
            )

        self.db.commit()

        return EvaluationDecisionResponse(
            evaluation_id=eval_id,
            application_status=new_app_status,
            decision=req.decision,
            certificate=cert_summary,
        )

    def get_evaluation(self, current_user: User, evaluation_id: uuid.UUID) -> EvaluationResponse:
        """GET /evaluations/{id} (FR-EVL-4)."""
        eval_data = self.repo.get_evaluation(evaluation_id)
        if not eval_data:
            raise HTTPException(status_code=404, detail="Evaluation not found")

        # Access check
        if current_user.role == "student":
            if eval_data["student_id"] != current_user.id:
                raise HTTPException(status_code=404, detail="Evaluation not found")
        elif current_user.role == "company":
            membership = self.db.execute(
                text("SELECT member_role FROM company_members WHERE company_id = :comp_id AND user_id = :user_id"),
                {"comp_id": eval_data["company_id"], "user_id": current_user.id},
            ).fetchone()
            if not membership:
                raise HTTPException(status_code=404, detail="Evaluation not found")
        elif current_user.role != "admin":
            raise HTTPException(status_code=404, detail="Evaluation not found")

        return EvaluationResponse(**eval_data)

    def create_appeal(
        self, current_user: User, evaluation_id: uuid.UUID, req: CreateAppealRequest
    ) -> AppealResponse:
        """POST /evaluations/{id}/appeal (FR-EVL-7, BR-7, T-EVL-07, T-EVL-08)."""
        eval_data = self.repo.get_evaluation(evaluation_id)
        if not eval_data:
            raise HTTPException(status_code=404, detail="Evaluation not found")

        # Only student owner can appeal
        if current_user.role != "student" or eval_data["student_id"] != current_user.id:
            raise HTTPException(status_code=404, detail="Evaluation not found")

        # Check 7 days limit (BR-7, T-EVL-07)
        now = datetime.now(UTC)
        eval_time = eval_data["evaluated_at"]
        if eval_time.tzinfo is None:
            eval_time = eval_time.replace(tzinfo=UTC)

        if now - eval_time > timedelta(days=settings.appeal_days):
            raise HTTPException(
                status_code=400,
                detail=f"Appeals must be submitted within {settings.appeal_days} days of the evaluation",
            )

        # Check for existing open appeal (BR-7, T-EVL-08)
        open_appeal = self.repo.get_open_appeal_for_evaluation(evaluation_id)
        if open_appeal:
            raise HTTPException(
                status_code=409,
                detail="There is already an open appeal for this evaluation",
            )

        appeal_id = self.repo.create_appeal(
            evaluation_id=evaluation_id,
            student_id=current_user.id,
            reason=req.reason,
        )

        appeal_row = self.db.execute(
            text("SELECT id, evaluation_id, student_id, reason, status, resolved_by, resolution_note, created_at, resolved_at FROM appeals WHERE id = :id"),
            {"id": appeal_id},
        ).mappings().fetchone()

        self.db.commit()
        return AppealResponse(**dict(appeal_row))

