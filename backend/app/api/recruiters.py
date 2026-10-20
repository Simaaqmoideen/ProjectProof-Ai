from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.deps import (
    get_db,
    require_approved_recruiter,
    require_roles,
    require_verified_email,
)
from app.models.user import User
from app.schemas.recruiter import RecruiterProfileRequest, RecruiterProfileResponse
from app.services.recruiter_service import RecruiterService

router = APIRouter(prefix="", tags=["Recruiters"])


@router.post("/recruiters", response_model=RecruiterProfileResponse, status_code=status.HTTP_201_CREATED)
def register_recruiter_profile(
    data: RecruiterProfileRequest,
    request: Request,
    current_user: User = Depends(require_roles("recruiter")),
    db: Session = Depends(get_db),
):
    require_verified_email(current_user)
    ip = request.client.host if request.client else None

    profile = RecruiterService.register_recruiter(
        db=db,
        user=current_user,
        full_name=data.full_name,
        organization=data.organization,
        ip=ip,
    )
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/recruiters/me", response_model=RecruiterProfileResponse)
def get_recruiter_profile(
    current_user: User = Depends(require_roles("recruiter")),
    db: Session = Depends(get_db),
):
    require_verified_email(current_user)
    return RecruiterService.get_profile(db, current_user)


@router.get("/recruiter/students")
def search_students(
    auth: tuple[User, any] = Depends(require_approved_recruiter),
    db: Session = Depends(get_db),
):
    """FR-ORG-6 & T-ORG-06: Unapproved recruiter searches returns 403."""
    return {"items": [], "total": 0, "page": 1, "page_size": 20}
