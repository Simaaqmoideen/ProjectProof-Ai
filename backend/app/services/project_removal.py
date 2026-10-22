"""Project removal service.

AGENTS.md rule 11: Only this file sets a project to 'removed', in one transaction.
FR-ADM-8: Admin removes an inappropriate project.
  - reason is required
  - project → removed (disappears from browse/search)
  - applied applications → rejected (reason: project_removed, no penalty)
  - in_progress applications → withdrawn (reason: project_removed, no penalty)
  - notifications sent to all affected students
  - audit row written in same transaction
  - company trust score -15 (BR-6 v2)
  - Existing certificates are NOT touched
"""

import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.core.errors import BadRequestError, NotFoundError
from app.services.audit_service import AuditService
from app.services.notifications import create_notification
from app.services.trust_score import adjust_company_trust_score

VALID_REASONS = {"inappropriate", "spam", "fraudulent", "duplicate", "other"}


def remove_project(
    db: Session,
    admin_user_id: uuid.UUID,
    project_id: uuid.UUID,
    reason: str,
    note: str | None,
) -> dict[str, Any]:
    """FR-ADM-8: Remove project in a single atomic transaction.

    Returns summary of what was changed.
    """
    if not reason or not reason.strip():
        raise BadRequestError("A reason is required to remove a project.")
    reason = reason.strip()

    # Load project
    project_row = db.execute(
        text("SELECT id, status, company_id, title FROM projects WHERE id = :pid"),
        {"pid": project_id},
    ).fetchone()
    if not project_row:
        raise NotFoundError("Project not found.")
    if project_row[1] == "removed":
        raise BadRequestError("Project is already removed.")

    # Reject applied → rejected with project_removed
    applied_rows = db.execute(
        text("""
            UPDATE applications
               SET status = 'rejected',
                   status_reason = 'project_removed',
                   updated_at = now()
             WHERE project_id = :pid AND status = 'applied'
             RETURNING id, student_id
        """),
        {"pid": project_id},
    ).fetchall()

    # Withdraw in_progress/submitted/changes_requested
    active_statuses = ("in_progress", "submitted", "changes_requested")
    active_rows = db.execute(
        text("""
            UPDATE applications
               SET status = 'withdrawn',
                   status_reason = 'project_removed',
                   updated_at = now()
             WHERE project_id = :pid AND status = ANY(:statuses)
             RETURNING id, student_id
        """),
        {"pid": project_id, "statuses": list(active_statuses)},
    ).fetchall()

    # Mark project removed
    db.execute(
        text("""
            UPDATE projects
               SET status = 'removed',
                   removed_at = now(),
                   removed_by = :admin_id,
                   removal_reason = :reason,
                   updated_at = now()
             WHERE id = :pid
        """),
        {"pid": project_id, "admin_id": admin_user_id, "reason": reason},
    )

    # Trust score -15 for company (BR-6 v2)
    company_id = project_row[2]
    new_trust = adjust_company_trust_score(
        db, company_id, -settings.trust_score_removed_project_penalty
    )

    # Notifications for affected students
    project_title = project_row[3]
    notif_title = f"Project '{project_title}' was removed"
    notif_body = "The project was removed by an administrator. Your application was cancelled with no penalty."

    all_affected = list(applied_rows) + list(active_rows)
    for _app_id, student_id in all_affected:
        create_notification(
            db,
            user_id=student_id,
            type="project_removed",
            title=notif_title,
            body=notif_body,
        )

    # Audit row
    AuditService.log(
        db,
        actor_id=admin_user_id,
        action="project_removed",
        entity_type="project",
        entity_id=project_id,
        detail={
            "reason": reason,
            "note": note,
            "applied_rejected": len(applied_rows),
            "active_withdrawn": len(active_rows),
            "new_company_trust_score": new_trust,
        },
    )

    return {
        "project_id": str(project_id),
        "new_status": "removed",
        "applied_rejected": len(applied_rows),
        "active_withdrawn": len(active_rows),
        "company_trust_score": new_trust,
    }
