"""Students API router.

Handles: profile, skills, visibility, resume, dashboard, portfolio, GitHub (FR-STU-1 to FR-STU-10).
Layers: HTTP only; all business logic delegated to services.
"""

import time
import uuid

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.config import settings
from app.core.errors import BadRequestError, NotFoundError
from app.db import get_db
from app.deps import require_roles, require_verified_email
from app.models.user import StudentProfile, User
from app.schemas.student import (
    GitHubLinkRequest,
    GitHubSummaryResponse,
    PortfolioItem,
    PortfolioResponse,
    SkillResponse,
    SkillsUpdateRequest,
    StudentDashboardResponse,
    StudentProfileResponse,
    StudentProfileUpdate,
    VisibilityUpdate,
)
from app.services import github as github_service
from app.services import portfolio as portfolio_service

router = APIRouter(prefix="/students", tags=["Students"])


def _require_student_profile(user: User, db: Session) -> StudentProfile:
    profile = (
        db.execute(select(StudentProfile).where(StudentProfile.user_id == user.id))
        .scalars()
        .first()
    )
    if not profile:
        raise NotFoundError("Student profile not found.")
    return profile


# ─── Profile ─────────────────────────────────────────────────────────────────


@router.get("/me", response_model=StudentProfileResponse)
def get_my_profile(
    user: User = Depends(require_roles("student")),
    db: Session = Depends(get_db),
):
    require_verified_email(user)
    profile = _require_student_profile(user, db)
    return profile


@router.put("/me", response_model=StudentProfileResponse)
def update_my_profile(
    data: StudentProfileUpdate,
    user: User = Depends(require_roles("student")),
    db: Session = Depends(get_db),
):
    require_verified_email(user)
    profile = _require_student_profile(user, db)

    if data.full_name is not None:
        profile.full_name = data.full_name
    if data.headline is not None:
        profile.headline = data.headline
    if data.bio is not None:
        profile.bio = data.bio
    if data.college is not None:
        profile.college = data.college
    if data.graduation_year is not None:
        profile.graduation_year = data.graduation_year

    db.commit()
    db.refresh(profile)
    return profile


@router.put("/me/visibility")
def update_visibility(
    data: VisibilityUpdate,
    user: User = Depends(require_roles("student")),
    db: Session = Depends(get_db),
):
    """FR-STU-5, FR-STU-6: Toggle public visibility and name preference."""
    require_verified_email(user)
    profile = _require_student_profile(user, db)

    profile.is_public = data.is_public
    if data.show_full_name_on_verification is not None:
        profile.show_full_name_on_verification = data.show_full_name_on_verification

    # Log consent (privacy by default rule)
    db.execute(
        text("""
            INSERT INTO consent_log (user_id, kind, granted)
            VALUES (:uid, 'public_profile', :granted)
        """),
        {"uid": user.id, "granted": data.is_public},
    )

    db.commit()
    return {
        "is_public": profile.is_public,
        "show_full_name_on_verification": profile.show_full_name_on_verification,
    }


# ─── Resume (FR-STU-3) ────────────────────────────────────────────────────────


@router.post("/me/resume")
async def upload_resume(
    file: UploadFile = File(...),
    user: User = Depends(require_roles("student")),
    db: Session = Depends(get_db),
):
    """FR-STU-3: Resume upload (PDF, up to 5 MB)."""
    require_verified_email(user)
    profile = _require_student_profile(user, db)

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise BadRequestError("Only PDF files are accepted.")

    content = await file.read()
    if len(content) > settings.max_resume_bytes:
        raise BadRequestError(
            f"Resume must be <= {settings.max_resume_bytes // (1024 * 1024)} MB."
        )

    resume_key = f"resumes/{user.id}_{int(time.time())}.pdf"
    profile.resume_file_key = resume_key
    db.commit()

    return {
        "message": "Resume uploaded successfully.",
        "resume_url": resume_key,
        "resume_file_key": resume_key,
    }


# ─── Skills ──────────────────────────────────────────────────────────────────


@router.get("/me/skills", response_model=list[SkillResponse])
def get_my_skills(
    user: User = Depends(require_roles("student")),
    db: Session = Depends(get_db),
):
    require_verified_email(user)
    rows = db.execute(
        text("""
            SELECT ss.skill_id, s.name, ss.proficiency, ss.source
              FROM student_skills ss
              JOIN skills s ON s.id = ss.skill_id
             WHERE ss.student_id = :uid
             ORDER BY s.name
        """),
        {"uid": user.id},
    ).fetchall()
    return [SkillResponse(skill_id=r[0], name=r[1], proficiency=r[2], source=r[3]) for r in rows]


@router.put("/me/skills")
def replace_my_skills(
    data: SkillsUpdateRequest,
    user: User = Depends(require_roles("student")),
    db: Session = Depends(get_db),
):
    """FR-STU-2: Replace skills list. Each skill must exist in the skills table."""
    require_verified_email(user)

    # Resolve skill names → IDs
    skill_ids = []
    for entry in data.skills:
        row = db.execute(
            text("SELECT id FROM skills WHERE lower(name) = lower(:name)"),
            {"name": entry.skill},
        ).fetchone()
        if not row:
            raise BadRequestError(f"Skill '{entry.skill}' not found in skill list.")
        skill_ids.append((row[0], entry.proficiency))

    # Delete existing self skills and insert new (replace)
    db.execute(
        text("DELETE FROM student_skills WHERE student_id = :uid AND source = 'self'"),
        {"uid": user.id},
    )
    for skill_id, proficiency in skill_ids:
        db.execute(
            text("""
                INSERT INTO student_skills (student_id, skill_id, proficiency, source)
                VALUES (:uid, :sid, :prof, 'self')
                ON CONFLICT (student_id, skill_id) DO UPDATE SET proficiency = :prof
            """),
            {"uid": user.id, "sid": skill_id, "prof": proficiency},
        )

    db.commit()
    return {"message": "Skills updated.", "count": len(skill_ids)}


