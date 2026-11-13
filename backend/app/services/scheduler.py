"""Scheduler jobs: overdue milestones and late resubmissions.
See docs/01 FR-WRK-4, FR-EVL-6, and docs/08 T-WRK-03, T-EVL-06.
"""

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.notifications import create_notification


def run_check_overdue_milestones(db: Session) -> int:
    """Flag overdue milestones and notify both sides ONCE (FR-WRK-4, T-WRK-03).

    Returns count of newly notified overdue milestones.
    """
    rows = db.execute(
        text("""
            SELECT a.id AS application_id, a.student_id, p.company_id, m.id AS milestone_id,
                   m.title AS milestone_title, p.title AS project_title,
                   a.started_at + (m.due_day_offset || ' days')::interval AS due
            FROM applications a
            JOIN projects p ON p.id = a.project_id
            JOIN milestones m ON m.project_id = a.project_id
            WHERE a.status = 'in_progress'
              AND a.started_at + (m.due_day_offset || ' days')::interval < now()
              AND NOT EXISTS (
                  SELECT 1 FROM milestone_checkins k
                  WHERE k.application_id = a.id AND k.milestone_id = m.id AND k.status = 'accepted'
              )
        """)
    ).fetchall()

    notified_count = 0
    for r in rows:
        app_id, student_id, company_id, milestone_id, m_title, p_title, _due = r

        # Check if already notified for this milestone to ensure once-only notification (T-WRK-03)
        existing = db.execute(
            text("""
                SELECT 1 FROM notifications
                WHERE type = 'milestone_overdue'
                  AND link = :link
            """),
            {"link": f"/applications/{app_id}/milestones/{milestone_id}"},
        ).fetchone()

        if not existing:
            # Notify student
            create_notification(
                db=db,
                user_id=student_id,
                type="milestone_overdue",
                title=f"Milestone overdue: {m_title}",
                body=f"Milestone '{m_title}' in project '{p_title}' is overdue. Please submit a check-in.",
                link=f"/applications/{app_id}/milestones/{milestone_id}",
            )
            # Notify company
            comp_member = db.execute(
                text(
                    "SELECT user_id FROM company_members WHERE company_id = :comp_id ORDER BY member_role = 'owner' DESC LIMIT 1"
                ),
                {"comp_id": company_id},
            ).fetchone()
            if comp_member:
                create_notification(
                    db=db,
                    user_id=comp_member[0],
                    type="milestone_overdue",
                    title=f"Student milestone overdue: {m_title}",
                    body=f"Milestone '{m_title}' in project '{p_title}' is overdue without an accepted check-in.",
                    link=f"/applications/{app_id}/milestones/{milestone_id}",
                )

            notified_count += 1

    return notified_count


def run_check_late_resubmissions(db: Session) -> int:
    """Fail applications where resubmission deadline (due_at + 3 days) has passed (FR-EVL-6, T-EVL-06).

    Returns count of failed applications.
    """
    rows = db.execute(
        text("""
            SELECT a.id, a.student_id, p.company_id, p.title as project_title
            FROM applications a
            JOIN projects p ON p.id = a.project_id
            WHERE a.status = 'changes_requested'
              AND a.due_at IS NOT NULL
              AND now() > a.due_at + interval '3 days'
        """)
    ).fetchall()

    failed_count = 0
    for app_id, student_id, company_id, p_title in rows:
        db.execute(
            text("""
                UPDATE applications
                SET status = 'failed', status_reason = 'Resubmission window expired', updated_at = now()
                WHERE id = :app_id
            """),
            {"app_id": app_id},
        )
        create_notification(
            db=db,
            user_id=student_id,
            type="application_failed",
            title="Project failed: Resubmission window expired",
            body=f"The resubmission window for project '{p_title}' has passed.",
            link=f"/student/applications/{app_id}/workspace",
        )
        failed_count += 1

    return failed_count


def run_daily_anomaly_scan(db: Session) -> int:
    """Run daily deterministic anomaly detection rules A1-A5 (FR-ADM-7).

    Returns count of newly opened anomaly flags.
    """
    from app.services.anomaly_detection import scan_anomalies

    res = scan_anomalies(db)
    return res.get("new_flags_opened", 0)
