import time
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.config import settings
from app.core.errors import (
    ConflictError,
    ForbiddenError,
    RateLimitedError,
    UnauthenticatedError,
    ValidationError,
)
from app.core.security import (
    create_access_token,
    create_email_verification_token,
    create_password_reset_token,
    decode_email_verification_token,
    decode_password_reset_token,
    generate_opaque_token,
    hash_password,
    hash_token,
    validate_password_strength,
    verify_password,
)
from app.models.user import User
from app.repositories.token_repo import TokenRepository
from app.repositories.user_repo import UserRepository
from app.services.audit_service import AuditService

# In-memory tracking for failed login attempts to satisfy T-AUTH-03
# { identifier: [timestamps] }
FAILED_ATTEMPTS: dict[str, list[float]] = {}
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_SECONDS = 60


def check_login_rate_limit(key: str) -> None:
    now = time.time()
    attempts = [t for t in FAILED_ATTEMPTS.get(key, []) if now - t < LOCKOUT_SECONDS]
    FAILED_ATTEMPTS[key] = attempts
    if len(attempts) >= MAX_FAILED_ATTEMPTS:
        raise RateLimitedError(
            message="Too many failed login attempts. Please wait before trying again."
        )


def record_failed_login(key: str) -> None:
    now = time.time()
    attempts = [t for t in FAILED_ATTEMPTS.get(key, []) if now - t < LOCKOUT_SECONDS]
    attempts.append(now)
    FAILED_ATTEMPTS[key] = attempts


def clear_failed_logins(key: str) -> None:
    FAILED_ATTEMPTS.pop(key, None)


