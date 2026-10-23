from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from sqlalchemy import text
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
    """FR-ANA-2: Company statistics."""
    require_verified_email(current_user)
    company = CompanyService.get_company_by_user(db, current_user)
    cid = company.id

    row = db.execute(
        text("""
            SELECT
                (SELECT count(*) FROM projects WHERE company_id = :cid) AS projects_posted,
                (SELECT count(*) FROM applications a
                    JOIN projects p ON p.id = a.project_id
                    WHERE p.company_id = :cid AND a.status NOT IN ('applied','rejected','withdrawn')) AS students_selected,
                (SELECT count(*) FROM applications a
                    JOIN projects p ON p.id = a.project_id
                    WHERE p.company_id = :cid AND a.status = 'completed') AS projects_completed,
                (SELECT count(*) FROM projects WHERE company_id = :cid AND status = 'open') AS active_projects,
                (SELECT count(*) FROM submissions su
                    JOIN applications a ON a.id = su.application_id
                    JOIN projects p ON p.id = a.project_id
                    WHERE p.company_id = :cid AND su.id NOT IN (
                        SELECT submission_id FROM evaluations
                    )) AS pending_reviews
        """),
        {"cid": cid},
    ).fetchone()

    return CompanyStatsResponse(
        projects_posted=int(row[0]),
        students_selected=int(row[1]),
        projects_completed=int(row[2]),
        active_projects=int(row[3]),
        pending_reviews=int(row[4]),
    )
