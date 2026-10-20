"""Certificates service: the ONLY place where certificates are created or revoked.

See AGENTS.md rule 3 and docs/03-tech-stack-and-architecture.md section 5.
"""
import uuid
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.ids import compute_certificate_hash, generate_qr_token, generate_verification_id
from app.services.badges import recalculate_student_badges
from app.services.notifications import create_notification
from app.services.trust_score import on_evaluation_completed
from app.services.xp import compute_xp


class CertificateError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


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
        text("SELECT id, verification_id, qr_token, status, xp_awarded FROM certificates WHERE application_id = :app_id"),
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
        raise CertificateError(f"Cannot approve application with status '{app_row.status}'", status_code=409)

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
    import json as _json
    db.execute(
        text("""
            INSERT INTO audit_log (actor_id, action, entity_type, entity_id, detail, created_at)
            VALUES (:actor_id, 'issue_certificate', 'certificate', :cert_id, CAST(:detail AS jsonb), :now)
        """),
        {
            "actor_id": reviewer_id,
            "cert_id": str(cert_id),
            "detail": _json.dumps({"verification_id": verification_id, "xp_awarded": xp_amount, "score": overall_score}),
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
        text("SELECT submitted_at FROM submissions WHERE application_id = :app_id ORDER BY version DESC LIMIT 1"),
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
