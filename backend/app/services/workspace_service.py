"""Workspace service: business logic for workspace, milestones, checkins, and tasks.
See docs/01 FR-WRK-1 to 8, docs/04 Section 7, and docs/05 Section 4.
"""

import uuid

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.workspace_repo import WorkspaceRepository
from app.schemas.workspace import (
    CheckinItem,
    CreateCheckinRequest,
    CreatePersonalTaskRequest,
    MilestoneWorkspaceItem,
    ReviewCheckinRequest,
    SubmissionSummaryItem,
    TaskProgressItem,
    WorkspaceViewResponse,
)


class WorkspaceService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = WorkspaceRepository(db)

    def _check_access(self, current_user: User, app_data: dict) -> None:
        """Authorization rule: Role -> Ownership -> State. Other users get 404 (AGENTS.md rule 6)."""
        if current_user.role == "admin":
            return
        if current_user.role == "student":
            if app_data["student_id"] != current_user.id:
                raise HTTPException(status_code=404, detail="Application not found")
            return
        if current_user.role == "company":
            membership = self.db.execute(
                text(
                    "SELECT member_role FROM company_members WHERE company_id = :comp_id AND user_id = :user_id"
                ),
                {"comp_id": app_data["company_id"], "user_id": current_user.id},
            ).fetchone()
            if not membership:
                raise HTTPException(status_code=404, detail="Application not found")
            return
        raise HTTPException(status_code=404, detail="Application not found")

    def get_workspace(self, current_user: User, application_id: uuid.UUID) -> WorkspaceViewResponse:
        """GET /applications/{id}/workspace (FR-WRK-1, FR-WRK-7)."""
        app_data = self.repo.get_application_with_project(application_id)
        if not app_data:
            raise HTTPException(status_code=404, detail="Application not found")

        self._check_access(current_user, app_data)

        milestones_raw = self.repo.get_milestones_for_application(
            app_data["project_id"], app_data["started_at"]
        )
        milestone_ids = [m["id"] for m in milestones_raw]

        tasks_raw = self.repo.get_tasks_for_application(application_id, milestone_ids)
        checkins_raw = self.repo.get_checkins_for_application(application_id)
        submissions_raw = self.repo.get_submissions_summary(application_id)

        # Group tasks and checkins by milestone
        tasks_by_m = {m["id"]: [] for m in milestones_raw}
        for t in tasks_raw:
            tasks_by_m[t["milestone_id"]].append(TaskProgressItem(**t))

        checkins_by_m = {m["id"]: [] for m in milestones_raw}
        for c in checkins_raw:
            checkins_by_m[c["milestone_id"]].append(CheckinItem(**c))

        milestones_out = []
        for m in milestones_raw:
            milestones_out.append(
                MilestoneWorkspaceItem(
                    id=m["id"],
                    title=m["title"],
                    due_day_offset=m["due_day_offset"],
                    due_date=m["due_date"],
                    is_overdue=m["is_overdue"],
                    tasks=tasks_by_m.get(m["id"], []),
                    checkins=checkins_by_m.get(m["id"], []),
                )
            )

        submissions_out = [SubmissionSummaryItem(**s) for s in submissions_raw]

        return WorkspaceViewResponse(
            application_id=app_data["id"],
            project_id=app_data["project_id"],
            project_title=app_data["project_title"],
            project_difficulty=app_data["project_difficulty"],
            project_duration_days=app_data["project_duration_days"],
            company_id=app_data["company_id"],
            company_name=app_data["company_name"],
            student_id=app_data["student_id"],
            student_name=app_data["student_name"],
            status=app_data["status"],
            started_at=app_data["started_at"],
            due_at=app_data["due_at"],
            completed_at=app_data["completed_at"],
            milestones=milestones_out,
            submissions=submissions_out,
        )

    def create_checkin(
        self, current_user: User, application_id: uuid.UUID, req: CreateCheckinRequest
    ) -> uuid.UUID:
        """POST /applications/{id}/checkins (FR-WRK-2, T-WRK-02)."""
        app_data = self.repo.get_application_with_project(application_id)
        if not app_data:
            raise HTTPException(status_code=404, detail="Application not found")

        # Must be owner student (T-WRK-02: Student checks in on another student's application -> 404)
        if current_user.role != "student" or app_data["student_id"] != current_user.id:
            raise HTTPException(status_code=404, detail="Application not found")

        if app_data["status"] not in ("in_progress", "changes_requested"):
            raise HTTPException(
                status_code=409,
                detail=f"Cannot post check-in on an application with status '{app_data['status']}'",
            )

        # Verify milestone belongs to this project
        m_check = self.db.execute(
            text("SELECT id FROM milestones WHERE id = :m_id AND project_id = :p_id"),
            {"m_id": req.milestone_id, "p_id": app_data["project_id"]},
        ).fetchone()
        if not m_check:
            raise HTTPException(status_code=404, detail="Milestone not found in this project")

        checkin_id = self.repo.create_checkin(
            application_id=application_id,
            milestone_id=req.milestone_id,
            note=req.note,
            evidence_url=req.evidence_url,
        )
        self.db.commit()
        return checkin_id

    def review_checkin(
        self, current_user: User, checkin_id: uuid.UUID, req: ReviewCheckinRequest
    ) -> None:
        """POST /checkins/{id}/review (FR-WRK-3)."""
        checkin_row = self.db.execute(
            text("""
                SELECT k.id, k.application_id, p.company_id
                FROM milestone_checkins k
                JOIN applications a ON a.id = k.application_id
                JOIN projects p ON p.id = a.project_id
                WHERE k.id = :checkin_id
            """),
            {"checkin_id": checkin_id},
        ).fetchone()

        if not checkin_row:
            raise HTTPException(status_code=404, detail="Check-in not found")

        if current_user.role == "company":
            membership = self.db.execute(
                text(
                    "SELECT member_role FROM company_members WHERE company_id = :comp_id AND user_id = :user_id"
                ),
                {"comp_id": checkin_row.company_id, "user_id": current_user.id},
            ).fetchone()
            if not membership:
                raise HTTPException(status_code=404, detail="Check-in not found")
        elif current_user.role != "admin":
            raise HTTPException(status_code=404, detail="Check-in not found")

        self.repo.review_checkin(
            checkin_id=checkin_id,
            reviewer_id=current_user.id,
            status=req.status,
            review_note=req.review_note,
        )
        self.db.commit()

    def update_task_progress(
        self, current_user: User, application_id: uuid.UUID, task_id: uuid.UUID, status: str
    ) -> None:
        """PUT /applications/{id}/tasks/{task_id}/progress (FR-WRK-7)."""
        app_data = self.repo.get_application_with_project(application_id)
        if not app_data:
            raise HTTPException(status_code=404, detail="Application not found")

        if current_user.role != "student" or app_data["student_id"] != current_user.id:
            raise HTTPException(status_code=404, detail="Application not found")

        if app_data["status"] not in ("in_progress", "changes_requested"):
            raise HTTPException(
                status_code=409,
                detail=f"Cannot update task progress on application with status '{app_data['status']}'",
            )

        # Check task belongs to application's project milestone, or is a personal task
        task = self.db.execute(
            text("""
                SELECT t.id, t.application_id
                FROM tasks t
                JOIN milestones m ON m.id = t.milestone_id
                WHERE t.id = :task_id AND m.project_id = :project_id
            """),
            {"task_id": task_id, "project_id": app_data["project_id"]},
        ).fetchone()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Personal task cannot belong to another application
        if task.application_id is not None and task.application_id != application_id:
            raise HTTPException(status_code=404, detail="Task not found")

        self.repo.update_task_progress(application_id, task_id, status)
        self.db.commit()

    def create_personal_task(
        self,
        current_user: User,
        application_id: uuid.UUID,
        milestone_id: uuid.UUID,
        req: CreatePersonalTaskRequest,
    ) -> uuid.UUID:
        """POST /applications/{id}/milestones/{milestone_id}/tasks (FR-WRK-8)."""
        app_data = self.repo.get_application_with_project(application_id)
        if not app_data:
            raise HTTPException(status_code=404, detail="Application not found")

        if current_user.role != "student" or app_data["student_id"] != current_user.id:
            raise HTTPException(status_code=404, detail="Application not found")

        if app_data["status"] not in ("in_progress", "changes_requested"):
            raise HTTPException(
                status_code=409,
                detail=f"Cannot create personal task on application with status '{app_data['status']}'",
            )

        # Check milestone belongs to project
        m = self.db.execute(
            text("SELECT id FROM milestones WHERE id = :m_id AND project_id = :p_id"),
            {"m_id": milestone_id, "p_id": app_data["project_id"]},
        ).fetchone()
        if not m:
            raise HTTPException(status_code=404, detail="Milestone not found")

        task_id = self.repo.create_personal_task(
            application_id=application_id,
            milestone_id=milestone_id,
            title=req.title,
            description=req.description,
            created_by=current_user.id,
        )
        self.db.commit()
        return task_id

    def delete_personal_task(
        self, current_user: User, application_id: uuid.UUID, task_id: uuid.UUID
    ) -> None:
        """DELETE /applications/{id}/tasks/{task_id} (FR-WRK-8)."""
        app_data = self.repo.get_application_with_project(application_id)
        if not app_data:
            raise HTTPException(status_code=404, detail="Application not found")

        if current_user.role != "student" or app_data["student_id"] != current_user.id:
            raise HTTPException(status_code=404, detail="Application not found")

        success, reason = self.repo.delete_personal_task(application_id, task_id)
        if not success:
            if reason == "company_task":
                raise HTTPException(
                    status_code=409,
                    detail="Cannot delete company tasks. Only personal sub-tasks may be deleted.",
                )
            raise HTTPException(status_code=404, detail="Task not found")
        self.db.commit()
