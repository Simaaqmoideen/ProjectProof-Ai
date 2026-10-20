
from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.errors import UnauthenticatedError
from app.deps import get_current_user, get_db
from app.models.user import User
from app.repositories.company_repo import CompanyRepository
from app.repositories.recruiter_repo import RecruiterRepository
from app.schemas.auth import (
    CurrentUserResponse,
    EmailVerifyRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    RefreshResponse,
    ResetPasswordRequest,
    UserRegisterRequest,
    UserRegisterResponse,
    UserSummary,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="", tags=["Auth"])


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    max_age = settings.refresh_token_days * 24 * 3600
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=max_age,
        httponly=True,
        secure=(settings.environment != "development"),
        samesite="lax",
        path="/api/v1/auth",
    )


@router.post("/auth/register", response_model=UserRegisterResponse, status_code=status.HTTP_201_CREATED)
def register(
    data: UserRegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    ip = request.client.host if request.client else None
    user, _verify_token = AuthService.register(
        db=db,
        email=data.email,
        password=data.password,
        role=data.role,
        full_name=data.full_name,
        organization=data.organization,
        ip=ip,
    )
    db.commit()
    # In a real environment, send email with verify_token. For dev, we return created user.
    return UserRegisterResponse(
        id=user.id,
        role=user.role,
        email_verified=user.email_verified_at is not None,
    )


@router.post("/auth/verify-email")
def verify_email(
    data: EmailVerifyRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    ip = request.client.host if request.client else None
    AuthService.verify_email(db, data.token, ip=ip)
    db.commit()
    return {"message": "Email verified successfully.", "email_verified": True}


@router.post("/auth/login", response_model=LoginResponse)
def login(
    data: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    access_token, refresh_token, user = AuthService.login(
        db=db,
        email=data.email,
        password=data.password,
        user_agent=user_agent,
        ip=ip,
    )
    db.commit()

    set_refresh_cookie(response, refresh_token)

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserSummary(
            id=user.id,
            email=user.email,
            role=user.role,
            email_verified=user.email_verified_at is not None,
            is_active=user.is_active,
        ),
    )


@router.post("/auth/refresh", response_model=RefreshResponse)
def refresh_token_endpoint(
    request: Request,
    response: Response,
    refresh_token: str | None = Cookie(None),
    db: Session = Depends(get_db),
):
    if not refresh_token:
        raise UnauthenticatedError("Refresh token missing.")

    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    try:
        new_access_token, new_refresh_token, _ = AuthService.refresh(
            db=db,
            raw_refresh_token=refresh_token,
            user_agent=user_agent,
            ip=ip,
        )
        db.commit()
        set_refresh_cookie(response, new_refresh_token)
        return RefreshResponse(access_token=new_access_token, token_type="bearer")
    except Exception:
        db.commit()
        raise


@router.post("/auth/logout")
def logout(
    response: Response,
    refresh_token: str | None = Cookie(None),
    db: Session = Depends(get_db),
):
    AuthService.logout(db, refresh_token)
    db.commit()
    response.delete_cookie(key="refresh_token", path="/api/v1/auth")
    return {"message": "Logged out successfully."}


@router.post("/auth/forgot-password")
def forgot_password(
    data: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    # Always respond with the same message to prevent user enumeration
    AuthService.forgot_password(db, data.email)
    return {"message": "If an account exists with that email, a password reset link has been sent."}


@router.post("/auth/reset-password")
def reset_password(
    data: ResetPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    ip = request.client.host if request.client else None
    AuthService.reset_password(db, data.token, data.new_password, ip=ip)
    db.commit()
    return {"message": "Password reset successfully. You can now login with your new password."}


@router.get("/me", response_model=CurrentUserResponse)
def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile_data = None
    if current_user.role == "student" and current_user.student_profile:
        sp = current_user.student_profile
        profile_data = {
            "full_name": sp.full_name,
            "headline": sp.headline,
            "college": sp.college,
            "graduation_year": sp.graduation_year,
            "is_public": sp.is_public,
        }
    elif current_user.role == "company":
        company = CompanyRepository.get_by_user_id(db, current_user.id)
        if company:
            profile_data = {
                "id": str(company.id),
                "name": company.name,
                "status": company.status,
                "trust_score": company.trust_score,
                "website": company.website,
            }
    elif current_user.role == "recruiter":
        recruiter = RecruiterRepository.get_by_user_id(db, current_user.id)
        if recruiter:
            profile_data = {
                "full_name": recruiter.full_name,
                "organization": recruiter.organization,
                "status": recruiter.status,
            }

    return CurrentUserResponse(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role,
        is_active=current_user.is_active,
        email_verified=current_user.email_verified_at is not None,
        created_at=current_user.created_at,
        profile=profile_data,
    )
