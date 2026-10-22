"""Certificates service: the ONLY place where certificates are created or revoked.

See AGENTS.md rule 3 and docs/03-tech-stack-and-architecture.md section 5.
"""

import hashlib
import io
import json as _json
import time
import uuid
from datetime import UTC, datetime

import qrcode
from pypdf import PdfReader  # noqa: F401
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.core.ids import compute_certificate_hash, generate_qr_token, generate_verification_id
from app.services.badges import recalculate_student_badges
from app.services.notifications import create_notification
from app.services.trust_score import adjust_company_trust_score, on_evaluation_completed
from app.services.xp import compute_xp


class CertificateError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def verification_display_name(
    full_name: str, show_full_name: bool, *, first_initial_only: bool = False
) -> str:
    """FR-STU-6: Apply the student's name privacy preference."""
    if show_full_name:
        return full_name
    if first_initial_only:
        return f"{full_name[:1]}."
    parts = full_name.strip().split()
    if len(parts) >= 2:
        return f"{parts[0][:1]}. {parts[-1][:1]}."
    if parts:
        return f"{parts[0][:1]}."
    return "Student"


def issue_certificate_for_application(
    db: Session,
    application_id: uuid.UUID,
    reviewer_id: uuid.UUID,
    overall_score: int,
    rubric_scores: dict | None = None,
    feedback: str = "",
    public_summary: str | None = None,
    used_ai_draft: bool = False,
) -> dict:
    """Issue a certificate for an application within an atomic database transaction.

    AGENTS.md Rule 3:
    Only services/certificate.py creates or revokes certificates, inside a single database transaction.
    """
    if overall_score < 60:
        raise CertificateError("Overall score below 60 cannot be approved", status_code=409)

    # 1. Lock the application row and fetch project, company and student details
    app_row = db.execute(
        text("""
            SELECT a.id, a.project_id, a.student_id, a.status, a.started_at,
                   p.company_id, p.duration_days, p.difficulty, p.title as project_title,
                   sp.full_name as student_name
            FROM applications a
            JOIN projects p ON p.id = a.project_id
            JOIN student_profiles sp ON sp.user_id = a.student_id
            WHERE a.id = :app_id
            FOR UPDATE OF a
        """),
        {"app_id": application_id},
    ).fetchone()

    if not app_row:
        raise CertificateError("Application not found", status_code=404)

    # Check reviewer belongs to the project's company
    reviewer_membership = db.execute(
        text("""
            SELECT member_role FROM company_members
            WHERE company_id = :company_id AND user_id = :reviewer_id
        """),
        {"company_id": app_row.company_id, "reviewer_id": reviewer_id},
    ).fetchone()

    # Also check if reviewer is an admin
    reviewer_user = db.execute(
        text("SELECT role FROM users WHERE id = :user_id"),
        {"user_id": reviewer_id},
    ).fetchone()

    if not reviewer_membership and (not reviewer_user or reviewer_user.role != "admin"):
        raise CertificateError("Reviewer does not belong to the project company", status_code=404)

    # Check if certificate already exists (idempotency / double-click protection: T-CRT-02)
    existing_cert = db.execute(
        text(
            "SELECT id, verification_id, qr_token, status, xp_awarded FROM certificates WHERE application_id = :app_id"
        ),
        {"app_id": application_id},
    ).fetchone()
    if existing_cert:
        return {
            "certificate_id": existing_cert.id,
            "verification_id": existing_cert.verification_id,
            "qr_token": existing_cert.qr_token,
            "xp_awarded": existing_cert.xp_awarded,
            "status": existing_cert.status,
            "application_status": app_row.status,
        }

    if app_row.status not in ("submitted", "in_progress", "changes_requested"):
        raise CertificateError(
            f"Cannot approve application with status '{app_row.status}'", status_code=409
        )

    # Fetch project skills for hash
    skills_rows = db.execute(
        text("""
            SELECT s.name FROM project_skills ps
            JOIN skills s ON s.id = ps.skill_id
            WHERE ps.project_id = :project_id
        """),
        {"project_id": app_row.project_id},
    ).fetchall()
    skill_names = [r[0] for r in skills_rows]

    # Compute XP using business rule formula
    xp_amount = compute_xp(
        duration_days=app_row.duration_days,
        difficulty=app_row.difficulty,
        overall_score=overall_score,
    )

    now = datetime.now(UTC)

    # Set application.status = 'completed', completed_at = now
    # (Trigger certificate_requires_completed requires this before inserting certificate)
    db.execute(
        text("""
            UPDATE applications
            SET status = 'completed', completed_at = :now, updated_at = :now
            WHERE id = :app_id
        """),
        {"app_id": application_id, "now": now},
    )

    # Generate verification_id (with retry on collision) and qr_token
    cert_id = uuid.uuid4()
    qr_token = generate_qr_token()
    content_hash = compute_certificate_hash(
        student_id=app_row.student_id,
        project_id=app_row.project_id,
        company_id=app_row.company_id,
        completed_at=now,
        skills=skill_names,
        overall_score=overall_score,
    )

    inserted = False
    verification_id = ""
    for _ in range(10):
        verification_id = generate_verification_id(now.year)
        try:
            db.execute(
                text("""
                    INSERT INTO certificates (
                        id, application_id, verification_id, qr_token, status,
                        xp_awarded, content_hash, issued_at
                    ) VALUES (
                        :id, :app_id, :ver_id, :qr_token, 'issued',
                        :xp_awarded, :hash, :now
                    )
                """),
                {
                    "id": cert_id,
                    "app_id": application_id,
                    "ver_id": verification_id,
                    "qr_token": qr_token,
                    "xp_awarded": xp_amount,
                    "hash": content_hash,
                    "now": now,
                },
            )
            inserted = True
            break
        except IntegrityError as e:
            if "verification_id" in str(e):
                continue
            raise

    if not inserted:
        raise CertificateError("Failed to generate unique verification ID", status_code=500)

    # Insert xp_events row
    db.execute(
        text("""
            INSERT INTO xp_events (student_id, certificate_id, amount, reason, created_at)
            VALUES (:student_id, :cert_id, :amount, 'project_completed', :now)
        """),
        {
            "student_id": app_row.student_id,
            "cert_id": cert_id,
            "amount": xp_amount,
            "now": now,
        },
    )

    # Recalculate badges from issued certificates
    recalculate_student_badges(db, app_row.student_id)

    # Audit log (administrative / company state change) — FR-ADM-5
    db.execute(
        text("""
            INSERT INTO audit_log (actor_id, action, entity_type, entity_id, detail, created_at)
            VALUES (:actor_id, 'issue_certificate', 'certificate', :cert_id, CAST(:detail AS jsonb), :now)
        """),
        {
            "actor_id": reviewer_id,
            "cert_id": str(cert_id),
            "detail": _json.dumps(
                {
                    "verification_id": verification_id,
                    "xp_awarded": xp_amount,
                    "score": overall_score,
                }
            ),
            "now": now,
        },
    )

    # Notifications
    create_notification(
        db=db,
        user_id=app_row.student_id,
        type="certificate_issued",
        title="Certificate Issued!",
        body=f"Your work on '{app_row.project_title}' has been approved with a score of {overall_score}/100. Verification ID: {verification_id}",
        link=f"/student/certificates/{cert_id}",
    )

    # Adjust trust score for company if submission evaluated within 5 days
    latest_sub = db.execute(
        text(
            "SELECT submitted_at FROM submissions WHERE application_id = :app_id ORDER BY version DESC LIMIT 1"
        ),
        {"app_id": application_id},
    ).fetchone()
    if latest_sub and latest_sub.submitted_at:
        on_evaluation_completed(db, app_row.company_id, latest_sub.submitted_at, now)

    return {
        "certificate_id": cert_id,
        "verification_id": verification_id,
        "qr_token": qr_token,
        "xp_awarded": xp_amount,
        "status": "issued",
        "application_status": "completed",
    }


