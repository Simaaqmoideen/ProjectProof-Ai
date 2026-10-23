"""Project recommendation service.

FR-APP-10, BR-10: Recommendation score and ranking for a student's dashboard.
  recommend = min(100, match + 10 if category matched + 5 if 1-2 skills missing)
  Only open projects the student has not applied to and hasn't hit the 3-active limit.
Computed by code — never by LLM.
"""

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.application import Application, Certificate
from app.models.project import Project, ProjectSkill, Skill, StudentSkill
from app.services.match_service import MatchScoreService


def get_recommended_projects(
    db: Session,
    student_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """FR-APP-10: Return open projects ranked by recommendation score with a reason.

    Excludes:
    - Projects the student already applied to.
    - Removed projects.
    - Everything when the student already has >= 3 active applications.

    Returns paginated result: {"items": [...], "page": ..., "page_size": ..., "total": ...}
    """
    # Check 3-active applications limit once before loop
    active_apps_count = db.execute(
        select(func.count())
        .select_from(Application)
        .where(
            Application.student_id == student_id,
            Application.status.in_(["applied", "in_progress", "submitted", "changes_requested"]),
        )
    ).scalar_one()
    if active_apps_count >= 3:
        return {"items": [], "page": page, "page_size": page_size, "total": 0}
    scoring_active_count = db.execute(
        select(func.count())
        .select_from(Application)
        .where(
            Application.student_id == student_id,
            Application.status.in_(["in_progress", "submitted", "changes_requested"]),
        )
    ).scalar_one()

    # Preload applied project IDs once
    applied_project_ids = set(
        db.execute(select(Application.project_id).where(Application.student_id == student_id))
        .scalars()
        .all()
    )

    student_skill_map = {
        skill.skill_id: skill
        for skill in db.execute(select(StudentSkill).where(StudentSkill.student_id == student_id))
        .scalars()
        .all()
    }
    all_skills_map = {skill.id: skill.name for skill in db.execute(select(Skill)).scalars().all()}
    issued_certs = list(
        db.execute(
            select(Certificate, Project)
            .join(Application, Certificate.application_id == Application.id)
            .join(Project, Application.project_id == Project.id)
            .where(Application.student_id == student_id, Certificate.status == "issued")
        ).all()
    )
    completed_categories = {completed_project.category for _, completed_project in issued_certs}
    completed_project_ids = {completed_project.id for _, completed_project in issued_certs}
    project_skill_ids: dict[uuid.UUID, set[int]] = {}
    if completed_project_ids:
        for completed_id, skill_id in db.execute(
            select(ProjectSkill.project_id, ProjectSkill.skill_id).where(
                ProjectSkill.project_id.in_(completed_project_ids)
            )
        ).all():
            project_skill_ids.setdefault(completed_id, set()).add(skill_id)
    preloaded = {
        "active_count": active_apps_count,
        "scoring_active_count": scoring_active_count,
        "applied_project_ids": applied_project_ids,
        "student_skill_map": student_skill_map,
        "all_skills_map": all_skills_map,
        "issued_certs": issued_certs,
        "completed_categories": completed_categories,
        "project_skill_ids": project_skill_ids,
    }

    all_open = db.execute(select(Project).where(Project.status == "open")).scalars().all()

    recommendations: list[dict[str, Any]] = []
    for project in all_open:
        if project.id in applied_project_ids:
            continue
        rec = MatchScoreService.calculate_recommendation(db, student_id, project, preloaded)
        if rec is None:
            # Student already applied, or >= 3 active; skip
            continue
        recommendations.append(rec)

    # Sort by recommendation score descending
    recommendations.sort(key=lambda r: -r["recommendation_score"])

    total = len(recommendations)
    start = (page - 1) * page_size
    end = start + page_size
    page_items = recommendations[start:end]

    items = [
        {
            "project_id": str(r["project_id"]),
            "title": r["project"].title,
            "category": r["project"].category,
            "difficulty": r["project"].difficulty,
            "duration_days": r["project"].duration_days,
            "xp_max": r["project"].xp_max,
            "recommendation_score": r["recommendation_score"],
            "match_score": r["match_score"],
            "match_breakdown": r["match_breakdown"],
            "reason": r["reason"],
            "missing_skills": r["missing_skills"],
        }
        for r in page_items
    ]

    return {"items": items, "page": page, "page_size": page_size, "total": total}
