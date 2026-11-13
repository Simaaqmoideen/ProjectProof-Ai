import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.user import StudentProfile, User


class UserRepository:
    @staticmethod
    def get_by_id(db: Session, user_id: uuid.UUID) -> User | None:
        stmt = select(User).where(User.id == user_id)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_by_email(db: Session, email: str) -> User | None:
        stmt = select(User).where(User.email == email.strip().lower())
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def create_user(db: Session, email: str, password_hash: str, role: str) -> User:
        user = User(
            email=email.strip().lower(),
            password_hash=password_hash,
            role=role,
            is_active=True,
            email_verified_at=None,
        )
        db.add(user)
        db.flush()
        return user

    @staticmethod
    def create_student_profile(db: Session, user_id: uuid.UUID, full_name: str) -> StudentProfile:
        profile = StudentProfile(
            user_id=user_id,
            full_name=full_name,
            is_public=False,
            show_full_name_on_verification=True,
        )
        db.add(profile)
        db.flush()
        return profile

    @staticmethod
    def verify_email(db: Session, user_id: uuid.UUID) -> None:
        stmt = update(User).where(User.id == user_id).values(email_verified_at=datetime.now(UTC))
        db.execute(stmt)

    @staticmethod
    def update_last_login(db: Session, user_id: uuid.UUID) -> None:
        stmt = update(User).where(User.id == user_id).values(last_login_at=datetime.now(UTC))
        db.execute(stmt)

    @staticmethod
    def set_active_status(db: Session, user_id: uuid.UUID, is_active: bool) -> None:
        stmt = update(User).where(User.id == user_id).values(is_active=is_active)
        db.execute(stmt)

    @staticmethod
    def update_password(db: Session, user_id: uuid.UUID, password_hash: str) -> None:
        stmt = update(User).where(User.id == user_id).values(password_hash=password_hash)
        db.execute(stmt)
