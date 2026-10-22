"""Student portfolio service.

FR-STU-10: Student portfolio page showing verified project history.
           Revoked records shown with a 'revoked' label, never hidden.
BR-8: is_public check — recruiters see only public profiles.
"""

import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError


def get_portfolio(db: Session, student_user_id: uuid.UUID) -> list[dict[str, Any]]:
    """Return own portfolio (issued + revoked), newest issued_at first.
    Reads from v_student_portfolio view.
    """
    rows = db.execute(
        text("""
            SELECT verification_id, qr_token, status, xp_awarded, issued_at, revoked_at,
                   project_title, category, difficulty, duration_days,
                   company_name, completed_at, public_summary, skills
              FROM v_student_portfolio
             WHERE student_id = :uid
             ORDER BY issued_at DESC
        """),
        {"uid": student_user_id},
    ).fetchall()

    return [_row_to_dict(r) for r in rows]


def get_public_portfolio(db: Session, student_user_id: uuid.UUID) -> list[dict[str, Any]]:
    """Return a public student's portfolio for recruiter view.
    BR-8: if profile is not public, raise 404 (ownership check already done by caller).
    """
    # Check is_public, active account, and verified email
    profile = db.execute(
        text("""
            SELECT sp.is_public
              FROM student_profiles sp
              JOIN users u ON u.id = sp.user_id
             WHERE sp.user_id = :uid
               AND u.is_active = TRUE
               AND u.email_verified_at IS NOT NULL
        """),
        {"uid": student_user_id},
    ).fetchone()

    if not profile or not profile[0]:
        raise NotFoundError("Student profile not found or is private.")

    rows = db.execute(
        text("""
            SELECT verification_id, qr_token, status, xp_awarded, issued_at, revoked_at,
                   project_title, category, difficulty, duration_days,
                   company_name, completed_at, public_summary, skills
              FROM v_student_portfolio
             WHERE student_id = :uid
             ORDER BY issued_at DESC
        """),
        {"uid": student_user_id},
    ).fetchall()

    return [_row_to_dict(r) for r in rows]


def _row_to_dict(row) -> dict[str, Any]:
    return {
        "verification_id": row[0],
        "qr_token": row[1],
        "status": row[2],
        "xp_awarded": row[3],
        "issued_at": row[4].isoformat() if row[4] else None,
        "revoked_at": row[5].isoformat() if row[5] else None,
        "project_title": row[6],
        "category": row[7],
        "difficulty": row[8],
        "duration_days": row[9],
        "company_name": row[10],
        "completed_at": row[11].isoformat() if row[11] else None,
        "public_summary": row[12],
        "skills": list(row[13]) if row[13] else [],
    }


def get_student_stats(db: Session, student_user_id: uuid.UUID) -> dict[str, Any]:
    """FR-ANA-1: Student statistics."""
    row = db.execute(
        text("""
            SELECT
                COALESCE((SELECT total_xp FROM v_student_progress WHERE student_id = :uid), 0) AS xp,
                (SELECT count(*) FROM applications WHERE student_id = :uid)                 AS total_applications,
                (SELECT count(*) FROM applications WHERE student_id = :uid
                    AND status = 'in_progress')                                             AS active_projects,
                (SELECT count(*) FROM applications WHERE student_id = :uid
                    AND status = 'completed')                                               AS completed_projects,
                (SELECT count(*) FROM applications a
                    JOIN certificates c ON c.application_id = a.id
                    WHERE a.student_id = :uid AND c.status = 'issued')                     AS verified_projects,
                (SELECT count(*) FROM applications WHERE student_id = :uid
                    AND status = 'rejected')                                                AS rejected_projects
        """),
        {"uid": student_user_id},
    ).fetchone()

    total = row[1]
    completed = row[4]
    completion_rate = round(completed / total * 100) if total > 0 else 0

    return {
        "xp": int(row[0]),
        "total_applications": int(row[1]),
        "active_projects": int(row[2]),
        "completed_projects": int(row[3]),
        "verified_projects": int(row[4]),
        "rejected_projects": int(row[5]),
        "completion_rate": completion_rate,
    }
