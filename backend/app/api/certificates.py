"""Certificate API routes: verification, download, revocation requests, admin revocation, and student certificates.
See docs/04-api-specification.md Section 8 & 10, and docs/01 FR-CRT-1 to 6.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.rate_limit import check_rate_limit, get_client_ip
from app.db import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.certificate import (
    AdminRevocationCreate,
    CertificateResponse,
    PublicVerificationResponse,
    RevocationRequestCreate,
)
from app.services.certificate import (
    CertificateError,
    generate_certificate_pdf,
    get_public_verification,
    request_revocation,
    revoke_certificate,
)

router = APIRouter(tags=["certificates"])


@router.get(
    "/public/verify/{qr_token}",
    response_model=PublicVerificationResponse,
    summary="Public verification by QR token (live read, no-store)",
)
def verify_by_qr_token(
    qr_token: str,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Public verification route by QR token.

    AGENTS.md Rule 1: Always reads live from database view; Cache-Control: no-store.
    FR-CRT-6, T-CRT-15: Rate limited per IP (30/minute).
    """
    client_ip = get_client_ip(request)
    check_rate_limit(f"verify:{client_ip}", max_requests=30, window_seconds=60)

    # Rule 1: Verified means live; never cached
    response.headers["Cache-Control"] = "no-store"
    try:
        return get_public_verification(
            db, lookup_kind="qr", lookup_value=qr_token, client_ip=client_ip
        )
    except CertificateError as e:
        raise HTTPException(
            status_code=e.status_code, detail=e.message, headers={"Cache-Control": "no-store"}
        )


@router.get(
    "/public/verify-id/{verification_id}",
    response_model=PublicVerificationResponse,
    summary="Public verification by typed verification ID (live read, no-store)",
)
def verify_by_verification_id(
    verification_id: str,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Public verification route by typed verification ID."""
    client_ip = get_client_ip(request)
    check_rate_limit(f"verify:{client_ip}", max_requests=30, window_seconds=60)

    response.headers["Cache-Control"] = "no-store"
    try:
        return get_public_verification(
            db, lookup_kind="id", lookup_value=verification_id, client_ip=client_ip
        )
    except CertificateError as e:
        raise HTTPException(
            status_code=e.status_code, detail=e.message, headers={"Cache-Control": "no-store"}
        )


@router.get(
    "/certificates/{certificate_id}/pdf",
    summary="Download certificate PDF (FR-CRT-2, T-CRT-16)",
)
def download_certificate_pdf(
    certificate_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate and return certificate PDF."""
    try:
        pdf_bytes, filename = generate_certificate_pdf(
            db=db,
            certificate_id=certificate_id,
            requesting_user_id=current_user.id,
            requesting_role=current_user.role,
        )
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{filename}"'},
        )
    except CertificateError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post(
    "/certificates/{certificate_id}/revocation-request",
    status_code=status.HTTP_200_OK,
    summary="Company requests certificate revocation (FR-CRT-4, T-CRT-12)",
)
def request_certificate_revocation(
    certificate_id: uuid.UUID,
    req: RevocationRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Company requests revocation -> opens a flag; certificate unchanged."""
    try:
        return request_revocation(
            db=db,
            certificate_id=certificate_id,
            user_id=current_user.id,
            reason=req.reason,
            note=req.note or "",
        )
    except CertificateError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post(
    "/admin/certificates/{certificate_id}/revoke",
    status_code=status.HTTP_200_OK,
    summary="Admin revokes a certificate (FR-CRT-5, T-CRT-13, T-CRT-14)",
)
def admin_revoke_certificate(
    certificate_id: uuid.UUID,
    req: AdminRevocationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Admin revokes certificate, reverses XP, recalculates badges, audits, notifies."""
    try:
        return revoke_certificate(
            db=db,
            certificate_id=certificate_id,
            admin_id=current_user.id,
            reason=req.reason,
            note=req.note or "",
        )
    except CertificateError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get(
    "/students/me/certificates",
    response_model=list[CertificateResponse],
    summary="List all certificates for logged-in student",
)
def get_my_certificates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students have certificates")

    rows = db.execute(
        text("""
            SELECT c.id, c.application_id, c.verification_id, c.qr_token,
                   c.status, c.xp_awarded, c.issued_at, c.revoked_at, c.revocation_reason,
                   p.title as project_title, co.name as company_name
            FROM certificates c
            JOIN applications a ON a.id = c.application_id
            JOIN projects p ON p.id = a.project_id
            JOIN companies co ON co.id = p.company_id
            WHERE a.student_id = :student_id
            ORDER BY c.issued_at DESC
        """),
        {"student_id": current_user.id},
    ).fetchall()

    return [
        CertificateResponse(
            id=r.id,
            application_id=r.application_id,
            verification_id=r.verification_id,
            qr_token=r.qr_token,
            status=r.status,
            xp_awarded=r.xp_awarded,
            project_title=r.project_title,
            company_name=r.company_name,
            issued_at=r.issued_at,
            revoked_at=r.revoked_at,
            revocation_reason=r.revocation_reason,
        )
        for r in rows
    ]


@router.get(
    "/students/me/progress",
    summary="Get gamification progress: XP, level, badges (FR-RWD-2, FR-RWD-3, BR-4, BR-5)",
)
def get_my_progress(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students have progress")

    # Read live from v_student_progress view
    prog = db.execute(
        text("SELECT total_xp, level FROM v_student_progress WHERE student_id = :sid"),
        {"sid": current_user.id},
    ).fetchone()

    total_xp = prog.total_xp if prog else 0
    current_lvl = prog.level if prog else 1

    # Fetch level definition and next level
    levels = db.execute(
        text("SELECT level, name, min_xp FROM levels ORDER BY level ASC")
    ).fetchall()
    lvl_map = {r.level: {"name": r.name, "min_xp": r.min_xp} for r in levels}

    current_lvl_info = lvl_map.get(current_lvl, {"name": "Starter", "min_xp": 0})
    next_lvl = current_lvl + 1 if (current_lvl + 1) in lvl_map else None
    next_lvl_info = lvl_map.get(next_lvl) if next_lvl else None

    xp_to_next = (next_lvl_info["min_xp"] - total_xp) if next_lvl_info else 0

    # Badges earned
    badges_rows = db.execute(
        text("""
            SELECT b.code, b.name, b.description, sb.awarded_at
            FROM student_badges sb
            JOIN badges b ON b.id = sb.badge_id
            WHERE sb.student_id = :sid
            ORDER BY sb.awarded_at ASC
        """),
        {"sid": current_user.id},
    ).fetchall()

    badges = [
        {
            "code": b.code,
            "name": b.name,
            "description": b.description,
            "awarded_at": b.awarded_at.isoformat(),
        }
        for b in badges_rows
    ]

    # Completed projects count
    completed_projects = (
        db.execute(
            text("""
            SELECT count(c.id) FROM certificates c
            JOIN applications a ON a.id = c.application_id
            WHERE a.student_id = :sid AND c.status = 'issued'
        """),
            {"sid": current_user.id},
        ).scalar()
        or 0
    )

    return {
        "student_id": current_user.id,
        "total_xp": total_xp,
        "level": current_lvl,
        "level_name": current_lvl_info["name"],
        "min_xp": current_lvl_info["min_xp"],
        "next_level": next_lvl,
        "next_level_name": next_lvl_info["name"] if next_lvl_info else None,
        "next_level_xp": next_lvl_info["min_xp"] if next_lvl_info else None,
        "xp_to_next_level": max(0, xp_to_next),
        "completed_projects": completed_projects,
        "badges": badges,
    }
