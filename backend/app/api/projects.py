"""Projects router — HTTP layer only; business rules live in services.
Implements: FR-PRJ-1 to FR-PRJ-8, FR-APP-10.
API spec: docs/04-api-specification.md §Projects.
"""

import uuid

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.db import get_db
from app.deps import (
    get_optional_current_user,
    require_company,
    require_roles,
    require_verified_email,
)
from app.models.project import Project
from app.models.user import StudentProfile, User
from app.repositories.company_repo import CompanyRepository
from app.repositories.project_repo import ProjectRepository
from app.schemas.project import (
    MilestoneResponse,
    PaginatedProjectsResponse,
    ProjectCompanyInfo,
    ProjectCreateRequest,
    ProjectResponse,
    ProjectUpdateRequest,
    TaskResponse,
)
from app.services.match_service import MatchScoreService
from app.services.project_service import ProjectService

router = APIRouter(prefix="", tags=["Projects"])


# ── helpers ────────────────────────────────────────────────────────────────────


def _build_project_response(db: Session, project: Project, viewer: User | None = None) -> dict:
    """Assemble ProjectResponse dict; attach match info for student viewers (FR-APP-3)."""
    skill_names = ProjectRepository.get_skill_names(db, project.id)

    # Milestones + tasks
    ms_list = []
    for ms in project.milestones:
        task_list = [
            TaskResponse(id=t.id, position=t.position, title=t.title, description=t.description)
            for t in ms.tasks
        ]
        ms_list.append(
            MilestoneResponse(
                id=ms.id,
                position=ms.position,
                title=ms.title,
                description=ms.description,
                due_day_offset=ms.due_day_offset,
                tasks=task_list,
            )
        )

    company = project.company
    company_info = ProjectCompanyInfo(
        id=company.id,
        name=company.name,
        website=company.website,
        status=company.status,
        trust_score=company.trust_score,
    )

    match_data = None
    if viewer and viewer.role == "student":
        sp = db.execute(
            select(StudentProfile).where(StudentProfile.user_id == viewer.id)
        ).scalar_one_or_none()
        if sp:
            match_data = MatchScoreService.calculate_match_score(db, viewer.id, project)

    return {
        "id": project.id,
        "title": project.title,
        "description": project.description,
        "category": project.category,
        "difficulty": project.difficulty,
        "duration_days": project.duration_days,
        "xp_max": project.xp_max,
        "max_selected": project.max_selected,
        "status": project.status,
        "application_deadline": project.application_deadline,
        "published_at": project.published_at,
        "company": company_info,
        "skills": skill_names,
        "milestones": ms_list,
        "created_at": project.created_at,
        "match": match_data,
    }


# ── FR-PRJ-1: Create draft project (company) ──────────────────────────────────


@router.post("/companies/me/projects", status_code=status.HTTP_201_CREATED)
def create_project(
    data: ProjectCreateRequest,
    request: Request,
    user_and_company: tuple = Depends(require_company),
    db: Session = Depends(get_db),
):
    """FR-PRJ-1, T-PRJ-01: Create a project draft. xp_max is server-computed."""
    current_user, company = user_and_company
    project = ProjectService.create_draft(
        db=db,
        company=company,
        created_by=current_user.id,
        data=data.model_dump(),
        actor_ip=request.client.host if request.client else None,
    )
    return _build_project_response(db, project)


@router.get("/companies/me/projects", response_model=PaginatedProjectsResponse)
def list_company_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    user_and_company: tuple = Depends(require_company),
    db: Session = Depends(get_db),
):
    """List all projects for current company (drafts, open, in_progress, closed)."""
    current_user, company = user_and_company
    projects, total = ProjectRepository.list_for_company(
        db, company.id, page=page, page_size=page_size
    )
    items = [_build_project_response(db, p, viewer=current_user) for p in projects]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


# ── FR-PRJ-2: Update draft project ────────────────────────────────────────────


