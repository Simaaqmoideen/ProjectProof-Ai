"""Application service — business rules for student applications and company decisions.
FR-APP-1 to FR-APP-9, BR-3.
Authorization order: role → ownership → state (AGENTS.md rule 6).
"""
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.errors import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.models.application import Application
from app.repositories.application_repo import ApplicationRepository
from app.repositories.project_repo import ProjectRepository
from app.services.audit_service import AuditService
from app.services.match_service import MatchScoreService


class ApplicationService:
    @staticmethod
    def apply(
        db: Session,
        student_id: uuid.UUID,
        project_id: uuid.UUID,
        cover_note: str | None,
        actor_ip: str | None = None,
    ) -> Application:
        """FR-APP-1: Student applies to an open project."""
        project = ProjectRepository.get_by_id(db, project_id)
        if not project or project.status != "open":
            raise NotFoundError("Project not found or not open.")

        # FR-APP-1: Cannot apply twice
        existing = ApplicationRepository.get_by_student_and_project(db, student_id, project_id)
        if existing:
            raise ConflictError("You have already applied to this project.")

        # FR-APP-1: Max 3 active applications per student
        active_count = ApplicationRepository.count_active_for_student(db, student_id)
        if active_count >= 3:
            raise ForbiddenError("You already have 3 active projects. Complete or withdraw one first.")

        # BR-3: Compute and persist match score immediately on apply
        match_info = MatchScoreService.calculate_match_score(db, student_id, project)

        application = Application(
            project_id=project_id,
            student_id=student_id,
            cover_note=cover_note,
            match_score=match_info["score"],
            match_breakdown=match_info["breakdown"],
            status="applied",
        )
        db.add(application)
        db.commit()
        db.refresh(application)
        return application

    @staticmethod
    def withdraw(
        db: Session,
        application_id: uuid.UUID,
        student_id: uuid.UUID,
        actor_ip: str | None = None,
    ) -> Application:
        """FR-APP-2: Student withdraws an application (applied only)."""
        application = ApplicationRepository.get_by_id(db, application_id)
        if not application or application.student_id != student_id:
            raise NotFoundError("Application not found.")
        if application.status != "applied":
            raise ValidationError(
                message="Only 'applied' applications can be withdrawn.",
                details=[{"field": "status", "issue": "invalid_transition"}],
            )

        ApplicationRepository.update_status(db, application_id, "withdrawn")
        db.commit()
        db.refresh(application)
        return application

    @staticmethod
    def select_applicant(
        db: Session,
        application_id: uuid.UUID,
        company_id: uuid.UUID,
        actor_id: uuid.UUID,
        actor_ip: str | None = None,
    ) -> Application:
        """FR-APP-5: Company selects an applicant (applied → in_progress).
        Checks max_selected limit; sets due_at = started_at + project.duration_days.
        """
        application = ApplicationRepository.get_by_id(db, application_id)
        if not application:
            raise NotFoundError("Application not found.")

        # Ownership: project must belong to this company
        project = ProjectRepository.get_company_project(db, application.project_id, company_id)
        if not project:
            raise NotFoundError("Application not found.")  # 404 per AGENTS.md rule 6

        if application.status != "applied":
            raise ValidationError(
                message=f"Can only select an 'applied' application (current: '{application.status}').",
                details=[{"field": "status", "issue": "not_applied"}],
            )

        # FR-APP-5: max_selected check
        already_selected = ApplicationRepository.count_selected_for_project(db, project.id)
        if already_selected >= project.max_selected:
            raise ForbiddenError(
                f"This project has already selected the maximum of {project.max_selected} student(s)."
            )

        now = datetime.now(UTC)
        due = now + timedelta(days=project.duration_days)

        ApplicationRepository.update_status(
            db,
            application_id,
            status="in_progress",
            decided_at=now,
            decided_by=actor_id,
            started_at=now,
            due_at=due,
        )

        AuditService.log(
            db,
            action="application_selected",
            actor_id=actor_id,
            entity_type="application",
            entity_id=str(application_id),
            detail={"project_id": str(project.id), "student_id": str(application.student_id)},
            ip=actor_ip,
        )

        db.commit()
        db.refresh(application)
        return application

    @staticmethod
    def reject_applicant(
        db: Session,
        application_id: uuid.UUID,
        company_id: uuid.UUID,
        actor_id: uuid.UUID,
        reason: str | None,
        actor_ip: str | None = None,
    ) -> Application:
        """FR-APP-6: Company rejects an applicant (applied → rejected)."""
        application = ApplicationRepository.get_by_id(db, application_id)
        if not application:
            raise NotFoundError("Application not found.")

        project = ProjectRepository.get_company_project(db, application.project_id, company_id)
        if not project:
            raise NotFoundError("Application not found.")

        if application.status != "applied":
            raise ValidationError(
                message=f"Can only reject an 'applied' application (current: '{application.status}').",
                details=[{"field": "status", "issue": "not_applied"}],
            )

        now = datetime.now(UTC)
        ApplicationRepository.update_status(
            db,
            application_id,
            status="rejected",
            decided_at=now,
            decided_by=actor_id,
            status_reason=reason,
        )

        AuditService.log(
            db,
            action="application_rejected",
            actor_id=actor_id,
            entity_type="application",
            entity_id=str(application_id),
            detail={"project_id": str(project.id), "reason": reason},
            ip=actor_ip,
        )

        db.commit()
        db.refresh(application)
        return application
