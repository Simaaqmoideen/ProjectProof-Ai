"""Student profile lookups used by services."""

import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session


class StudentRepository:
    @staticmethod
    def get_public_name_preferences(db: Session, student_user_id: uuid.UUID):
        return db.execute(
            text("""
                SELECT full_name, show_full_name_on_verification
                  FROM student_profiles WHERE user_id = :uid
            """),
            {"uid": student_user_id},
        ).fetchone()