@router.put("/projects/{project_id}")
def update_project(
    project_id: uuid.UUID,
    data: ProjectUpdateRequest,
    request: Request,
    user_and_company: tuple = Depends(require_company),
    db: Session = Depends(get_db),
):
    """FR-PRJ-2: Edit a draft project."""
    current_user, company = user_and_company
    project = ProjectService.update_draft(
        db=db,
        project_id=project_id,
        company=company,
        actor_id=current_user.id,
        data=data.model_dump(exclude_unset=True),
    )
    return _build_project_response(db, project)


# ── FR-WRK-7: Replace milestones on a project ─────────────────────────────────

from pydantic import BaseModel as _BaseModel
from pydantic import Field as _Field

from app.schemas.project import TaskCreate


class MilestoneReplaceItem(_BaseModel):
    position: int | None = None
    title: str
    description: str | None = None
    due_day_offset: int
    tasks: list[TaskCreate] = _Field(default_factory=list)


class ReplaceMilestonesRequest(_BaseModel):
    milestones: list[MilestoneReplaceItem]


@router.put("/projects/{project_id}/milestones")
def replace_project_milestones(
    project_id: uuid.UUID,
    data: ReplaceMilestonesRequest,
    user_and_company: tuple = Depends(require_company),
    db: Session = Depends(get_db),
):
    """FR-WRK-7, docs/04 Section 5: Replace milestones list with tasks."""
    from app.core.errors import ConflictError
    from app.models.application import Application

    _current_user, company = user_and_company
    project = ProjectRepository.get_company_project(db, project_id, company.id)
    if not project:
        raise NotFoundError("Project not found.")

    # Rejected with 409 after first selection (FR-PRJ-6, docs/04 §5)
    has_selection = db.execute(
        select(Application.id).where(
            Application.project_id == project_id, Application.started_at.is_not(None)
        )
    ).first()
    if has_selection:
        raise ConflictError("Milestones and tasks are locked after the first student is selected.")

    # Prepare data for repo
    ms_data = []
    for idx, m in enumerate(data.milestones, start=1):
        m_dict = m.model_dump()
        if "position" not in m_dict or not m_dict["position"]:
            m_dict["position"] = idx
        ms_data.append(m_dict)

    ProjectRepository.replace_milestones(db, project_id, ms_data)
    db.commit()
    db.refresh(project)
    return _build_project_response(db, project)


# ── FR-PRJ-3: Publish project ─────────────────────────────────────────────────


@router.post("/projects/{project_id}/publish")
def publish_project(
    project_id: uuid.UUID,
    request: Request,
    user_and_company: tuple = Depends(require_company),
    db: Session = Depends(get_db),
):
    """FR-PRJ-3, FR-ORG-5, T-ORG-05: Publish a draft project."""
    current_user, company = user_and_company
    # Evaluations completed = 0 for Phase 2 (will be wired from evaluations table in Phase 3)
    project = ProjectService.publish(
        db=db,
        project_id=project_id,
        company=company,
        actor_id=current_user.id,
        actor_ip=request.client.host if request.client else None,
        evaluations_completed=0,
    )
    return {
        "message": "Project published successfully.",
        "id": str(project.id),
        "status": project.status,
    }


# ── FR-PRJ-4: Close project ───────────────────────────────────────────────────


@router.post("/projects/{project_id}/close")
def close_project(
    project_id: uuid.UUID,
    request: Request,
    user_and_company: tuple = Depends(require_company),
    db: Session = Depends(get_db),
):
    """FR-PRJ-4: Close an open project."""
    current_user, company = user_and_company
    project = ProjectService.close(
        db=db,
        project_id=project_id,
        company=company,
        actor_id=current_user.id,
        actor_ip=request.client.host if request.client else None,
    )
    return {"message": "Project closed.", "id": str(project.id), "status": project.status}


# ── FR-PRJ-5: Cancel project ─────────────────────────────────────────────────


