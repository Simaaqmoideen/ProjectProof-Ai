import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.user import RecruiterProfile, User


class RecruiterRepository:
    @staticmethod
    def get_by_user_id(db: Session, user_id: uuid.UUID) -> RecruiterProfile | None:
        stmt = select(RecruiterProfile).where(RecruiterProfile.user_id == user_id)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def create_profile(
        db: Session,
        user_id: uuid.UUID,
        full_name: str,
        organization: str,
        work_email_domain: str | None = None,
        status: str = "pending",
    ) -> RecruiterProfile:
        profile = RecruiterProfile(
            user_id=user_id,
            full_name=full_name,
            organization=organization,
            work_email_domain=work_email_domain.strip().lower() if work_email_domain else None,
            status=status,
        )
        db.add(profile)
        db.flush()
        return profile

    @staticmethod
    def update_status(
        db: Session,
        user_id: uuid.UUID,
        status: str,
        reviewed_by: uuid.UUID | None = None,
        rejection_reason: str | None = None,
    ) -> None:
        values = {
            "status": status,
            "reviewed_by": reviewed_by,
            "reviewed_at": datetime.now(UTC),
            "rejection_reason": rejection_reason,
        }
        stmt = update(RecruiterProfile).where(RecruiterProfile.user_id == user_id).values(**values)
        db.execute(stmt)

    @staticmethod
    def list_by_status(db: Session, status: str | None = None) -> list[tuple[RecruiterProfile, User]]:
        stmt = (
            select(RecruiterProfile, User)
            .join(User, User.id == RecruiterProfile.user_id)
        )
        if status:
            stmt = stmt.where(RecruiterProfile.status == status)
        stmt = stmt.order_by(RecruiterProfile.created_at.desc())
        return list(db.execute(stmt).all())
