"""Business rule BR-5: Badge evaluation and recalculation.

Only certificates with status 'issued' count toward badges.
See docs/01-product-requirements.md BR-5 and schema.sql badges seed.
"""

import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session


def recalculate_student_badges(db: Session, student_id: uuid.UUID) -> list[str]:
    """Recalculate and synchronize badges for a student based on issued certificates.

    Returns list of newly awarded badge codes.
    """
    # 1. Total verified completions
    total_completions = (
        db.execute(
            text("""
            SELECT count(c.id)
            FROM certificates c
            JOIN applications a ON a.id = c.application_id
            WHERE a.student_id = :student_id AND c.status = 'issued'
        """),
            {"student_id": student_id},
        ).scalar()
        or 0
    )

    # 2. Total development category completions
    dev_completions = (
        db.execute(
            text("""
            SELECT count(c.id)
            FROM certificates c
            JOIN applications a ON a.id = c.application_id
            JOIN projects p ON p.id = a.project_id
            WHERE a.student_id = :student_id AND c.status = 'issued' AND p.category = 'development'
        """),
            {"student_id": student_id},
        ).scalar()
        or 0
    )

    # 3. Distinct companies
    distinct_companies = (
        db.execute(
            text("""
            SELECT count(DISTINCT p.company_id)
            FROM certificates c
            JOIN applications a ON a.id = c.application_id
            JOIN projects p ON p.id = a.project_id
            WHERE a.student_id = :student_id AND c.status = 'issued'
        """),
            {"student_id": student_id},
        ).scalar()
        or 0
    )

    # Read all badges from DB
    badges = db.execute(text("SELECT id, code, rule FROM badges")).fetchall()

    qualifying_badge_ids = set()
    for b_id, b_code, b_rule in badges:
        rule_type = b_rule.get("type")
        min_val = b_rule.get("min", 1)
        category = b_rule.get("category")

        if rule_type == "verified_completions":
            if category == "development":
                if dev_completions >= min_val:
                    qualifying_badge_ids.add(b_id)
            else:
                if total_completions >= min_val:
                    qualifying_badge_ids.add(b_id)
        elif rule_type == "distinct_companies" and distinct_companies >= min_val:
            qualifying_badge_ids.add(b_id)

    # Current badges
    current_badge_ids = set(
        db.execute(
            text("SELECT badge_id FROM student_badges WHERE student_id = :student_id"),
            {"student_id": student_id},
        )
        .scalars()
        .all()
    )

    # Badges to remove (e.g. on revocation)
    to_remove = current_badge_ids - qualifying_badge_ids
    if to_remove:
        db.execute(
            text(
                "DELETE FROM student_badges WHERE student_id = :student_id AND badge_id = ANY(:ids)"
            ),
            {"student_id": student_id, "ids": list(to_remove)},
        )

    # Badges to add
    new_badge_ids = qualifying_badge_ids - current_badge_ids
    newly_awarded_codes = []
    for b_id, b_code, _ in badges:
        if b_id in new_badge_ids:
            db.execute(
                text(
                    "INSERT INTO student_badges (student_id, badge_id) VALUES (:student_id, :badge_id)"
                ),
                {"student_id": student_id, "badge_id": b_id},
            )
            newly_awarded_codes.append(b_code)

    return newly_awarded_codes