def revoke_certificate(
    db: Session,
    certificate_id: uuid.UUID,
    admin_id: uuid.UUID,
    reason: str,
    note: str = "",
) -> dict:
    """Revoke a certificate inside a single transaction.

    AGENTS.md Rule 3: Only services/certificate.py creates or revokes certificates.
    T-CRT-13: Non-admin calls revoke -> 403.
    T-CRT-14: Admin revokes -> Negative XP event; badges recalculated; audit; notifications.
    T-RWD-05: Revocation drops a student below a badge threshold -> Badge removed.
    BR-6: minus 20 trust score for each certificate revoked for company error or fraud.
    """
    # 1. Verify caller is an admin
    admin_user = db.execute(
        text("SELECT role FROM users WHERE id = :user_id"),
        {"user_id": admin_id},
    ).fetchone()
    if not admin_user or admin_user[0] != "admin":
        raise CertificateError("Only administrators can revoke certificates", status_code=403)

    valid_reasons = {"fraud", "plagiarism", "evaluation_overturned", "company_error", "other"}
    if reason not in valid_reasons:
        raise CertificateError(f"Invalid revocation reason: '{reason}'", status_code=400)

    # 2. Lock certificate and fetch related application and student
    cert_row = db.execute(
        text("""
            SELECT c.id, c.verification_id, c.status, c.xp_awarded,
                   a.student_id, a.id as application_id,
                   p.company_id, p.title as project_title
            FROM certificates c
            JOIN applications a ON a.id = c.application_id
            JOIN projects p ON p.id = a.project_id
            WHERE c.id = :cert_id
            FOR UPDATE OF c
        """),
        {"cert_id": certificate_id},
    ).fetchone()

    if not cert_row:
        raise CertificateError("Certificate not found", status_code=404)

    if cert_row.status == "revoked":
        raise CertificateError("Certificate is already revoked", status_code=409)

    now = datetime.now(UTC)

    # 3. Update certificate to revoked
    db.execute(
        text("""
            UPDATE certificates
            SET status = 'revoked',
                revoked_at = :now,
                revoked_by = :admin_id,
                revocation_reason = CAST(:reason AS revocation_reason),
                revocation_note = :note
            WHERE id = :cert_id
        """),
        {
            "cert_id": certificate_id,
            "now": now,
            "admin_id": admin_id,
            "reason": reason,
            "note": note or None,
        },
    )

    # 4. Insert negative XP event (amount = -xp_awarded)
    db.execute(
        text("""
            INSERT INTO xp_events (student_id, certificate_id, amount, reason, created_at)
            VALUES (:student_id, :cert_id, :neg_amount, 'certificate_revoked', :now)
        """),
        {
            "student_id": cert_row.student_id,
            "cert_id": certificate_id,
            "neg_amount": -cert_row.xp_awarded,
            "now": now,
        },
    )

    # 5. Recalculate badges (removes badges if student drops below threshold)
    recalculate_student_badges(db, cert_row.student_id)

    # 6. Adjust company trust score if company error or fraud (BR-6)
    if reason in ("company_error", "fraud"):
        adjust_company_trust_score(
            db, cert_row.company_id, -settings.trust_score_revocation_penalty
        )

    # 7. Audit log
    db.execute(
        text("""
            INSERT INTO audit_log (actor_id, action, entity_type, entity_id, detail, created_at)
            VALUES (:actor_id, 'revoke_certificate', 'certificate', :cert_id, CAST(:detail AS jsonb), :now)
        """),
        {
            "actor_id": admin_id,
            "cert_id": str(certificate_id),
            "detail": _json.dumps(
                {
                    "verification_id": cert_row.verification_id,
                    "reason": reason,
                    "note": note,
                    "xp_reversed": cert_row.xp_awarded,
                }
            ),
            "now": now,
        },
    )

    # 8. Notifications
    create_notification(
        db=db,
        user_id=cert_row.student_id,
        type="certificate_revoked",
        title="Certificate Revoked",
        body=f"Your certificate {cert_row.verification_id} for '{cert_row.project_title}' has been revoked: {reason}.",
        link=f"/student/certificates/{certificate_id}",
    )
    db.commit()

    return {
        "certificate_id": cert_row.id,
        "verification_id": cert_row.verification_id,
        "status": "revoked",
        "revoked_at": now.isoformat(),
        "revocation_reason": reason,
    }


