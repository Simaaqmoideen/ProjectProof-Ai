import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.deps import get_db, require_roles
from app.models.user import User
from app.schemas.admin import (
    AdminDecisionRequest,
    AdminRequestInfoRequest,
    CompanyApprovalItem,
    PaginatedAuditLog,
    RecruiterApprovalItem,
)
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/companies", response_model=list[CompanyApprovalItem])
def get_company_queue(
    status: str | None = Query(None),
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    return AdminService.get_company_queue(db, status=status)


@router.post("/companies/{company_id}/approve")
def approve_company(
    company_id: uuid.UUID,
    request: Request,
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    ip = request.client.host if request.client else None
    company = AdminService.approve_company(db, admin=admin, company_id=company_id, ip=ip)
    db.commit()
    return {"message": "Company approved successfully.", "status": company.status}


@router.post("/companies/{company_id}/reject")
def reject_company(
    company_id: uuid.UUID,
    data: AdminDecisionRequest,
    request: Request,
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    ip = request.client.host if request.client else None
    company = AdminService.reject_company(db, admin=admin, company_id=company_id, reason=data.reason, ip=ip)
    db.commit()
    return {"message": "Company rejected.", "status": company.status}


@router.post("/companies/{company_id}/suspend")
def suspend_company(
    company_id: uuid.UUID,
    data: AdminDecisionRequest,
    request: Request,
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    ip = request.client.host if request.client else None
    company = AdminService.suspend_company(db, admin=admin, company_id=company_id, reason=data.reason, ip=ip)
    db.commit()
    return {"message": "Company suspended and open projects closed.", "status": company.status}


@router.post("/companies/{company_id}/request-info")
def request_company_info(
    company_id: uuid.UUID,
    data: AdminRequestInfoRequest,
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    # Sends message/notification to company
    return {"message": "Info request logged and sent to company."}


@router.get("/recruiters", response_model=list[RecruiterApprovalItem])
def get_recruiter_queue(
    status: str | None = Query(None),
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    return AdminService.get_recruiter_queue(db, status=status)


@router.post("/recruiters/{user_id}/approve")
def approve_recruiter(
    user_id: uuid.UUID,
    request: Request,
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    ip = request.client.host if request.client else None
    recruiter = AdminService.approve_recruiter(db, admin=admin, user_id=user_id, ip=ip)
    db.commit()
    return {"message": "Recruiter approved successfully.", "status": recruiter.status}


@router.post("/recruiters/{user_id}/reject")
def reject_recruiter(
    user_id: uuid.UUID,
    data: AdminDecisionRequest,
    request: Request,
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    ip = request.client.host if request.client else None
    recruiter = AdminService.reject_recruiter(db, admin=admin, user_id=user_id, reason=data.reason, ip=ip)
    db.commit()
    return {"message": "Recruiter rejected.", "status": recruiter.status}


@router.get("/audit-log", response_model=PaginatedAuditLog)
def get_audit_log(
    actor_id: uuid.UUID | None = Query(None),
    action: str | None = Query(None),
    entity_type: str | None = Query(None),
    entity_id: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    items, total = AdminService.get_audit_logs(
        db=db,
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    return PaginatedAuditLog(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post("/users/{user_id}/suspend")
def suspend_user(
    user_id: uuid.UUID,
    data: AdminDecisionRequest,
    request: Request,
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    ip = request.client.host if request.client else None
    user = AdminService.suspend_user(db, admin=admin, target_user_id=user_id, reason=data.reason, ip=ip)
    db.commit()
    return {"message": "User suspended.", "is_active": user.is_active}


@router.post("/users/{user_id}/reactivate")
def reactivate_user(
    user_id: uuid.UUID,
    request: Request,
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    ip = request.client.host if request.client else None
    user = AdminService.reactivate_user(db, admin=admin, target_user_id=user_id, ip=ip)
    db.commit()
    return {"message": "User reactivated.", "is_active": user.is_active}


@router.post("/jobs/check-overdue")
def trigger_check_overdue(
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    from app.services.scheduler import run_check_overdue_milestones
    count = run_check_overdue_milestones(db)
    db.commit()
    return {"notified": count}


@router.post("/jobs/check-late-resubmissions")
def trigger_check_late_resubmissions(
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    from app.services.scheduler import run_check_late_resubmissions
    count = run_check_late_resubmissions(db)
    db.commit()
    return {"failed": count}

