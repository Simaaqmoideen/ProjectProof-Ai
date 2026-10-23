"""Project service — business rules for project lifecycle.
FR-PRJ-1 to FR-PRJ-8, FR-ORG-5, BR-1.
Authorization order: role → ownership → state (AGENTS.md rule 6).
"""

import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.core.errors import BadRequestError, ForbiddenError, NotFoundError, ValidationError
from app.models.project import Project
from app.models.user import Company
from app.repositories.flag_repo import FlagRepository
from app.repositories.project_repo import ProjectRepository
from app.services.audit_service import AuditService


def _compute_xp_max(duration_days: int, difficulty: str) -> int:
    """BR-1: xp_max is always computed by the server; never accepted from client."""
    base = settings.xp_base_per_day
    cap = settings.xp_cap
    diff_mult = settings.difficulty_multiplier.get(difficulty, 1.0)
    eval_mult = 1.2  # Maximum evaluation-tier multiplier
    raw = base * duration_days * diff_mult * eval_mult
    return round(min(cap, raw))


class ProjectService:
    @staticmethod
    def create_draft(
        db: Session,
        company: Company,
        created_by: uuid.UUID,
        data: dict,
        actor_ip: str | None = None,
    ) -> Project:
        """FR-PRJ-1: Create project draft (company only). xp_max is server-computed."""
        if data.get("xp_max") is not None:
            raise ValidationError(
                message="xp_max is computed by the server and cannot be specified by the client.",
                details=[{"field": "xp_max", "issue": "read_only"}],
            )

        computed_xp = _compute_xp_max(data["duration_days"], data["difficulty"])

        project = Project(
            company_id=company.id,
            created_by=created_by,
            title=data["title"],
            description=data["description"],
            category=data.get("category", "development"),
            difficulty=data["difficulty"],
            duration_days=data["duration_days"],
            xp_max=computed_xp,
            max_selected=data.get("max_selected", 1),
            application_deadline=data.get("application_deadline"),
            status="draft",
        )
        db.add(project)
        db.flush()

        # Replace skills (if provided)
        skills = data.get("skills", [])
        if skills:
            ProjectRepository.replace_skills(db, project.id, skills)

        # Replace milestones (if provided), otherwise add default
        milestones = data.get("milestones", [])
        if milestones:
            ProjectRepository.replace_milestones(
                db, project.id, [m.model_dump() for m in milestones]
            )
        else:
            from app.models.project import Milestone

            db.add(
                Milestone(
                    project_id=project.id,
                    position=1,
                    title="Project Completion",
                    due_day_offset=data["duration_days"],
                )
            )

        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def update_draft(
        db: Session,
        project_id: uuid.UUID,
        company: Company,
        actor_id: uuid.UUID,
        data: dict,
    ) -> Project:
        """FR-PRJ-2: Edit draft project (company, own project, draft only)."""
        project = ProjectRepository.get_company_project(db, project_id, company.id)
        if not project:
            raise NotFoundError("Project not found.")
        if project.status != "draft":
            raise ValidationError(
                message="Only draft projects can be edited.",
                details=[{"field": "status", "issue": "not_draft"}],
            )
        if data.get("xp_max") is not None:
            raise ValidationError(
                message="xp_max is read-only.",
                details=[{"field": "xp_max", "issue": "read_only"}],
            )

        update_fields: dict = {}
        for field in (
            "title",
            "description",
            "category",
            "difficulty",
            "duration_days",
            "max_selected",
            "application_deadline",
        ):
            if data.get(field) is not None:
                update_fields[field] = data[field]

        # Recompute xp_max if duration or difficulty changed
        duration = data.get("duration_days", project.duration_days)
        difficulty = data.get("difficulty", project.difficulty)
        update_fields["xp_max"] = _compute_xp_max(duration, difficulty)

        if update_fields:
            ProjectRepository.update_project(db, project_id, **update_fields)

        if "skills" in data and data["skills"] is not None:
            ProjectRepository.replace_skills(db, project_id, data["skills"])

        if "milestones" in data and data["milestones"] is not None:
            ProjectRepository.replace_milestones(
                db, project_id, [m.model_dump() for m in data["milestones"]]
            )

        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def publish(
        db: Session,
        project_id: uuid.UUID,
        company: Company,
        actor_id: uuid.UUID,
        actor_ip: str | None = None,
        evaluations_completed: int = 0,
    ) -> Project:
        """FR-PRJ-3, FR-ORG-2, FR-ORG-5, T-ORG-05: Publish a draft project."""
        if company.status != "approved":
            raise ForbiddenError(
                f"Company status is '{company.status}'. Only approved companies can publish projects."
            )

        project = ProjectRepository.get_company_project(db, project_id, company.id)
        if not project:
            raise NotFoundError("Project not found.")
        if project.status == "open":
            return project  # Idempotent

        if project.status != "draft":
            raise ValidationError(
                message=f"Cannot publish a project in '{project.status}' status.",
                details=[{"field": "status", "issue": "not_draft"}],
            )

        # FR-ORG-5 / T-ORG-05: new-company limit
        if evaluations_completed < settings.new_company_evaluations_needed:
            open_count = ProjectRepository.count_open_for_company(db, company.id)
            if open_count >= settings.new_company_project_limit:
                raise ForbiddenError(
                    f"New companies may have at most {settings.new_company_project_limit} open projects "
                    f"until {settings.new_company_evaluations_needed} evaluations are completed."
                )

        now = datetime.now(UTC)
        ProjectRepository.set_status(db, project_id, "open", published_at=now)

        AuditService.log(
            db,
            action="project_published",
            actor_id=actor_id,
            entity_type="project",
            entity_id=str(project_id),
            detail={"title": project.title, "xp_max": project.xp_max},
            ip=actor_ip,
        )

        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def close(
        db: Session,
        project_id: uuid.UUID,
        company: Company,
        actor_id: uuid.UUID,
        actor_ip: str | None = None,
    ) -> Project:
        """FR-PRJ-4: Close open project (no more applications)."""
        project = ProjectRepository.get_company_project(db, project_id, company.id)
        if not project:
            raise NotFoundError("Project not found.")
        if project.status != "open":
            raise ValidationError(
                message="Only open projects can be closed.",
                details=[{"field": "status", "issue": "not_open"}],
            )

        ProjectRepository.set_status(db, project_id, "closed")
        AuditService.log(
            db,
            action="project_closed",
            actor_id=actor_id,
            entity_type="project",
            entity_id=str(project_id),
            detail={"title": project.title},
            ip=actor_ip,
        )
        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def cancel(
        db: Session,
        project_id: uuid.UUID,
        company: Company,
        actor_id: uuid.UUID,
        actor_ip: str | None = None,
    ) -> Project:
        """FR-PRJ-5: Cancel a project (draft or open)."""
        project = ProjectRepository.get_company_project(db, project_id, company.id)
        if not project:
            raise NotFoundError("Project not found.")
        if project.status not in ("draft", "open"):
            raise ValidationError(
                message=f"Cannot cancel a project in '{project.status}' status.",
                details=[{"field": "status", "issue": "invalid_transition"}],
            )

        ProjectRepository.set_status(db, project_id, "cancelled")
        AuditService.log(
            db,
            action="project_cancelled",
            actor_id=actor_id,
            entity_type="project",
            entity_id=str(project_id),
            detail={"title": project.title},
            ip=actor_ip,
        )
        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def report_project(
        db: Session,
        project_id: uuid.UUID,
        reporter_id: uuid.UUID,
        reason: str,
        note: str | None = None,
    ) -> dict[str, str]:
        """FR-ADM-9: Create a manual flag for admin review."""
        reason = reason.strip()
        note = note.strip() if note else None
        if not reason:
            raise BadRequestError("reason is required.")

        # Verify project exists
        proj = db.execute(
            text("SELECT id FROM projects WHERE id = :pid"),
            {"pid": project_id},
        ).fetchone()
        if not proj:
            raise NotFoundError("Project not found.")

        flag_id = uuid.uuid4()
        details_json = json.dumps(
            {
                "reason": reason,
                "note": note,
                "reported_by": str(reporter_id),
            }
        )
        FlagRepository.create_project_report(db, flag_id, project_id, details_json)
        db.commit()
        return {"message": "Report submitted. An admin will review it.", "flag_id": str(flag_id)}
