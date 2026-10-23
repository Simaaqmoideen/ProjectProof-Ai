"""Applications router — HTTP layer only; business rules live in ApplicationService.
Implements: FR-APP-1 to FR-APP-9.
API spec: docs/04-api-specification.md §Applications.
"""

import uuid

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.db import get_db
from app.deps import (
    get_current_user,
    require_approved_company,
    require_roles,
    require_verified_email,
)
from app.models.application import Application
from app.models.user import StudentProfile, User
from app.repositories.application_repo import ApplicationRepository
from app.repositories.project_repo import ProjectRepository
from app.schemas.application import (
    ApplicationStudentInfo,
    ApplyRequest,
    PaginatedApplicationsResponse,
    RejectApplicationRequest,
    StudentSkillItem,
)
from app.services.application_service import ApplicationService
from app.services.match_service import MatchScoreService

router = APIRouter(prefix="", tags=["Applications"])


# ── helpers ────────────────────────────────────────────────────────────────────


def _get_student_info(db: Session, student_id: uuid.UUID) -> ApplicationStudentInfo | None:
    sp = db.execute(
        select(StudentProfile).where(StudentProfile.user_id == student_id)
    ).scalar_one_or_none()
    if not sp:
        return None

    from app.models.application import Certificate

    # Count verified certificates
    verified_count = (
        db.execute(
            select(Certificate)
            .join(Application, Certificate.application_id == Application.id)
            .where(Application.student_id == student_id, Certificate.status == "issued")
        )
        .scalars()
        .all()
    )
    xp_total = sum(c.xp_awarded for c in verified_count)

    skills = [
        StudentSkillItem(name=ss.skill.name, proficiency=ss.proficiency, source=ss.source)
        for ss in sp.skills
    ]

    return ApplicationStudentInfo(
        user_id=sp.user_id,
        full_name=sp.full_name,
        headline=sp.headline,
        college=sp.college,
        graduation_year=sp.graduation_year,
        github_username=sp.github_username,
        github_summary=sp.github_summary,
        skills=skills,
        verified_projects_count=len(verified_count),
        xp=xp_total,
    )


def _build_application_response(
    db: Session,
    application: Application,
    include_student: bool = False,
    include_project: bool = False,
) -> dict:
    resp: dict = {
        "id": application.id,
        "project_id": application.project_id,
        "student_id": application.student_id,
        "status": application.status,
        "cover_note": application.cover_note,
        "match_score": float(application.match_score)
        if application.match_score is not None
        else None,
        "match_breakdown": application.match_breakdown,
        "applied_at": application.applied_at,
        "decided_at": application.decided_at,
        "status_reason": application.status_reason,
        "started_at": application.started_at,
        "due_at": application.due_at,
        "completed_at": application.completed_at,
        "project": None,
        "student": None,
    }
    if include_student:
        resp["student"] = _get_student_info(db, application.student_id)
    if include_project:
        project = ProjectRepository.get_by_id(db, application.project_id)
        if project:
            from app.repositories.project_repo import ProjectRepository as PR

            skill_names = PR.get_skill_names(db, project.id)
            company = project.company
            resp["project"] = {
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
                "company": {
                    "id": company.id,
                    "name": company.name,
                    "website": company.website,
                    "status": company.status,
                    "trust_score": company.trust_score,
                },
                "skills": skill_names,
                "milestones": [],
                "created_at": project.created_at,
                "match": None,
            }
    return resp


# ── FR-APP-1: Student applies to a project ────────────────────────────────────


@router.post("/projects/{project_id}/applications", status_code=status.HTTP_201_CREATED)
def apply_to_project(
    project_id: uuid.UUID,
    data: ApplyRequest,
    request: Request,
    current_user: User = Depends(require_roles("student")),
    db: Session = Depends(get_db),
):
    """FR-APP-1, T-APP-01: Apply to an open project. Max 3 active; no duplicate."""
    require_verified_email(current_user)
    application = ApplicationService.apply(
        db=db,
        student_id=current_user.id,
        project_id=project_id,
        cover_note=data.cover_note,
        actor_ip=request.client.host if request.client else None,
    )
    return _build_application_response(db, application, include_project=True)