def request_revocation(
    db: Session,
    certificate_id: uuid.UUID,
    user_id: uuid.UUID,
    reason: str,
    note: str = "",
) -> dict:
    """Company requests revocation -> Opens a flag; certificate unchanged (T-CRT-12, FR-CRT-4)."""
    cert_row = db.execute(
        text("""
            SELECT c.id, c.verification_id, c.status, p.company_id
            FROM certificates c
            JOIN applications a ON a.id = c.application_id
            JOIN projects p ON p.id = a.project_id
            WHERE c.id = :cert_id
        """),
        {"cert_id": certificate_id},
    ).fetchone()

    if not cert_row:
        raise CertificateError("Certificate not found", status_code=404)

    # Check caller is a member of the project's company (or admin)
    member = db.execute(
        text(
            "SELECT member_role FROM company_members WHERE company_id = :company_id AND user_id = :user_id"
        ),
        {"company_id": cert_row.company_id, "user_id": user_id},
    ).fetchone()

    admin_check = db.execute(
        text("SELECT role FROM users WHERE id = :user_id"),
        {"user_id": user_id},
    ).fetchone()

    if not member and (not admin_check or admin_check[0] != "admin"):
        raise CertificateError(
            "Only the issuing company or admin can request revocation", status_code=403
        )

    now = datetime.now(UTC)
    flag_id = uuid.uuid4()
    details_json = _json.dumps({"reporter_id": str(user_id), "reason": reason, "note": note})
    db.execute(
        text("""
            INSERT INTO flags (id, kind, status, entity_type, entity_id, details, created_at)
            VALUES (:id, 'manual', 'open', 'certificate', :entity_id, CAST(:details AS jsonb), :now)
        """),
        {
            "id": flag_id,
            "entity_id": certificate_id,
            "details": details_json,
            "now": now,
        },
    )
    db.commit()

    return {
        "flag_id": flag_id,
        "certificate_id": certificate_id,
        "status": "requested",
    }


