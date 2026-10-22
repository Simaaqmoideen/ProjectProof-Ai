"""Recruiter API router.

FR-REC-1: Search public students by skills, min_xp, min_verified, verified_only.
FR-REC-2: Open a student's public portfolio.
FR-REC-4: Results sorted by verified project count first, then XP.
BR-8: Only public profiles visible to recruiters.
T-REC-01, T-REC-02, T-REC-04.
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_approved_recruiter, require_roles, require_verified_email
from app.models.user import User
from app.schemas.recruiter import RecruiterProfileRequest, RecruiterProfileResponse
from app.schemas.student import (
    PortfolioItem,
    PortfolioResponse,
    RecruiterSearchResponse,
    RecruiterStudentResult,
)
from app.services import portfolio as portfolio_service
from app.services.recruiter_service import RecruiterService

router = APIRouter(prefix="", tags=["Recruiters"])


@router.post("/recruiters", response_model=RecruiterProfileResponse)
def register_recruiter_profile(
    data: RecruiterProfileRequest,
    current_user: User = Depends(require_roles("recruiter")),
    db: Session = Depends(get_db),
):
    require_verified_email(current_user)
    profile = RecruiterService.register_recruiter(
        db=db,
        user=current_user,
        full_name=data.full_name,
        organization=data.organization,
    )
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/recruiters/me", response_model=RecruiterProfileResponse)
def get_recruiter_profile(
    current_user: User = Depends(require_roles("recruiter")),
    db: Session = Depends(get_db),
):
    require_verified_email(current_user)
    return RecruiterService.get_profile(db, current_user)


@router.get("/recruiter/students", response_model=RecruiterSearchResponse)
def search_students(
    skills: str | None = Query(None, description="Comma-separated skill names"),
    min_xp: int = Query(0, ge=0),
    min_verified: int = Query(0, ge=0),
    verified_only: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    auth: tuple = Depends(require_approved_recruiter),
    db: Session = Depends(get_db),
):
    """FR-REC-1, FR-REC-4: Search public students sorted by verified_projects, then XP.
    BR-8: Only public, active profiles.
    T-REC-01: private profiles never returned.
    T-REC-02: student turns public off → disappears immediately.
    T-REC-04: verified_projects sorted first.
    """
    skill_list = [s.strip() for s in skills.split(",") if s.strip()] if skills else []

    # Build parameterised query
    filters = [
        "sp.is_public = TRUE",
        "u.is_active = TRUE",
        "u.email_verified_at IS NOT NULL",
        "COALESCE(vsp.total_xp, 0) >= :min_xp",
    ]
    params: dict = {"min_xp": min_xp}

    if min_verified > 0:
        filters.append("""
            (SELECT count(*) FROM certificates c
               JOIN applications a ON a.id = c.application_id
              WHERE a.student_id = u.id AND c.status = 'issued') >= :min_verified
        """)
        params["min_verified"] = min_verified

    if verified_only:
        filters.append("""
            EXISTS (
                SELECT 1 FROM certificates c
                  JOIN applications a ON a.id = c.application_id
                 WHERE a.student_id = u.id AND c.status = 'issued'
            )
        """)

    # Skill filter — only public, safe field from skills table
    if skill_list:
        # Build a subquery filter using EXISTS per skill
        for i, skill_name in enumerate(skill_list[:10]):  # cap at 10 skills
            param_key = f"skill_{i}"
            filters.append(f"""
                EXISTS (
                    SELECT 1 FROM student_skills ss_{i}
                    JOIN skills sk_{i} ON sk_{i}.id = ss_{i}.skill_id
                    WHERE ss_{i}.student_id = u.id AND lower(sk_{i}.name) = lower(:{param_key})
                )
            """)
            params[param_key] = skill_name

    where = " AND ".join(filters)

    count_sql = f"""
        SELECT count(*)
          FROM users u
          JOIN student_profiles sp ON sp.user_id = u.id
          LEFT JOIN v_student_progress vsp ON vsp.student_id = sp.user_id
         WHERE {where}
    """
    total = db.execute(text(count_sql), params).scalar() or 0

    offset = (page - 1) * page_size
    params["lim"] = page_size
    params["off"] = offset

    rows_sql = f"""
        SELECT u.id, sp.full_name, sp.headline, sp.college, sp.graduation_year,
               (SELECT count(*)::int FROM certificates c
                  JOIN applications a ON a.id = c.application_id
                 WHERE a.student_id = u.id AND c.status = 'issued') AS verified_projects,
               COALESCE(vsp.total_xp, 0) AS total_xp,
               COALESCE(vsp.level, 1) AS level,
               COALESCE((SELECT name FROM levels WHERE level = vsp.level), 'Starter') AS level_name,
               ARRAY(
                 SELECT s.name::text FROM student_skills ss
                 JOIN skills s ON s.id = ss.skill_id
                 WHERE ss.student_id = u.id
                 ORDER BY ss.proficiency DESC LIMIT 5
               ) AS top_skills
          FROM users u
          JOIN student_profiles sp ON sp.user_id = u.id
          LEFT JOIN v_student_progress vsp ON vsp.student_id = sp.user_id
         WHERE {where}
         ORDER BY verified_projects DESC, total_xp DESC
         LIMIT :lim OFFSET :off
    """
    rows = db.execute(text(rows_sql), params).fetchall()

    items = [
        RecruiterStudentResult(
            student_id=r[0],
            display_name=r[1],
            headline=r[2],
            college=r[3],
            graduation_year=r[4],
            verified_projects=int(r[5]),
            xp=int(r[6]),
            level=int(r[7]),
            level_name=r[8],
            top_skills=list(r[9]) if r[9] else [],
        )
        for r in rows
    ]
    return RecruiterSearchResponse(items=items, page=page, page_size=page_size, total=int(total))


@router.get("/recruiter/students/{student_id}", response_model=PortfolioResponse)
def get_student_portfolio(
    student_id: uuid.UUID,
    auth: tuple = Depends(require_approved_recruiter),
    db: Session = Depends(get_db),
):
    """FR-REC-2, FR-STU-10, BR-8: Open a student's public portfolio.
    T-STU-02: private profile → 404.
    """
    items = portfolio_service.get_public_portfolio(db, student_id)
    return PortfolioResponse(items=[PortfolioItem(**i) for i in items], total=len(items))