# ── FR-APP-2: Student withdraws an application ────────────────────────────────


@router.post("/applications/{application_id}/withdraw")
def withdraw_application(
    application_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_roles("student")),
    db: Session = Depends(get_db),
):
    """FR-APP-2, T-APP-02: Student withdraws an 'applied' application."""
    require_verified_email(current_user)
    application = ApplicationService.withdraw(
        db=db,
        application_id=application_id,
        student_id=current_user.id,
        actor_ip=request.client.host if request.client else None,
    )
    return _build_application_response(db, application)


# ── FR-APP-3: Student lists own applications ──────────────────────────────────


@router.get("/applications/me", response_model=PaginatedApplicationsResponse)
def list_my_applications(
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_roles("student")),
    db: Session = Depends(get_db),
):
    """FR-APP-3: List own applications with project details."""
    require_verified_email(current_user)
    applications, total = ApplicationRepository.list_for_student(
        db,
        current_user.id,
        status=status_filter,
        page=page,
        page_size=page_size,
    )
    items = [_build_application_response(db, a, include_project=True) for a in applications]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


# ── FR-APP-4: Company views applicants for a project ──────────────────────────


@router.get("/projects/{project_id}/applications")
def list_project_applications(
    project_id: uuid.UUID,
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user_and_company: tuple = Depends(require_approved_company),
    db: Session = Depends(get_db),
):
    """FR-APP-4, T-APP-03: Company views applications for their project."""
    _current_user, company = user_and_company
    project = ProjectRepository.get_company_project(db, project_id, company.id)
    if not project:
        raise NotFoundError("Project not found.")

    applications, total = ApplicationRepository.list_for_project(
        db,
        project_id,
        status=status_filter,
        page=page,
        page_size=page_size,
    )
    items = [_build_application_response(db, a, include_student=True) for a in applications]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


# ── FR-APP-5: Company selects an applicant ────────────────────────────────────


@router.post("/applications/{application_id}/select")
def select_applicant(
    application_id: uuid.UUID,
    request: Request,
    user_and_company: tuple = Depends(require_approved_company),
    db: Session = Depends(get_db),
):
    """FR-APP-5, T-APP-04: Company selects an applicant; enforces max_selected."""
    current_user, company = user_and_company
    application = ApplicationService.select_applicant(
        db=db,
        application_id=application_id,
        company_id=company.id,
        actor_id=current_user.id,
        actor_ip=request.client.host if request.client else None,
    )
    return {
        "message": "Applicant selected.",
        "application_id": application.id,
        "status": application.status,
        "started_at": application.started_at,
        "due_at": application.due_at,
    }


# ── FR-APP-6: Company rejects an applicant ────────────────────────────────────


@router.post("/applications/{application_id}/reject")
def reject_applicant(
    application_id: uuid.UUID,
    data: RejectApplicationRequest,
    request: Request,
    user_and_company: tuple = Depends(require_approved_company),
    db: Session = Depends(get_db),
):
    """FR-APP-6, T-APP-05: Company rejects an applicant."""
    current_user, company = user_and_company
    application = ApplicationService.reject_applicant(
        db=db,
        application_id=application_id,
        company_id=company.id,
        actor_id=current_user.id,
        reason=data.reason,
        actor_ip=request.client.host if request.client else None,
    )
    return _build_application_response(db, application)


# ── FR-APP-7: Company compares applicants ────────────────────────────────────


