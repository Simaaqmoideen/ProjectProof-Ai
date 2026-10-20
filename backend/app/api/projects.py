import uuid
from datetime import UTC
from typing import Literal

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.errors import ForbiddenError, NotFoundError, ValidationError
from app.deps import get_db, require_roles, require_verified_email
from app.models.project import Milestone, Project
from app.models.user import User
from app.repositories.company_repo import CompanyRepository
from app.services.audit_service import AuditService

router = APIRouter(prefix="", tags=["Projects"])


class CreateProjectRequest(BaseModel):
    title: str = Field(..., min_length=3)
    description: str = Field(..., min_length=10)
    category: Literal["development", "data", "design", "other"] = "development"
    difficulty: Literal["beginner", "intermediate", "advanced"]
    duration_days: int = Field(..., ge=1, le=120)
    max_selected: int = Field(1, ge=1)
    xp_max: int | None = None  # Client must not provide this; if provided, reject (T-PRJ-01)


def compute_xp_max(duration_days: int, difficulty: str) -> int:
    base = settings.xp_base_per_day
    cap = settings.xp_cap
    diff_mult = settings.difficulty_multiplier.get(difficulty, 1.0)
    eval_mult = 1.2  # Max evaluation tier multiplier
    raw_xp = base * duration_days * diff_mult * eval_mult
    return round(min(cap, raw_xp))


@router.post("/companies/me/projects", status_code=status.HTTP_201_CREATED)
def create_project_draft(
    data: CreateProjectRequest,
    current_user: User = Depends(require_roles("company")),
    db: Session = Depends(get_db),
):
    require_verified_email(current_user)

    # T-PRJ-01: Create project with a client-supplied xp_max is rejected
    if data.xp_max is not None:
        raise ValidationError(
            message="xp_max is computed by the server and cannot be specified by the client.",
            details=[{"field": "xp_max", "issue": "read_only"}],
        )

    company = CompanyRepository.get_by_user_id(db, current_user.id)
    if not company:
        raise ForbiddenError("No company registered for this user.")

    # Calculate xp_max on server
    computed_xp = compute_xp_max(data.duration_days, data.difficulty)

    project = Project(
        company_id=company.id,
        created_by=current_user.id,
        title=data.title,
        description=data.description,
        category=data.category,
        difficulty=data.difficulty,
        duration_days=data.duration_days,
        xp_max=computed_xp,
        max_selected=data.max_selected,
        status="draft",
    )
    db.add(project)
    db.flush()

    # Add default milestone
    db.add(Milestone(
        project_id=project.id,
        position=1,
        title="Project Completion",
        due_day_offset=data.duration_days,
    ))

    db.commit()
    db.refresh(project)
    return project


@router.post("/projects/{project_id}/publish")
def publish_project(
    project_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_roles("company")),
    db: Session = Depends(get_db),
):
    require_verified_email(current_user)
    company = CompanyRepository.get_by_user_id(db, current_user.id)
    if not company:
        raise ForbiddenError("No company profile found.")

    # T-ORG-01 & FR-ORG-2: Pending company tries to publish -> 403
    if company.status != "approved":
        raise ForbiddenError(f"Company status is '{company.status}'. Only approved companies can publish projects.")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or project.company_id != company.id:
        raise NotFoundError("Project not found.")

    if project.status == "open":
        return {"message": "Project is already published.", "id": str(project.id), "status": project.status}

    # T-ORG-05 & FR-ORG-5: New company may have at most 2 open projects until it has completed 3 evaluations
    # Count open projects for this company
    open_count = db.query(func.count(Project.id)).filter(
        Project.company_id == company.id,
        Project.status == "open",
    ).scalar()

    # Count completed evaluations for this company
    # In Phase 1, evaluations completed is 0 for a new company
    evaluations_completed = 0  # In later phases, count from evaluations table

    if evaluations_completed < settings.new_company_evaluations_needed and open_count >= settings.new_company_project_limit:
        raise ForbiddenError(
            f"New companies may have at most {settings.new_company_project_limit} open projects until {settings.new_company_evaluations_needed} evaluations are completed."
        )

    project.status = "open"
    from datetime import datetime
    project.published_at = datetime.now(UTC)

    AuditService.log(
        db,
        action="project_published",
        actor_id=current_user.id,
        entity_type="project",
        entity_id=str(project.id),
        detail={"title": project.title, "xp_max": project.xp_max},
        ip=request.client.host if request.client else None,
    )

    db.commit()
    db.refresh(project)
    return {"message": "Project published successfully.", "id": str(project.id), "status": project.status}


@router.get("/projects")
def list_projects(
    db: Session = Depends(get_db),
):
    stmt = select(Project).where(Project.status == "open").order_by(Project.created_at.desc())
    projects = list(db.execute(stmt).scalars().all())
    return {"items": projects, "total": len(projects), "page": 1, "page_size": 20}
