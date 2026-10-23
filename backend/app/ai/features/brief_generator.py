"""Project brief generator AI feature — FR-PRJ-5.

Drafts a structured project brief from a rough company idea.
All checks enforce docs/06-ai-modules-specification.md section 6.2.
"""

from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.ai import client as ai_client
from app.ai.schemas import BriefOutput

_MAX_IDEA_CHARS = 1_000
_FEATURE = "brief_generator"
_PROMPT_VERSION = "v1"


def generate(
    *,
    db: Session,
    user_id: uuid.UUID,
    rough_idea: str,
    target_difficulty: str | None = None,
    duration_days: int | None = None,
) -> dict:
    """Generate a project brief draft and return it labelled as 'AI draft'.

    Checks (sec 6.2):
    - milestone due_day_offsets are increasing and last <= duration_days
    - required_skills exist in the skills table
    - no XP value accepted (server computes XP)
    """
    rough_idea = rough_idea[:_MAX_IDEA_CHARS]
    variables = {
        "ROUGH_IDEA": rough_idea,
        "DIFFICULTY": target_difficulty or "intermediate",
        "DURATION_DAYS": str(duration_days or 30),
    }

    raw_result = ai_client.run(
        db=db,
        user_id=user_id,
        feature=_FEATURE,
        prompt_version=_PROMPT_VERSION,
        variables=variables,
        output_model=BriefOutput,
        input_text=rough_idea,
    )

    output: BriefOutput = raw_result["result"]

    # --- Check 1: Honor duration_days, sort milestones, and clamp every offset 1..duration_days
    if duration_days:
        output.duration_days = duration_days
    output.milestones.sort(key=lambda m: m.due_day_offset)
    for m in output.milestones:
        m.due_day_offset = max(1, min(m.due_day_offset, output.duration_days))

    # --- Check 2: required_skills must be in skills table (single query)
    skill_rows = db.execute(text("SELECT name FROM skills")).fetchall()
    name_map = {row[0].lower(): row[0] for row in skill_rows}
    valid_skills = [name_map[s.lower()] for s in output.required_skills if s.lower() in name_map]
    check_pass_rate = len(valid_skills) / max(len(output.required_skills), 1)

    ai_client.recompute_confidence(
        raw_result["ai"],
        input_text=rough_idea,
        check_pass_rate=check_pass_rate,
    )

    return {
        "ai": raw_result["ai"],
        "result": {
            "title": output.title,
            "description": output.description,
            "category": output.category,
            "difficulty": output.difficulty,
            "duration_days": output.duration_days,
            "required_skills": valid_skills,
            "milestones": [m.model_dump() for m in output.milestones],
            "deliverables_checklist": output.deliverables_checklist,
            "ai_generated": True,
        },
    }
