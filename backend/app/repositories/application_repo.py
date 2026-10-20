"""Application repository — parameterised queries only (AGENTS.md rule 5).
FR-APP-1 to FR-APP-10.
"""
import uuid
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.application import Application


class ApplicationRepository:
    @staticmethod
    def get_by_id(db: Session, application_id: uuid.UUID) -> Application | None:
        return db.execute(
            select(Application).where(Application.id == application_id)
        ).scalar_one_or_none()

    @staticmethod
    def get_by_student_and_project(
        db: Session,
        student_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> Application | None:
        return db.execute(
            select(Application).where(
                Application.student_id == student_id,
                Application.project_id == project_id,
            )
        ).scalar_one_or_none()

    @staticmethod
    def count_active_for_student(db: Session, student_id: uuid.UUID) -> int:
        """FR-APP-1: Student cannot have more than 3 active applications."""
        return db.execute(
            select(func.count(Application.id)).where(
                Application.student_id == student_id,
                Application.status.in_(["in_progress", "submitted", "changes_requested"]),
            )
        ).scalar_one()

    @staticmethod
    def list_for_student(
        db: Session,
        student_id: uuid.UUID,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Application], int]:
        stmt = select(Application).where(Application.student_id == student_id)
        if status:
            stmt = stmt.where(Application.status == status)
        total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        stmt = stmt.order_by(Application.applied_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        return list(db.execute(stmt).scalars().all()), total

    @staticmethod
    def list_for_project(
        db: Session,
        project_id: uuid.UUID,
        status: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Application], int]:
        stmt = select(Application).where(Application.project_id == project_id)
        if status:
            stmt = stmt.where(Application.status == status)
        total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        stmt = stmt.order_by(Application.match_score.desc().nulls_last(), Application.applied_at.asc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        return list(db.execute(stmt).scalars().all()), total

    @staticmethod
    def count_selected_for_project(db: Session, project_id: uuid.UUID) -> int:
        """FR-APP-5: Count already selected applications for a project."""
        return db.execute(
            select(func.count(Application.id)).where(
                Application.project_id == project_id,
                Application.status == "in_progress",
            )
        ).scalar_one()

    @staticmethod
    def update_status(
        db: Session,
        application_id: uuid.UUID,
        status: str,
        decided_at: datetime | None = None,
        decided_by: uuid.UUID | None = None,
        status_reason: str | None = None,
        started_at: datetime | None = None,
        due_at: datetime | None = None,
    ) -> None:
        values: dict = {"status": status}
        if decided_at is not None:
            values["decided_at"] = decided_at
        if decided_by is not None:
            values["decided_by"] = decided_by
        if status_reason is not None:
            values["status_reason"] = status_reason
        if started_at is not None:
            values["started_at"] = started_at
        if due_at is not None:
            values["due_at"] = due_at
        db.execute(update(Application).where(Application.id == application_id).values(**values))
