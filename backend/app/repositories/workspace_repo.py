"""Workspace repository: parameterized SQL queries for workspace, check-ins and tasks.
See AGENTS.md rule 5 and docs/02-database-schema.md.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.orm import Session


class WorkspaceRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_application_with_project(self, application_id: uuid.UUID) -> dict | None:
        """Fetch application and project info."""
        row = (
            self.db.execute(
                text("""
                SELECT a.id, a.project_id, a.student_id, a.status, a.started_at, a.due_at, a.completed_at,
                       p.title as project_title, p.difficulty as project_difficulty, p.duration_days as project_duration_days,
                       p.company_id, c.name as company_name, sp.full_name as student_name
                FROM applications a
                JOIN projects p ON p.id = a.project_id
                JOIN companies c ON c.id = p.company_id
                JOIN student_profiles sp ON sp.user_id = a.student_id
                WHERE a.id = :app_id
            """),
                {"app_id": application_id},
            )
            .mappings()
            .fetchone()
        )
        return dict(row) if row else None

    def get_milestones_for_application(
        self, project_id: uuid.UUID, started_at: datetime | None
    ) -> list[dict]:
        """Fetch project milestones and compute due dates from started_at."""
        rows = (
            self.db.execute(
                text("""
                SELECT id, title, due_day_offset
                FROM milestones
                WHERE project_id = :project_id
                ORDER BY due_day_offset ASC
            """),
                {"project_id": project_id},
            )
            .mappings()
            .fetchall()
        )

        now = datetime.now(UTC)
        result = []
        for r in rows:
            m = dict(r)
            if started_at:
                import datetime as dt

                due_date = started_at + dt.timedelta(days=m["due_day_offset"])
                m["due_date"] = due_date
                m["is_overdue"] = due_date < now
            else:
                m["due_date"] = None
                m["is_overdue"] = False
            result.append(m)
        return result

    def get_tasks_for_application(
        self, application_id: uuid.UUID, milestone_ids: list[uuid.UUID]
    ) -> list[dict]:
        """Fetch company tasks and personal sub-tasks for this application with progress."""
        if not milestone_ids:
            return []
        rows = (
            self.db.execute(
                text("""
                SELECT t.id, t.milestone_id, t.title, t.description,
                       t.position AS order_index,
                       (t.application_id IS NOT NULL) as is_personal,
                       COALESCE(tp.status, 'todo') as status,
                       tp.completed_at
                FROM tasks t
                LEFT JOIN task_progress tp ON tp.task_id = t.id AND tp.application_id = :app_id
                WHERE t.milestone_id = ANY(:milestone_ids)
                  AND (t.application_id IS NULL OR t.application_id = :app_id)
                ORDER BY t.milestone_id, t.position ASC, t.created_at ASC
            """),
                {"app_id": application_id, "milestone_ids": milestone_ids},
            )
            .mappings()
            .fetchall()
        )
        return [dict(r) for r in rows]

    def get_checkins_for_application(self, application_id: uuid.UUID) -> list[dict]:
        """Fetch check-ins for the application."""
        rows = (
            self.db.execute(
                text("""
                SELECT id, milestone_id, note, evidence_url, status, submitted_at,
                       reviewed_by, reviewed_at, review_note
                FROM milestone_checkins
                WHERE application_id = :app_id
                ORDER BY submitted_at ASC
            """),
                {"app_id": application_id},
            )
            .mappings()
            .fetchall()
        )
        return [dict(r) for r in rows]

    def get_submissions_summary(self, application_id: uuid.UUID) -> list[dict]:
        """Fetch submissions list for this application."""
        rows = (
            self.db.execute(
                text("""
                SELECT id, version, repo_url, file_key, notes, submitted_at
                FROM submissions
                WHERE application_id = :app_id
                ORDER BY version ASC
            """),
                {"app_id": application_id},
            )
            .mappings()
            .fetchall()
        )
        return [dict(r) for r in rows]

    def create_checkin(
        self,
        application_id: uuid.UUID,
        milestone_id: uuid.UUID,
        note: str | None,
        evidence_url: str | None,
    ) -> uuid.UUID:
        checkin_id = uuid.uuid4()
        self.db.execute(
            text("""
                INSERT INTO milestone_checkins (id, application_id, milestone_id, note, evidence_url, status, submitted_at)
                VALUES (:id, :app_id, :milestone_id, :note, :evidence_url, 'submitted', now())
            """),
            {
                "id": checkin_id,
                "app_id": application_id,
                "milestone_id": milestone_id,
                "note": note,
                "evidence_url": evidence_url,
            },
        )
        return checkin_id

    def review_checkin(
        self,
        checkin_id: uuid.UUID,
        reviewer_id: uuid.UUID,
        status: str,
        review_note: str | None,
    ) -> bool:
        result = self.db.execute(
            text("""
                UPDATE milestone_checkins
                SET status = :status, reviewed_by = :reviewer_id, reviewed_at = now(), review_note = :review_note
                WHERE id = :checkin_id
            """),
            {
                "status": status,
                "reviewer_id": reviewer_id,
                "review_note": review_note,
                "checkin_id": checkin_id,
            },
        )
        return result.rowcount > 0

    def update_task_progress(
        self, application_id: uuid.UUID, task_id: uuid.UUID, status: str
    ) -> None:
        """Upsert task progress following CHECK ((status = 'done') = (completed_at IS NOT NULL))."""
        now = datetime.now(UTC)
        completed_at = now if status == "done" else None
        self.db.execute(
            text("""
                INSERT INTO task_progress (application_id, task_id, status, completed_at, updated_at)
                VALUES (:app_id, :task_id, :status, :completed_at, :now)
                ON CONFLICT (application_id, task_id)
                DO UPDATE SET
                    status = EXCLUDED.status,
                    completed_at = EXCLUDED.completed_at,
                    updated_at = EXCLUDED.updated_at
            """),
            {
                "app_id": application_id,
                "task_id": task_id,
                "status": status,
                "completed_at": completed_at,
                "now": now,
            },
        )

    def create_personal_task(
        self,
        application_id: uuid.UUID,
        milestone_id: uuid.UUID,
        title: str,
        description: str | None,
        created_by: uuid.UUID | None = None,
    ) -> uuid.UUID:
        task_id = uuid.uuid4()
        # Find next position (position must be > 0, starts at 1)
        max_pos = (
            self.db.execute(
                text("""
                SELECT COALESCE(MAX(position), 0)
                FROM tasks
                WHERE milestone_id = :milestone_id
                  AND (application_id IS NULL OR application_id = :app_id)
            """),
                {"milestone_id": milestone_id, "app_id": application_id},
            ).scalar()
            or 0
        )

        self.db.execute(
            text("""
                INSERT INTO tasks (id, milestone_id, application_id, title, description, position, created_by, created_at)
                VALUES (:id, :milestone_id, :app_id, :title, :description, :position, :created_by, now())
            """),
            {
                "id": task_id,
                "milestone_id": milestone_id,
                "app_id": application_id,
                "title": title,
                "description": description,
                "position": max_pos + 1,
                "created_by": created_by,
            },
        )
        # Initialize task_progress as todo
        self.db.execute(
            text("""
                INSERT INTO task_progress (application_id, task_id, status, completed_at, updated_at)
                VALUES (:app_id, :task_id, 'todo', NULL, now())
                ON CONFLICT DO NOTHING
            """),
            {"app_id": application_id, "task_id": task_id},
        )
        return task_id

    def delete_personal_task(
        self, application_id: uuid.UUID, task_id: uuid.UUID
    ) -> tuple[bool, str]:
        """Delete personal sub-task. If it is a company task, returns (False, 'company_task')."""
        task = self.db.execute(
            text("SELECT id, application_id FROM tasks WHERE id = :task_id"),
            {"task_id": task_id},
        ).fetchone()
        if not task:
            return False, "not_found"
        if task.application_id is None:
            return False, "company_task"  # Return 409
        if task.application_id != application_id:
            return False, "not_found"

        self.db.execute(
            text("DELETE FROM tasks WHERE id = :task_id AND application_id = :app_id"),
            {"task_id": task_id, "app_id": application_id},
        )
        return True, "deleted"
