import uuid
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.errors import ForbiddenError, UnauthenticatedError
from app.core.security import decode_access_token
from app.db import get_db
from app.models.user import User
from app.repositories.company_repo import CompanyRepository
from app.repositories.recruiter_repo import RecruiterRepository
from app.repositories.user_repo import UserRepository


def get_current_user(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthenticatedError("Missing or invalid Authorization header.")

    token = authorization.split(" ", 1)[1].strip()
    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        raise UnauthenticatedError("Invalid or expired access token.")

    try:
        user_id = uuid.UUID(payload["sub"])
    except (ValueError, TypeError):
        raise UnauthenticatedError("Invalid user ID in token.")

    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise UnauthenticatedError("User not found.")

    if not user.is_active:
        raise ForbiddenError("Account is suspended.")

    return user


def require_verified_email(user: User = Depends(get_current_user)) -> User:
    """FR-AUTH-2 & T-AUTH-02: Email must be verified before acting beyond viewing profile."""
    if user.email_verified_at is None:
        raise ForbiddenError("Please verify your email address to perform this action.")
    return user


def require_roles(*allowed_roles: str) -> Callable[[User], User]:
    def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise ForbiddenError(f"Action not permitted for role '{user.role}'.")
        return user

    return role_checker


def require_approved_company(
    user: User = Depends(require_roles("company")),
    db: Session = Depends(get_db),
) -> tuple[User, any]:
    """FR-ORG-2 & T-ORG-01: Pending company cannot publish or act as approved."""
    require_verified_email(user)
    company = CompanyRepository.get_by_user_id(db, user.id)
    if not company:
        raise ForbiddenError("No company profile registered.")
    if company.status != "approved":
        raise ForbiddenError(f"Company status is '{company.status}'. Admin approval required.")
    return user, company


def require_approved_recruiter(
    user: User = Depends(require_roles("recruiter")),
    db: Session = Depends(get_db),
) -> tuple[User, any]:
    """FR-ORG-6 & T-ORG-06: Unapproved recruiter cannot search."""
    require_verified_email(user)
    recruiter = RecruiterRepository.get_by_user_id(db, user.id)
    if not recruiter:
        raise ForbiddenError("No recruiter profile registered.")
    if recruiter.status != "approved":
        raise ForbiddenError(f"Recruiter status is '{recruiter.status}'. Admin approval required.")
    return user, recruiter
