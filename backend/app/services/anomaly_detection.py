"""Anomaly Detection Service — FR-ADM-7 (docs/06-ai-modules-specification.md Section 5.3).

Deterministic anomaly detection rules that flag potential integrity issues for human admin review.
Rules:
- A1: One company issues 3 or more certificates to the same student within 14 days
- A2: Completion in under 25% of the project duration with an overall score of 90 or more
- A3: A company with at least 5 evaluations and an average score of 95 or more
- A4: Student and company share the same non-public email domain
- A5: One hashed IP makes more than 50 failed verification lookups in an hour

Flags are prompts for a human admin to review, not automatic accusations.
"""

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

PUBLIC_EMAIL_DOMAINS = {
    "gmail.com",
    "yahoo.com",
    "hotmail.com",
    "outlook.com",
    "icloud.com",
    "proton.me",
    "protonmail.com",
    "mail.com",
    "aol.com",
    "zoho.com",
}


def scan_anomalies(db: Session) -> dict[str, Any]:
    """Run all 5 anomaly detection rules and insert open flags.

    Deduplicates against already open flags for the same rule and entity.
    """
    now = datetime.now(UTC)
    new_flags: list[dict[str, Any]] = []

    # ── Rule A1: 3+ certificates from same company to same student within 14 days ──
    rows_a1 = db.execute(
        text("""
            SELECT p.company_id, a.student_id, COUNT(cert.id) as cert_count
              FROM certificates cert
              JOIN applications a ON a.id = cert.application_id
              JOIN projects p ON p.id = a.project_id
             WHERE cert.status = 'issued'
               AND cert.issued_at >= :since
             GROUP BY p.company_id, a.student_id
            HAVING COUNT(cert.id) >= 3
        """),
        {"since": now - timedelta(days=14)},
    ).fetchall()

    for comp_id, student_id, count in rows_a1:
        if not _open_flag_exists(db, rule_id="A1", entity_id=comp_id):
            flag = _create_flag(
                db=db,
                kind="anomaly",
                entity_type="company",
                entity_id=comp_id,
                details={
                    "rule": "A1",
                    "student_id": str(student_id),
                    "cert_count": int(count),
                    "summary": f"Company issued {count} certificates to student {student_id} within 14 days.",
                },
            )
            new_flags.append(flag)

    # ── Rule A2: Completion in < 25% duration with score >= 90 ──────────────────
    rows_a2 = db.execute(
        text("""
            SELECT a.id, a.student_id, p.id, p.duration_days, e.overall_score,
                   EXTRACT(EPOCH FROM (e.evaluated_at - a.started_at)) / 86400.0 as days_taken
              FROM evaluations e
              JOIN submissions s ON s.id = e.submission_id
              JOIN applications a ON a.id = s.application_id
              JOIN projects p ON p.id = a.project_id
             WHERE e.overall_score >= 90
               AND a.started_at IS NOT NULL
               AND EXTRACT(EPOCH FROM (e.evaluated_at - a.started_at)) / 86400.0 < (p.duration_days * 0.25)
        """)
    ).fetchall()

    for app_id, student_id, proj_id, dur_days, score, days_taken in rows_a2:
        if not _open_flag_exists(db, rule_id="A2", entity_id=app_id):
            flag = _create_flag(
                db=db,
                kind="anomaly",
                entity_type="application",
                entity_id=app_id,
                score=float(score),
                details={
                    "rule": "A2",
                    "student_id": str(student_id),
                    "project_id": str(proj_id),
                    "duration_days": dur_days,
                    "score": float(score),
                    "days_taken": round(float(days_taken), 2),
                    "summary": f"Application completed in {round(float(days_taken), 1)} days (< 25% of {dur_days}d) with high score ({score}).",
                },
            )
            new_flags.append(flag)

    # ── Rule A3: Company with >= 5 evaluations and average score >= 95 ──────────
    rows_a3 = db.execute(
        text("""
            SELECT p.company_id, COUNT(e.id) as eval_count, AVG(e.overall_score) as avg_score
              FROM evaluations e
              JOIN submissions s ON s.id = e.submission_id
              JOIN applications a ON a.id = s.application_id
              JOIN projects p ON p.id = a.project_id
             GROUP BY p.company_id
            HAVING COUNT(e.id) >= 5 AND AVG(e.overall_score) >= 95.0
        """)
    ).fetchall()

    for comp_id, eval_count, avg_score in rows_a3:
        if not _open_flag_exists(db, rule_id="A3", entity_id=comp_id):
            flag = _create_flag(
                db=db,
                kind="anomaly",
                entity_type="company",
                entity_id=comp_id,
                score=float(avg_score),
                details={
                    "rule": "A3",
                    "eval_count": int(eval_count),
                    "avg_score": round(float(avg_score), 2),
                    "summary": f"Company has {eval_count} evaluations with an unusually high average score of {round(float(avg_score), 1)}/100.",
                },
            )
            new_flags.append(flag)

    # ── Rule A4: Student and company share the same non-public email domain ─────
    rows_a4 = db.execute(
        text("""
            SELECT a.id, a.student_id, p.company_id, u.email as student_email, c.email_domain
              FROM applications a
              JOIN users u ON u.id = a.student_id
              JOIN projects p ON p.id = a.project_id
              JOIN companies c ON c.id = p.company_id
             WHERE c.email_domain IS NOT NULL
               AND LOWER(SPLIT_PART(u.email, '@', 2)) = LOWER(c.email_domain)
        """)
    ).fetchall()

    for app_id, student_id, comp_id, student_email, company_domain in rows_a4:
        if company_domain.lower() not in PUBLIC_EMAIL_DOMAINS and not _open_flag_exists(
            db, rule_id="A4", entity_id=app_id
        ):
            flag = _create_flag(
                db=db,
                kind="anomaly",
                entity_type="application",
                entity_id=app_id,
                details={
                    "rule": "A4",
                    "student_id": str(student_id),
                    "company_id": str(comp_id),
                    "student_email": student_email,
                    "company_domain": company_domain,
                    "summary": f"Student email '{student_email}' shares private domain '{company_domain}' with the company.",
                },
            )
            new_flags.append(flag)

    # ── Rule A5: IP with > 50 failed verification lookups in an hour ───────────
    rows_a5 = db.execute(
        text("""
            SELECT ip_hash, COUNT(*) as failed_count
              FROM verification_lookups
             WHERE found = false
               AND created_at >= NOW() - INTERVAL '1 hour'
             GROUP BY ip_hash
            HAVING COUNT(*) > 50
        """)
    ).fetchall()

    for ip_hash, failed_count in rows_a5:
        # Check if recent open flag exists for this ip_hash
        existing = db.execute(
            text("""
                SELECT id FROM flags
                 WHERE kind = 'anomaly'
                   AND status = 'open'
                   AND details->>'rule' = 'A5'
                   AND details->>'ip_hash' = :iph
            """),
            {"iph": ip_hash},
        ).fetchone()
        if not existing:
            flag_id = uuid.uuid4()
            details = {
                "rule": "A5",
                "ip_hash": ip_hash,
                "failed_lookups": int(failed_count),
                "summary": f"IP hash {ip_hash[:8]}... made {failed_count} failed verification lookups in 1 hour.",
            }
            db.execute(
                text("""
                    INSERT INTO flags (id, kind, entity_type, entity_id, details, status, created_at)
                    VALUES (:id, 'anomaly', 'ip', NULL, CAST(:details AS jsonb), 'open', NOW())
                """),
                {"id": flag_id, "details": json.dumps(details)},
            )
            new_flags.append(
                {"id": str(flag_id), "rule": "A5", "entity_type": "ip", "details": details}
            )

    db.commit()
    return {
        "scanned_at": now.isoformat(),
        "rules_executed": ["A1", "A2", "A3", "A4", "A5"],
        "new_flags_opened": len(new_flags),
        "flags": new_flags,
    }