@router.get("/projects/{project_id}/applications/compare")
def compare_applicants(
    project_id: uuid.UUID,
    user_and_company: tuple = Depends(require_approved_company),
    db: Session = Depends(get_db),
):
    """FR-APP-7, T-APP-06: Side-by-side applicant comparison with match scores."""
    _current_user, company = user_and_company
    project = ProjectRepository.get_company_project(db, project_id, company.id)
    if not project:
        raise NotFoundError("Project not found.")

    # Only compare 'applied' applications
    applications, _ = ApplicationRepository.list_for_project(
        db,
        project_id,
        status="applied",
        page=1,
        page_size=200,
    )

    applicants = []
    for app in applications:
        student_info = _get_student_info(db, app.student_id)
        if not student_info:
            continue

        # Recompute match for freshness (or use stored score if identical)
        match_info = MatchScoreService.calculate_match_score(db, app.student_id, project)

        applicants.append(
            {
                "application_id": app.id,
                "status": app.status,
                "student": student_info.model_dump(),
                "cover_note": app.cover_note,
                "match_score": match_info["score"],
                "match_breakdown": match_info["breakdown"],
                "missing_skills": match_info["missing_skills"],
                "verified_projects_count": student_info.verified_projects_count,
                "xp": student_info.xp,
                "github_summary": student_info.github_summary,
            }
        )

    applicants.sort(key=lambda x: x["match_score"], reverse=True)

    return {
        "project_id": project.id,
        "project_title": project.title,
        "applicants": applicants,
    }


# ── FR-APP-8: Single application detail ──────────────────────────────────────


@router.get("/applications/{application_id}")
def get_application(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """FR-APP-8: Get application detail. Student sees own; company sees own project's."""
    require_verified_email(current_user)
    application = ApplicationRepository.get_by_id(db, application_id)
    if not application:
        raise NotFoundError("Application not found.")

    if current_user.role == "student":
        if application.student_id != current_user.id:
            raise NotFoundError("Application not found.")
        return _build_application_response(db, application, include_project=True)
    elif current_user.role == "company":
        from app.repositories.company_repo import CompanyRepository

        company = CompanyRepository.get_by_user_id(db, current_user.id)
        if not company:
            raise NotFoundError("Application not found.")
        project = ProjectRepository.get_company_project(db, application.project_id, company.id)
        if not project:
            raise NotFoundError("Application not found.")
        return _build_application_response(db, application, include_student=True)
    elif current_user.role == "admin":
        return _build_application_response(
            db, application, include_student=True, include_project=True
        )

    raise NotFoundError("Application not found.")


# ── FR-WRK-5: Mentor usage summary for company / student / admin ─────────────


@router.get("/applications/{application_id}/mentor-usage")
def get_mentor_usage_summary(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """FR-WRK-5: Exchange count for mentor assistance without revealing private content."""
    require_verified_email(current_user)
    application = ApplicationRepository.get_by_id(db, application_id)
    if not application:
        raise NotFoundError("Application not found.")

    # Authorization: Student owner, project company, or admin
    if current_user.role == "student":
        if application.student_id != current_user.id:
            raise NotFoundError("Application not found.")
    elif current_user.role == "company":
        from app.repositories.company_repo import CompanyRepository

        company = CompanyRepository.get_by_user_id(db, current_user.id)
        if not company:
            raise NotFoundError("Application not found.")
        project = ProjectRepository.get_company_project(db, application.project_id, company.id)
        if not project:
            raise NotFoundError("Application not found.")
    elif current_user.role != "admin":
        raise NotFoundError("Application not found.")

    total = (
        db.execute(
            text("""
                SELECT count(*) FROM ai_logs
                 WHERE feature = 'mentor'
                   AND user_id = :uid
                   AND application_id = CAST(:aid AS uuid)
            """),
            {"uid": application.student_id, "aid": str(application_id)},
        ).scalar()
        or 0
    )

    return {
        "application_id": str(application_id),
        "total_exchanges": int(total),
        "note": "Per privacy policy, mentor chat content is private to the student.",
    }