def get_public_verification(
    db: Session,
    lookup_kind: str,
    lookup_value: str,
    client_ip: str | None = None,
) -> dict:
    """Read live record from v_public_verification (FR-CRT-3, NFR-1, T-CRT-06 to 10).

    Verified means live (AGENTS.md Rule 1).
    Logs lookup with hashed IP in verification_lookups table.
    Constant timing on unknown token / ID to prevent enumeration (T-CRT-08).
    """
    ip_hash = hashlib.sha256(client_ip.encode("utf-8")).hexdigest() if client_ip else None

    # Query view live
    if lookup_kind == "qr":
        row = db.execute(
            text("SELECT * FROM v_public_verification WHERE qr_token = :val"),
            {"val": lookup_value},
        ).fetchone()
    else:
        row = db.execute(
            text("SELECT * FROM v_public_verification WHERE verification_id = :val"),
            {"val": lookup_value},
        ).fetchone()

    if not row:
        # T-CRT-08: Unknown value - dummy compute for timing parity, log failed lookup
        hashlib.sha256(
            b"projectproof-timing-dummy-salt-" + lookup_value.encode("utf-8")
        ).hexdigest()
        time.sleep(0.005)  # 5ms jitter for database parity
        db.execute(
            text("""
                INSERT INTO verification_lookups (lookup_kind, found, ip_hash, created_at)
                VALUES (:kind, false, :ip_hash, now())
            """),
            {"kind": lookup_kind, "ip_hash": ip_hash},
        )
        db.commit()
        raise CertificateError("Verification record not found", status_code=404)

    # Found record: log successful lookup with certificate_id
    cert_id = db.execute(
        text("SELECT id FROM certificates WHERE verification_id = :v_id"),
        {"v_id": row.verification_id},
    ).scalar()

    db.execute(
        text("""
            INSERT INTO verification_lookups (certificate_id, lookup_kind, found, ip_hash, created_at)
            VALUES (:cert_id, :kind, true, :ip_hash, now())
        """),
        {"cert_id": cert_id, "kind": lookup_kind, "ip_hash": ip_hash},
    )
    db.commit()

    display_name = verification_display_name(row.full_name, row.show_full_name_on_verification)

    # T-CRT-09: No email, private feedback, rubric, AI output or internal IDs
    res = {
        "verification_id": row.verification_id,
        "status": row.status,
        "project": {
            "title": row.project_title,
            "difficulty": row.difficulty,
            "duration_days": row.duration_days,
        },
        "company": {
            "name": row.company_name,
            "approved": (row.company_status == "approved"),
        },
        "student": {
            "display_name": display_name,
        },
        "evaluation": {
            "summary": row.public_summary,
            "evaluated_at": row.evaluated_at.isoformat() if row.evaluated_at else None,
        },
        "skills": list(row.skills) if row.skills else [],
        "timeline": {
            "applied_at": row.applied_at.isoformat() if row.applied_at else None,
            "started_at": row.started_at.isoformat() if row.started_at else None,
            "completed_at": row.completed_at.isoformat() if row.completed_at else None,
        },
        "checked_at": datetime.now(UTC).isoformat(),
        "disclaimer": "This is a ProjectProof verification record. It is not formal employment experience.",
    }

    # T-CRT-07: Public page after revocation shows Revoked immediately; category only
    if row.status == "revoked":
        res["revoked_at"] = row.revoked_at.isoformat() if row.revoked_at else None
        res["revocation_reason"] = row.revocation_reason

    return res


