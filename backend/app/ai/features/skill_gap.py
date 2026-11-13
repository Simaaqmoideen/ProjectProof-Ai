"""Skill gap AI feature — FR-APP-9.

Deterministic gap identification (code) + LLM for suggested learning order.
See docs/06-ai-modules-specification.md section 6.8.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.ai import client as ai_client
from app.ai.schemas import SkillGapOutput

_FEATURE = "skill_gap"
_PROMPT_VERSION = "v1"


def suggest(
    *,
    db: Session,
    user_id: uuid.UUID,
    missing_skills: list[str],
    current_skills: list[str],
    project_difficulty: str,
) -> dict:
    """Suggest a learning order for missing skills with one resource each.

    The code supplies the missing skills; the model cannot add any.
    Checks: every returned skill must be in the supplied missing_skills list.
    Labelled 'AI draft'; never changes the match score.
    """
    import json

    if not missing_skills:
        return {
            "ai": {"label": "AI draft", "confidence": "high", "log_id": None},
            "result": {"order_reason": "No missing skills.", "items": []},
        }

    variables = {
        "MISSING_SKILLS": json.dumps(missing_skills),
        "CURRENT_SKILLS": json.dumps(current_skills),
        "PROJECT_DIFFICULTY": project_difficulty,
    }

    raw_result = ai_client.run(
        db=db,
        user_id=user_id,
        feature=_FEATURE,
        prompt_version=_PROMPT_VERSION,
        variables=variables,
        output_model=SkillGapOutput,
        input_text=json.dumps(missing_skills),
    )

    output: SkillGapOutput = raw_result["result"]

    # Check: every returned skill must be in the supplied missing_skills list
    missing_lower = {s.lower() for s in missing_skills}
    valid_items = [
        item.model_dump() for item in output.items if item.skill.lower() in missing_lower
    ]

    check_pass_rate = len(valid_items) / max(len(output.items), 1) if output.items else 1.0

    ai_client.recompute_confidence(
        raw_result["ai"],
        input_text=json.dumps(missing_skills),
        check_pass_rate=check_pass_rate,
    )

    return {
        "ai": raw_result["ai"],
        "result": {
            "order_reason": output.order_reason,
            "items": valid_items,
        },
    }