# ─── Dashboard ───────────────────────────────────────────────────────────────


@router.get("/me/dashboard", response_model=StudentDashboardResponse)
def get_dashboard(
    user: User = Depends(require_roles("student")),
    db: Session = Depends(get_db),
):
    """FR-STU-7: Dashboard with XP, level, badges, active projects, stats."""
    require_verified_email(user)

    # XP and level from v_student_progress
    prog = db.execute(
        text("SELECT total_xp, level FROM v_student_progress WHERE student_id = :uid"),
        {"uid": user.id},
    ).fetchone()
    xp = int(prog[0]) if prog else 0
    level = int(prog[1]) if prog and prog[1] is not None else 1

    # Fetch level name and next level threshold from levels table
    current_level_row = db.execute(
        text("SELECT name FROM levels WHERE level = :lvl"),
        {"lvl": level},
    ).fetchone()
    level_name = current_level_row[0] if current_level_row else "Starter"

    next_level_row = db.execute(
        text("SELECT min_xp FROM levels WHERE level = :lvl"),
        {"lvl": level + 1},
    ).fetchone()
    xp_to_next = (int(next_level_row[0]) - xp) if next_level_row else None

    # Badges
    badge_rows = db.execute(
        text("""
            SELECT b.code, b.name, b.description, sb.awarded_at
              FROM student_badges sb
              JOIN badges b ON b.id = sb.badge_id
             WHERE sb.student_id = :uid
        """),
        {"uid": user.id},
    ).fetchall()
    badges = [
        {
            "code": r[0],
            "name": r[1],
            "description": r[2],
            "awarded_at": r[3].isoformat() if r[3] else None,
        }
        for r in badge_rows
    ]

    # Stats
    stats = portfolio_service.get_student_stats(db, user.id)

    return StudentDashboardResponse(
        xp=xp,
        level=level,
        level_name=level_name,
        xp_to_next_level=xp_to_next,
        badges=badges,
        active_projects=stats["active_projects"],
        completed_projects=stats["completed_projects"],
        verified_projects=stats["verified_projects"],
        total_applications=stats["total_applications"],
        completion_rate=stats["completion_rate"],
    )


# ─── Portfolio ────────────────────────────────────────────────────────────────


@router.get("/me/portfolio", response_model=PortfolioResponse)
def get_my_portfolio(
    user: User = Depends(require_roles("student")),
    db: Session = Depends(get_db),
):
    """FR-STU-10: Own portfolio — issued and revoked certs, newest first."""
    require_verified_email(user)
    items = portfolio_service.get_portfolio(db, user.id)
    return PortfolioResponse(items=[PortfolioItem(**i) for i in items], total=len(items))


# ─── GitHub ──────────────────────────────────────────────────────────────────


@router.put("/me/github")
def link_github(
    data: GitHubLinkRequest,
    user: User = Depends(require_roles("student")),
    db: Session = Depends(get_db),
):
    """FR-STU-8: Link GitHub username and fetch public summary.
    T-STU-04: Invalid usernames (slash, space, >39 chars) rejected before any request leaves.
    AGENTS.md rule 12: Only services/github.py calls GitHub.
    """
    require_verified_email(user)
    summary = github_service.link_github(db, student_user_id=user.id, username=data.username)
    db.commit()
    return {"message": "GitHub linked.", "label": "self-linked, not verified", "summary": summary}


@router.get("/me/github", response_model=GitHubSummaryResponse)
def get_github(
    user: User = Depends(require_roles("student")),
    db: Session = Depends(get_db),
):
    """FR-STU-8: Return stored GitHub summary."""
    require_verified_email(user)
    result = github_service.get_github_summary(db, user.id)
    if not result:
        raise NotFoundError("No GitHub account linked.")
    return GitHubSummaryResponse(
        username=result["username"],
        label=result["label"],
        summary=result["summary"],
        analyzed_at=result["analyzed_at"],
    )


@router.delete("/me/github", status_code=status.HTTP_204_NO_CONTENT)
def unlink_github(
    user: User = Depends(require_roles("student")),
    db: Session = Depends(get_db),
):
    """DELETE /students/me/github: unlink and delete stored GitHub summary."""
    require_verified_email(user)
    github_service.unlink_github(db, user.id)
    db.commit()


# ─── Public Portfolio ─────────────────────────────────────────────────────────


@router.get("/{student_id}/portfolio", response_model=PortfolioResponse)
def get_public_portfolio(
    student_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """FR-STU-10, BR-8: Public portfolio for a student. Returns 404 if private."""
    items = portfolio_service.get_public_portfolio(db, student_id)
    student_name = portfolio_service.get_public_student_name(db, student_id)
    return PortfolioResponse(
        items=[PortfolioItem(**i) for i in items],
        total=len(items),
        student_name=student_name,
    )