def generate_certificate_pdf(
    db: Session,
    certificate_id: uuid.UUID,
    requesting_user_id: uuid.UUID,
    requesting_role: str,
) -> tuple[bytes, str]:
    """Generate certificate PDF with all required contents (FR-CRT-2, T-CRT-16).

    Contains: name, project, company, duration, skills, ID, QR code, disclaimer.
    Returns: (pdf_bytes, filename)
    """
    row = db.execute(
        text("""
            SELECT c.id, c.verification_id, c.qr_token, c.status, c.issued_at,
                   a.student_id,
                   p.company_id, p.title as project_title, p.duration_days, p.difficulty,
                   co.name as company_name,
                   sp.full_name as student_name
            FROM certificates c
            JOIN applications a ON a.id = c.application_id
            JOIN projects p ON p.id = a.project_id
            JOIN companies co ON co.id = p.company_id
            JOIN student_profiles sp ON sp.user_id = a.student_id
            WHERE c.id = :cert_id
        """),
        {"cert_id": certificate_id},
    ).fetchone()

    if not row:
        raise CertificateError("Certificate not found", status_code=404)

    # Authorization: student (owner), company (issuer), admin
    if requesting_role not in ("admin", "student", "company"):
        raise CertificateError("Not authorized to download this certificate", status_code=404)
    if requesting_role == "student" and row.student_id != requesting_user_id:
        raise CertificateError("Not authorized to download this certificate", status_code=404)
    elif requesting_role == "company":
        membership = db.execute(
            text(
                "SELECT member_role FROM company_members WHERE company_id = :cid AND user_id = :uid"
            ),
            {"cid": row.company_id, "uid": requesting_user_id},
        ).fetchone()
        if not membership:
            raise CertificateError(
                "Not authorized to download this certificate", status_code=404
            )

    # Fetch skills
    skills_rows = db.execute(
        text("""
            SELECT s.name FROM project_skills ps
            JOIN skills s ON s.id = ps.skill_id
            JOIN applications a ON a.project_id = ps.project_id
            JOIN certificates c ON c.application_id = a.id
            WHERE c.id = :cert_id
            ORDER BY s.name
        """),
        {"cert_id": certificate_id},
    ).fetchall()
    skill_names = [s[0] for s in skills_rows]
    skills_str = ", ".join(skill_names) if skill_names else "General Software Development"

    # Generate QR Code image
    verification_url = f"{settings.frontend_url}/verify/{row.qr_token}"
    qr = qrcode.QRCode(box_size=5, border=1)
    qr.add_data(verification_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_buf = io.BytesIO()
    qr_img.save(qr_buf, format="PNG")
    qr_buf.seek(0)

    # Draw PDF
    pdf_buf = io.BytesIO()
    width, height = landscape(letter)  # 792 x 612
    c = canvas.Canvas(pdf_buf, pagesize=landscape(letter))

    # Border & frame
    c.setStrokeColor(HexColor("#000000"))
    c.setLineWidth(2)
    c.rect(30, 30, width - 60, height - 60)
    c.setLineWidth(0.5)
    c.rect(36, 36, width - 72, height - 72)

    # Header
    c.setFont("Helvetica-Bold", 24)
    c.setFillColor(HexColor("#000000"))
    c.drawCentredString(width / 2, height - 90, "PROJECTPROOF AI")

    c.setFont("Helvetica", 11)
    c.setFillColor(HexColor("#666666"))
    c.drawCentredString(width / 2, height - 110, "LIVE VERIFIABLE PROJECT RECORD")

    c.setFont("Helvetica", 13)
    c.setFillColor(HexColor("#333333"))
    c.drawCentredString(width / 2, height - 150, "This is to certify that")

    # Student Name
    c.setFont("Helvetica-Bold", 22)
    c.setFillColor(HexColor("#000000"))
    c.drawCentredString(width / 2, height - 185, row.student_name)

    # Accomplishment
    c.setFont("Helvetica", 13)
    c.setFillColor(HexColor("#333333"))
    c.drawCentredString(width / 2, height - 225, "has successfully completed the project")

    # Project Title
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(HexColor("#000000"))
    c.drawCentredString(width / 2, height - 255, row.project_title)

    # Project metadata block
    c.setFont("Helvetica-Bold", 11)
    c.drawString(60, height - 320, "Company:")
    c.setFont("Helvetica", 11)
    c.drawString(130, height - 320, row.company_name)

    c.setFont("Helvetica-Bold", 11)
    c.drawString(60, height - 345, "Duration:")
    c.setFont("Helvetica", 11)
    c.drawString(130, height - 345, f"{row.duration_days} days ({row.difficulty.capitalize()})")

    c.setFont("Helvetica-Bold", 11)
    c.drawString(60, height - 370, "Skills:")
    c.setFont("Helvetica", 11)
    c.drawString(130, height - 370, skills_str)

    c.setFont("Helvetica-Bold", 11)
    c.drawString(60, height - 405, "Verification ID:")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(160, height - 405, row.verification_id)

    # QR Code at bottom right
    c.drawImage(ImageReader(qr_buf), width - 180, height - 440, width=110, height=110)
    c.setFont("Helvetica", 8)
    c.setFillColor(HexColor("#666666"))
    c.drawCentredString(width - 125, height - 450, "Scan to verify live")

    # Mandatory Legal Disclaimer (AGENTS.md and PRD)
    c.setFont("Helvetica-Oblique", 9)
    c.setFillColor(HexColor("#444444"))
    disclaimer_text = (
        "This is a ProjectProof verification record. It is not formal employment experience."
    )
    c.drawCentredString(width / 2, 50, disclaimer_text)

    c.save()
    pdf_bytes = pdf_buf.getvalue()
    filename = f"ProjectProof-Certificate-{row.verification_id}.pdf"
    return pdf_bytes, filename


def verify_certificate_content_hash(db: Session, certificate_id: uuid.UUID) -> bool:
    """Recompute content hash from live database fields and verify against stored content_hash (T-CRT-17)."""
    row = db.execute(
        text("""
            SELECT c.content_hash, c.issued_at,
                   a.student_id, a.project_id, a.completed_at,
                   p.company_id,
                   e.overall_score
            FROM certificates c
            JOIN applications a ON a.id = c.application_id
            JOIN projects p ON p.id = a.project_id
            JOIN submissions su ON su.application_id = a.id
            JOIN evaluations e ON e.submission_id = su.id AND e.decision = 'approved'
            WHERE c.id = :cert_id
            ORDER BY su.version DESC
            LIMIT 1
        """),
        {"cert_id": certificate_id},
    ).fetchone()

    if not row:
        return False

    skills_rows = db.execute(
        text("""
            SELECT s.name FROM project_skills ps
            JOIN skills s ON s.id = ps.skill_id
            WHERE ps.project_id = :project_id
        """),
        {"project_id": row.project_id},
    ).fetchall()
    skill_names = [s[0] for s in skills_rows]

    computed = compute_certificate_hash(
        student_id=row.student_id,
        project_id=row.project_id,
        company_id=row.company_id,
        completed_at=row.completed_at,
        skills=skill_names,
        overall_score=row.overall_score,
    )
    if computed == row.content_hash:
        return True

    # Backwards-compatible check for legacy isoformat() representation
    if isinstance(row.completed_at, datetime):
        legacy_completed_str = row.completed_at.isoformat()
    else:
        legacy_completed_str = str(row.completed_at)
    canonical_legacy = {
        "student_id": str(row.student_id),
        "project_id": str(row.project_id),
        "company_id": str(row.company_id),
        "completed_at": legacy_completed_str,
        "skills": sorted(skill_names),
        "overall_score": row.overall_score,
    }
    raw_legacy = _json.dumps(canonical_legacy, sort_keys=True, separators=(",", ":"))
    legacy_hash = hashlib.sha256(raw_legacy.encode("utf-8")).hexdigest()
    return legacy_hash == row.content_hash
