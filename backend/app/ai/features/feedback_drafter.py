"""Evaluation Feedback Drafter — FR-EVL-5 (docs/06-ai-modules-specification.md Section 6.5).

Turns reviewer rough notes and rubric scores into structured feedback (strengths,
improvements, next steps, public summary).
Enforces grounding: no claims absent from the notes.
Reviewer edits and accepts before sending.
"""

import json
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.ai import client as ai_client
from app.ai.schemas import FeedbackDraftOutput
from app.core.errors import ForbiddenError, NotFoundError


def draft(
    db: Session,
    user_id: uuid.UUID,
    submission_id: uuid.UUID,
    rough_notes: str,
    rubric_scores: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate structured feedback draft from reviewer notes."""
    # 1. Verify reviewer belongs to company owning the project
    sub_row = db.execute(
        text("""
            SELECT s.id, p.id as project_id, p.title, p.category, p.difficulty, p.company_id
              FROM submissions s
              JOIN applications a ON a.id = s.application_id
              JOIN projects p ON p.id = a.project_id
             WHERE s.id = :sid
        """),
        {"sid": submission_id},
    ).fetchone()

    if not sub_row:
        raise NotFoundError("Submission not found.")

    company_id = sub_row[5]
    member_row = db.execute(
        text("""
            SELECT member_role FROM company_members
             WHERE company_id = :cid AND user_id = :uid
        """),
        {"cid": company_id, "uid": user_id},
    ).fetchone()

    if not member_row:
        # Also allow platform admin
        admin_row = db.execute(
            text("SELECT role FROM users WHERE id = :uid AND role = 'admin'"),
            {"uid": user_id},
        ).fetchone()
        if not admin_row:
            raise ForbiddenError(
                "You must belong to the project's company to draft evaluation feedback."
            )

    # 2. Build prompt variables
    scores_str = json.dumps(rubric_scores or {})
    variables = {
        "project_title": sub_row[2],
        "project_category": sub_row[3] or "Software Engineering",
        "project_difficulty": sub_row[4],
        "rough_notes": rough_notes[:3000],
        "rubric_scores": scores_str,
    }

    # 3. Call LLM
    ai_envelope = ai_client.run(
        db=db,
        user_id=user_id,
        feature="feedback_drafter",
        prompt_version="v1",
        variables=variables,
        output_model=FeedbackDraftOutput,
        input_text=rough_notes[:1000],
    )

    output: FeedbackDraftOutput = ai_envelope["result"]
    return {
        "ai": ai_envelope["ai"],
        "result": output.model_dump(),
    }