class AuthService:
    @staticmethod
    def register(
        db: Session,
        email: str,
        password: str,
        role: str,
        full_name: str | None = None,
        organization: str | None = None,
        ip: str | None = None,
    ) -> tuple[User, str]:
        # FR-AUTH-6 & T-AUTH-06: Public sign-up with role=admin rejected
        if role == "admin" or role not in ("student", "company", "recruiter"):
            raise ForbiddenError("Cannot register as an admin through public signup.")

        # Password rules
        validate_password_strength(password)

        clean_email = email.strip().lower()
        existing = UserRepository.get_by_email(db, clean_email)
        if existing:
            raise ConflictError("An account with this email already exists.")

        pwd_hash = hash_password(password)
        user = UserRepository.create_user(db, email=clean_email, password_hash=pwd_hash, role=role)

        if role == "student":
            name = full_name.strip() if full_name else clean_email.split("@")[0]
            UserRepository.create_student_profile(db, user_id=user.id, full_name=name)

        verify_token = create_email_verification_token(str(user.id), clean_email)

        AuditService.log(
            db,
            action="user_registered",
            actor_id=user.id,
            entity_type="user",
            entity_id=str(user.id),
            detail={"role": role, "email": clean_email},
            ip=ip,
        )

        return user, verify_token

    @staticmethod
    def verify_email(db: Session, token: str, ip: str | None = None) -> User:
        payload = decode_email_verification_token(token)
        if not payload or not payload.get("sub"):
            raise ValidationError("Invalid or expired email verification link.")

        user_id = uuid.UUID(payload["sub"])
        user = UserRepository.get_by_id(db, user_id)
        if not user:
            raise ValidationError("Invalid verification token.")

        if user.email_verified_at is None:
            UserRepository.verify_email(db, user_id)
            user.email_verified_at = datetime.now(UTC)
            AuditService.log(
                db,
                action="email_verified",
                actor_id=user.id,
                entity_type="user",
                entity_id=str(user.id),
                detail={"email": user.email},
                ip=ip,
            )

        return user

    @staticmethod
    def login(
        db: Session,
        email: str,
        password: str,
        user_agent: str | None = None,
        ip: str | None = None,
    ) -> tuple[str, str, User]:
        clean_email = email.strip().lower()
        rate_limit_key = f"{ip or 'unknown'}:{clean_email}"
        check_login_rate_limit(rate_limit_key)

        user = UserRepository.get_by_email(db, clean_email)
        if not user or not verify_password(password, user.password_hash):
            record_failed_login(rate_limit_key)
            # T-AUTH-03: Message does not reveal whether the email exists
            raise UnauthenticatedError("Invalid email or password.")

        clear_failed_logins(rate_limit_key)

        if not user.is_active:
            raise ForbiddenError("Your account has been suspended. Please contact support.")

        email_verified = user.email_verified_at is not None
        access_token = create_access_token(str(user.id), user.role, email_verified)

        # Generate refresh token
        raw_refresh_token = generate_opaque_token()
        refresh_hash = hash_token(raw_refresh_token)
        expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_days)

        TokenRepository.create_refresh_token(
            db=db,
            user_id=user.id,
            token_hash=refresh_hash,
            expires_at=expires_at,
            user_agent=user_agent,
        )

        UserRepository.update_last_login(db, user.id)

        AuditService.log(
            db,
            action="login_success",
            actor_id=user.id,
            entity_type="user",
            entity_id=str(user.id),
            ip=ip,
        )

        return access_token, raw_refresh_token, user

    @staticmethod
    def refresh(
        db: Session,
        raw_refresh_token: str,
        user_agent: str | None = None,
        ip: str | None = None,
    ) -> tuple[str, str, User]:
        token_hash = hash_token(raw_refresh_token)
        token_record = TokenRepository.get_by_hash(db, token_hash)

        if not token_record:
            raise UnauthenticatedError("Invalid refresh token.")

        # T-AUTH-05: Reuse of a rotated refresh token revokes token family
        if token_record.revoked_at is not None:
            TokenRepository.revoke_all_user_tokens(db, token_record.user_id)
            AuditService.log(
                db,
                action="token_reuse_detected",
                actor_id=token_record.user_id,
                entity_type="refresh_token",
                entity_id=str(token_record.id),
                detail={"message": "Revoked all user refresh tokens due to token reuse"},
                ip=ip,
            )
            raise UnauthenticatedError("Refresh token has expired or been revoked.")

        now = datetime.now(UTC)
        if token_record.expires_at <= now:
            TokenRepository.revoke_token(db, token_record.id)
            raise UnauthenticatedError("Refresh token has expired.")

        user = UserRepository.get_by_id(db, token_record.user_id)
        if not user or not user.is_active:
            raise UnauthenticatedError("User is no longer active.")

        # T-AUTH-04: Rotate token
        TokenRepository.revoke_token(db, token_record.id)

        new_raw_refresh_token = generate_opaque_token()
        new_token_hash = hash_token(new_raw_refresh_token)
        expires_at = now + timedelta(days=settings.refresh_token_days)

        TokenRepository.create_refresh_token(
            db=db,
            user_id=user.id,
            token_hash=new_token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
        )

        email_verified = user.email_verified_at is not None
        new_access_token = create_access_token(str(user.id), user.role, email_verified)

        return new_access_token, new_raw_refresh_token, user

    @staticmethod
    def logout(db: Session, raw_refresh_token: str | None) -> None:
        if raw_refresh_token:
            token_hash = hash_token(raw_refresh_token)
            token_record = TokenRepository.get_by_hash(db, token_hash)
            if token_record and token_record.revoked_at is None:
                TokenRepository.revoke_token(db, token_record.id)

    @staticmethod
    def forgot_password(db: Session, email: str) -> str | None:
        clean_email = email.strip().lower()
        user = UserRepository.get_by_email(db, clean_email)
        if user and user.is_active:
            return create_password_reset_token(str(user.id), clean_email)
        return None

    @staticmethod
    def reset_password(db: Session, token: str, new_password: str, ip: str | None = None) -> None:
        payload = decode_password_reset_token(token)
        if not payload or not payload.get("sub"):
            raise ValidationError("Invalid or expired password reset link.")

        validate_password_strength(new_password)

        user_id = uuid.UUID(payload["sub"])
        user = UserRepository.get_by_id(db, user_id)
        if not user or not user.is_active:
            raise ValidationError("Invalid or expired password reset link.")

        pwd_hash = hash_password(new_password)
        UserRepository.update_password(db, user_id, pwd_hash)
        # Revoke all existing sessions
        TokenRepository.revoke_all_user_tokens(db, user_id)

        AuditService.log(
            db,
            action="password_reset",
            actor_id=user.id,
            entity_type="user",
            entity_id=str(user.id),
            ip=ip,
        )
