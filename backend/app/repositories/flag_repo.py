"""Database access for project and administrative flags."""

import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session


class FlagRepository:
    @staticmethod
    def create_project_report(
        db: Session, flag_id: uuid.UUID, project_id: uuid.UUID, details_json: str
    ) -> None:
        db.execute(
            text("""
                INSERT INTO flags (id, kind, entity_type, entity_id, details, status, created_at)
                VALUES (:id, 'manual', 'project', :entity_id, CAST(:details AS jsonb), 'open', now())
            """),
            {"id": flag_id, "entity_id": project_id, "details": details_json},
        )

    @staticmethod
    def resolve_open(db: Session, flag_id: uuid.UUID, admin_id: uuid.UUID, status: str):
        return db.execute(
            text("""
                UPDATE flags
                   SET status = CAST(:status AS flag_status), reviewed_by = :admin, reviewed_at = now()
                 WHERE id = :flag_id AND status = 'open'
            """),
            {"status": status, "admin": admin_id, "flag_id": flag_id},
        )

    @staticmethod
    def get_status(db: Session, flag_id: uuid.UUID) -> str | None:
        return db.execute(
            text("SELECT status FROM flags WHERE id = :flag_id"), {"flag_id": flag_id}
        ).scalar_one_or_none()