def _open_flag_exists(db: Session, rule_id: str, entity_id: uuid.UUID) -> bool:
    """Check if an open flag for this rule and entity already exists."""
    row = db.execute(
        text("""
            SELECT id FROM flags
             WHERE kind = 'anomaly'
               AND status = 'open'
               AND entity_id = :eid
               AND details->>'rule' = :rule
        """),
        {"eid": entity_id, "rule": rule_id},
    ).fetchone()
    return row is not None


def _create_flag(
    db: Session,
    kind: str,
    entity_type: str,
    entity_id: uuid.UUID,
    details: dict[str, Any],
    score: float | None = None,
) -> dict[str, Any]:
    """Insert a new flag row."""
    flag_id = uuid.uuid4()
    db.execute(
        text("""
            INSERT INTO flags (id, kind, entity_type, entity_id, score, details, status, created_at)
            VALUES (:id, CAST(:kind AS flag_kind), :entity_type, :entity_id, :score, CAST(:details AS jsonb), 'open', NOW())
        """),
        {
            "id": flag_id,
            "kind": kind,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "score": score,
            "details": json.dumps(details),
        },
    )
    return {
        "id": str(flag_id),
        "rule": details.get("rule"),
        "entity_type": entity_type,
        "entity_id": str(entity_id),
        "score": score,
        "details": details,
    }
