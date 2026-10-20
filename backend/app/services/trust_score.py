"""Business rule BR-6: Company trust score calculation and adjustment.

See docs/01-product-requirements.md BR-6.
"""
import uuid
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings


def adjust_company_trust_score(db: Session, company_id: uuid.UUID, delta: int) -> int:
    """Adjust trust score by delta, clamped between 0 and 100."""
    row = db.execute(
        text("SELECT trust_score FROM companies WHERE id = :company_id FOR UPDATE"),
        {"company_id": company_id},
    ).fetchone()
    if not row:
        return settings.trust_score_initial

    current = row[0]
    new_score = max(0, min(100, current + delta))
    db.execute(
        text("UPDATE companies SET trust_score = :score, updated_at = now() WHERE id = :company_id"),
        {"score": new_score, "company_id": company_id},
    )
    return new_score


def on_evaluation_completed(db: Session, company_id: uuid.UUID, submitted_at: datetime, evaluated_at: datetime | None = None) -> None:
    """Apply BR-6 fast evaluation bonus (+5 if within 5 days, capped at +30 total bonus)."""
    if evaluated_at is None:
        evaluated_at = datetime.now(UTC)
    
    # Days elapsed
    days = (evaluated_at - submitted_at).total_seconds() / 86400.0
    if days <= 5.0:
        adjust_company_trust_score(db, company_id, settings.trust_score_fast_eval)
