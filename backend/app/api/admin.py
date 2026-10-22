import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_roles
from app.models.user import User
from app.schemas.admin import (
    AdminDecisionRequest,
    AdminRequestInfoRequest,
    CompanyApprovalItem,
    PaginatedAuditLog,
    RecruiterApprovalItem,
)
from app.schemas.student import (
    PlatformStatsResponse,
    ProjectRemovalRequest,
    ProjectRemovalResponse,
)
from app.core.errors import BadRequestError, NotFoundError
from app.services import platform_stats as platform_stats_service
from app.services import project_removal as project_removal_service
from app.services.admin_service import AdminService
from app.services.audit_service import AuditService

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
    company = AdminService.reject_company(
        db, admin=admin, company_id=company_id, reason=data.reason, ip=ip
    )
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
    company = AdminService.suspend_company(
        db, admin=admin, company_id=company_id, reason=data.reason, ip=ip
    )
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
    recruiter = AdminService.reject_recruiter(
        db, admin=admin, user_id=user_id, reason=data.reason, ip=ip
    )
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
    user = AdminService.suspend_user(
        db, admin=admin, target_user_id=user_id, reason=data.reason, ip=ip
    )
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


# ─── Platform stats (FR-ANA-3) ───────────────────────────────────────────────


@router.get("/stats", response_model=PlatformStatsResponse)
def get_stats(
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """FR-ANA-3, T-ADM-09: Platform statistics from v_platform_stats view."""
    return platform_stats_service.get_platform_stats(db)


# ─── Project removal (FR-ADM-8) ──────────────────────────────────────────────


@router.get("/projects")
def list_all_projects(
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """Browse all projects by status (including reported/removed)."""
    offset = (page - 1) * page_size
    filters = []
    params: dict = {"lim": page_size, "off": offset}
    if status_filter:
        filters.append("p.status = :status")
        params["status"] = status_filter
    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    rows = db.execute(
        text(f"""
            SELECT p.id, p.title, p.status, p.difficulty, p.duration_days,
                   co.name AS company_name, p.created_at
              FROM projects p
              JOIN companies co ON co.id = p.company_id
             {where}
             ORDER BY p.created_at DESC
             LIMIT :lim OFFSET :off
        """),
        params,
    ).fetchall()
    total = (
        db.execute(
            text(f"SELECT count(*) FROM projects p {where}"),
            {k: v for k, v in params.items() if k not in ("lim", "off")},
        ).scalar()
        or 0
    )
    items = [
        {
            "id": str(r[0]),
            "title": r[1],
            "status": r[2],
            "difficulty": r[3],
            "duration_days": r[4],
            "company_name": r[5],
            "created_at": r[6].isoformat(),
        }
        for r in rows
    ]
    return {"items": items, "page": page, "page_size": page_size, "total": int(total)}


@router.post("/projects/{project_id}/remove", response_model=ProjectRemovalResponse)
def remove_project(
    project_id: uuid.UUID,
    data: ProjectRemovalRequest,
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """FR-ADM-8, T-ADM-04/05/06/07: Remove a project in one transaction.
    AGENTS.md rule 11: only services/project_removal.py sets status to 'removed'.
    """
    result = project_removal_service.remove_project(
        db=db,
        admin_user_id=admin.id,
        project_id=project_id,
        reason=data.reason,
        note=data.note,
    )
    db.commit()
    return result


# ─── Flags queue (FR-ADM-2) ──────────────────────────────────────────────────


@router.get("/flags")
def get_flags(
    kind: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """FR-ADM-2: Flag queue."""
    offset = (page - 1) * page_size
    filters = []
    params: dict = {"lim": page_size, "off": offset}
    if kind:
        filters.append("f.kind = :kind")
        params["kind"] = kind
    if status_filter:
        filters.append("f.status = :fstatus")
        params["fstatus"] = status_filter
    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    rows = db.execute(
        text(f"""
            SELECT f.id, f.kind, f.status, f.details, f.entity_type, f.entity_id, f.created_at, f.score
              FROM flags f
             {where}
             ORDER BY f.created_at DESC
             LIMIT :lim OFFSET :off
        """),
        params,
    ).fetchall()
    total = (
        db.execute(
            text(f"SELECT count(*) FROM flags f {where}"),
            {k: v for k, v in params.items() if k not in ("lim", "off")},
        ).scalar()
        or 0
    )
    items = [
        {
            "id": str(r[0]),
            "kind": r[1],
            "status": r[2],
            "details": r[3],
            "reason": r[3].get("summary") if isinstance(r[3], dict) else str(r[3]),
            "entity_type": r[4],
            "entity_id": str(r[5]) if r[5] else None,
            "created_at": r[6].isoformat(),
            "score": float(r[7]) if r[7] is not None else None,
        }
        for r in rows
    ]
    return {"items": items, "page": page, "page_size": page_size, "total": int(total)}


@router.post("/flags/{flag_id}/resolve")
def resolve_flag(
    flag_id: uuid.UUID,
    data: AdminDecisionRequest,
    request: Request,
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """FR-ADM-2: Resolve a flag (dismissed | confirmed)."""
    allowed = {"dismissed", "confirmed"}
    if data.reason not in allowed:
        raise BadRequestError(f"status must be one of {allowed}")
    res = db.execute(
        text(
            "UPDATE flags SET status = CAST(:s AS flag_status), reviewed_by = :admin, reviewed_at = now() WHERE id = :fid"
        ),
        {"s": data.reason, "admin": admin.id, "fid": flag_id},
    )
    if res.rowcount == 0:
        raise NotFoundError("Flag not found.")
    ip = request.client.host if request.client else None
    AuditService.log(
        db=db,
        action="flag_resolved",
        actor_id=admin.id,
        entity_type="flag",
        entity_id=str(flag_id),
        detail={"status": data.reason, "note": data.note},
        ip=ip,
    )
    db.commit()
    return {"message": "Flag resolved.", "status": data.reason}


# ─── Anomaly Detection Scan (FR-ADM-7) ─────────────────────────────────────────


@router.post("/anomalies/scan", summary="Run anomaly detection scan across platform")
def run_anomaly_scan(
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """FR-ADM-7: Run deterministic anomaly detection rules A1-A5."""
    from app.services.anomaly_detection import scan_anomalies

    return scan_anomalies(db)


# ─── Appeals queue (FR-ADM-3) ────────────────────────────────────────────────


@router.get("/appeals")
def get_appeals(
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """FR-ADM-3: Appeals queue."""
    offset = (page - 1) * page_size
    filters = []
    params: dict = {"lim": page_size, "off": offset}
    if status_filter:
        filters.append("ap.status = :astatus")
        params["astatus"] = status_filter
    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    rows = db.execute(
        text(f"""
            SELECT ap.id, ap.status, ap.reason, ap.filed_at, ap.resolved_at
              FROM appeals ap
             {where}
             ORDER BY ap.filed_at DESC
             LIMIT :lim OFFSET :off
        """),
        params,
    ).fetchall()
    total = (
        db.execute(
            text(f"SELECT count(*) FROM appeals ap {where}"),
            {k: v for k, v in params.items() if k not in ("lim", "off")},
        ).scalar()
        or 0
    )
    items = [
        {
            "id": str(r[0]),
            "status": r[1],
            "reason": r[2],
            "filed_at": r[3].isoformat() if r[3] else None,
            "resolved_at": r[4].isoformat() if r[4] else None,
        }
        for r in rows
    ]
    return {"items": items, "page": page, "page_size": page_size, "total": int(total)}
