
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.deps import get_db, require_roles, require_verified_email
from app.models.user import User
from app.schemas.company import (
    CompanyRegisterRequest,
    CompanyResponse,
    CompanyStatsResponse,
    CompanyUpdateRequest,
)
from app.services.company_service import CompanyService

router = APIRouter(prefix="/companies", tags=["Companies"])


@router.post("", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def register_company(
    request: Request,
    name: str = Form(...),
    website: str | None = Form(None),
    description: str | None = Form(None),
    document: UploadFile | None = File(None),
    current_user: User = Depends(require_roles("company")),
    db: Session = Depends(get_db),
):
    require_verified_email(current_user)
    ip = request.client.host if request.client else None

    # Handle document upload if provided
    doc_key = None
    if document and document.filename:
        # In local storage, save key
        doc_key = f"docs/{current_user.id}_{document.filename}"

    company = CompanyService.register_company(
        db=db,
        user=current_user,
        name=name,
        website=website,
        description=description,
        registration_doc_key=doc_key,
        ip=ip,
    )
    db.commit()
    db.refresh(company)
    return company


@router.post("/json", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
def register_company_json(
    data: CompanyRegisterRequest,
    request: Request,
    current_user: User = Depends(require_roles("company")),
    db: Session = Depends(get_db),
):
    require_verified_email(current_user)
    ip = request.client.host if request.client else None

    company = CompanyService.register_company(
        db=db,
        user=current_user,
        name=data.name,
        website=data.website,
        description=data.description,
        registration_doc_key=None,
        ip=ip,
    )
    db.commit()
    db.refresh(company)
    return company


@router.get("/me", response_model=CompanyResponse)
def get_my_company(
    current_user: User = Depends(require_roles("company")),
    db: Session = Depends(get_db),
):
    require_verified_email(current_user)
    return CompanyService.get_company_by_user(db, current_user)


@router.put("/me", response_model=CompanyResponse)
def update_my_company(
    data: CompanyUpdateRequest,
    request: Request,
    current_user: User = Depends(require_roles("company")),
    db: Session = Depends(get_db),
):
    require_verified_email(current_user)
    ip = request.client.host if request.client else None
    company = CompanyService.update_company(
        db=db,
        user=current_user,
        description=data.description,
        website=data.website,
        ip=ip,
    )
    db.commit()
    return company


@router.get("/me/stats", response_model=CompanyStatsResponse)
def get_company_stats(
    current_user: User = Depends(require_roles("company")),
    db: Session = Depends(get_db),
):
    require_verified_email(current_user)
    CompanyService.get_company_by_user(db, current_user)
    # Default stats
    return CompanyStatsResponse()
