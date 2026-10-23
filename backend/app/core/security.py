import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.config import settings
from app.core.errors import ValidationError

# Password hasher using Argon2id
ph = PasswordHasher()

COMMON_PASSWORDS = {
    "password",
    "password123",
    "1234567890",
    "qwertyuiop",
    "admin12345",
    "letmein123",
    "welcome123",
    "iloveyou12",
    "monkey1234",
    "dragon1234",
    "master1234",
    "football12",
    "shadow1234",
    "princess12",
    "superman12",
}


def validate_password_strength(password: str) -> None:
    if len(password) < 10:
        raise ValidationError(
            message="Password must be at least 10 characters long.",
            details=[{"field": "password", "issue": "minimum_length_10"}],
        )
    if password.lower() in COMMON_PASSWORDS:
        raise ValidationError(
            message="Password is too common. Please choose a more secure password.",
            details=[{"field": "password", "issue": "password_too_common"}],
        )


def hash_password(password: str) -> str:
    return ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return ph.verify(hashed_password, plain_password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def hash_token(token: str) -> str:
    """Hash opaque tokens (e.g. refresh tokens) for DB storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_opaque_token() -> str:
    return secrets.token_urlsafe(48)


def create_access_token(user_id: str, role: str, email_verified: bool) -> str:
    now = datetime.now(UTC)
    expires = now + timedelta(minutes=settings.access_token_minutes)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "email_verified": email_verified,
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != "access":
            return None
        return payload
    except Exception:
        return None


def create_email_verification_token(user_id: str, email: str) -> str:
    now = datetime.now(UTC)
    expires = now + timedelta(hours=settings.email_verification_token_hours)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
        "type": "email_verify",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_email_verification_token(token: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != "email_verify":
            return None
        return payload
    except Exception:
        return None


def create_password_reset_token(user_id: str, email: str) -> str:
    now = datetime.now(UTC)
    expires = now + timedelta(hours=settings.password_reset_token_hours)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
        "type": "password_reset",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_password_reset_token(token: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != "password_reset":
            return None
        return payload
    except Exception:
        return None
