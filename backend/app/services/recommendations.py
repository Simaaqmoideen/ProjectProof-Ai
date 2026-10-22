"""Project recommendation service.

FR-APP-10, BR-10: Recommendation score and ranking for a student's dashboard.
  recommend = min(100, match + 10 if category matched + 5 if 1-2 skills missing)
  Only open projects the student has not applied to and hasn't hit the 3-active limit.
Computed by code — never by LLM.
"""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.project import Project
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
    all_open = db.execute(select(Project).where(Project.status == "open")).scalars().all()

    recommendations: list[dict[str, Any]] = []
    for project in all_open:
        rec = MatchScoreService.calculate_recommendation(db, student_id, project)
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
