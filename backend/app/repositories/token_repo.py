import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.user import RefreshToken


class TokenRepository:
    @staticmethod
    def create_refresh_token(
        db: Session,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
        user_agent: str | None = None,
    ) -> RefreshToken:
        token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
        )
        db.add(token)
        db.flush()
        return token

    @staticmethod
    def get_by_hash(db: Session, token_hash: str) -> RefreshToken | None:
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def revoke_token(db: Session, token_id: uuid.UUID) -> None:
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.id == token_id)
            .values(revoked_at=datetime.now(UTC))
        )
        db.execute(stmt)

    @staticmethod
    def revoke_all_user_tokens(db: Session, user_id: uuid.UUID) -> None:
        """Revokes token family for this user if reuse is detected (T-AUTH-05)."""
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
        db.execute(stmt)