@router.post("/projects/{project_id}/cancel")
def cancel_project(
    project_id: uuid.UUID,
    request: Request,
    user_and_company: tuple = Depends(require_company),
    db: Session = Depends(get_db),
):
    """FR-PRJ-5: Cancel a draft or open project."""
    current_user, company = user_and_company
    project = ProjectService.cancel(
        db=db,
        project_id=project_id,
        company=company,
        actor_id=current_user.id,
        actor_ip=request.client.host if request.client else None,
    )
    return {"message": "Project cancelled.", "id": str(project.id), "status": project.status}


# ── FR-PRJ-6: Browse and search open projects ─────────────────────────────────


@router.get("/projects", response_model=PaginatedProjectsResponse)
def list_projects(
    request: Request,
    category: str | None = Query(None),
    difficulty: str | None = Query(None),
    search: str | None = Query(None, max_length=200),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    """FR-PRJ-6: Browse open projects. Students see match score (FR-APP-3)."""
    # Allow unauthenticated browsing
    viewer = current_user

    projects, total = ProjectRepository.list_open(
        db,
        category=category,
        difficulty=difficulty,
        search=search,
        page=page,
        page_size=page_size,
    )
    items = [_build_project_response(db, p, viewer=viewer) for p in projects]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


# ── FR-APP-10 / FR-PRJ-8: Recommended projects for student ───────────────────


@router.get("/projects/recommended")
@router.get("/projects/recommendations")
def get_recommended_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("student")),
):
    """FR-APP-10, FR-PRJ-8, BR-10: Personalised project recommendations for a student."""
    require_verified_email(current_user)
    from app.services import recommendations as recommendations_service

    return recommendations_service.get_recommended_projects(
        db, student_id=current_user.id, page=page, page_size=page_size
    )


# ── FR-PRJ-7: Get project detail ─────────────────────────────────────────────


@router.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    """FR-PRJ-7: Get project details. Company can see own drafts; students/public see open projects."""
    viewer = current_user

    project = ProjectRepository.get_by_id(db, project_id)
    if not project:
        raise NotFoundError("Project not found.")

    # Visibility: public can only see 'open'; company owner can see their own drafts
    if project.status != "open":
        if not viewer:
            raise NotFoundError("Project not found.")
        if viewer.role == "company":
            company = CompanyRepository.get_by_user_id(db, viewer.id)
            if not company or company.id != project.company_id:
                raise NotFoundError("Project not found.")
        elif viewer.role != "admin":
            raise NotFoundError("Project not found.")

    return _build_project_response(db, project, viewer=viewer)


# ─── Project report (FR-ADM-9) ───────────────────────────────────────────────


@router.post("/projects/{project_id}/report", status_code=status.HTTP_201_CREATED)
def report_project(
    project_id: uuid.UUID,
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("student", "recruiter", "company")),
):
    """FR-ADM-9, T-ADM-08: Any authenticated user can report a project; opens a manual flag."""
    import uuid as _uuid

    from sqlalchemy import text as _text

    require_verified_email(current_user)

    reason = (data.get("reason") or "").strip()
    note = (data.get("note") or "").strip() or None
    if not reason:
        from app.core.errors import BadRequestError

        raise BadRequestError("reason is required.")

    # Verify project exists
    proj = db.execute(
        _text("SELECT id FROM projects WHERE id = :pid"),
        {"pid": project_id},
    ).fetchone()
    if not proj:
        raise NotFoundError("Project not found.")

    import json as _json

    flag_id = _uuid.uuid4()
    details_json = _json.dumps(
        {
            "reason": reason,
            "note": note,
            "reported_by": str(current_user.id),
        }
    )
    db.execute(
        _text("""
            INSERT INTO flags (id, kind, entity_type, entity_id, details, status, created_at)
            VALUES (:id, 'manual', 'project', :entity_id, CAST(:details AS jsonb), 'open', now())
        """),
        {
            "id": flag_id,
            "entity_id": project_id,
            "details": details_json,
        },
    )
    db.commit()
    return {"message": "Report submitted. An admin will review it.", "flag_id": str(flag_id)}
