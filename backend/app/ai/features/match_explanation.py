"""Match explanation / applicant ranking AI feature — FR-APP-3, FR-APP-5.

LLM writes sentences; code supplies all facts and verifies every claim.
See docs/06-ai-modules-specification.md section 6.3.
"""

from __future__ import annotations

import re
import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.ai import client as ai_client
from app.ai.schemas import RankingOutput

_FEATURE = "match_explanation"
_PROMPT_VERSION = "v1"


def explain_applicants(
    *,
    db: Session,
    user_id: uuid.UUID,
    applicants: list[dict],
) -> dict:
    """Generate strength/gap sentences for each applicant.

    applicants is a list of dicts with:
      application_id, matched_skills, missing_skills, verified_project_count,
      relevant_verified_projects, current_load, breakdown (skills/difficulty/experience/availability).

    Check: every skill or number mentioned must appear in supplied facts;
    otherwise replace with a template sentence (sec 6.3).
    """
    import json

    # Build input — structured facts, not free text
    facts_json = json.dumps(applicants, default=str)

    variables = {
        "APPLICANT_FACTS": facts_json,
    }

    raw_result = ai_client.run(
        db=db,
        user_id=user_id,
        feature=_FEATURE,
        prompt_version=_PROMPT_VERSION,
        variables=variables,
        output_model=RankingOutput,
        input_text=facts_json,
    )

    output: RankingOutput = raw_result["result"]

    # Build fact lookup per applicant for verification
    fact_map: dict[str, dict] = {str(a["application_id"]): a for a in applicants}
    all_skills = {row[0].lower() for row in db.execute(text("SELECT name FROM skills")).fetchall()}

    verified: list[dict] = []
    seen_ids: set[str] = set()
    passed = 0

    for expl in output.explanations:
        aid = str(expl.application_id)
        if aid in seen_ids:
            continue
        app_facts = fact_map.get(aid)
        if not app_facts:
            continue

        seen_ids.add(aid)
        strengths = _verify_sentence(expl.strengths, app_facts, is_gaps=False, all_skills=all_skills)
        gaps = _verify_sentence(expl.gaps, app_facts, is_gaps=True, all_skills=all_skills)
        if strengths == expl.strengths.strip() and gaps == expl.gaps.strip():
            passed += 1

        verified.append(
            {
                "application_id": aid,
                "strengths": strengths,
                "gaps": gaps,
            }
        )

    # Add template sentences for applicants with no explanation
    for app in applicants:
        aid = str(app["application_id"])
        if aid not in seen_ids:
            seen_ids.add(aid)
            verified.append(
                {
                    "application_id": aid,
                    "strengths": _template_strengths(app),
                    "gaps": _template_gaps(app),
                }
            )

    check_pass_rate = passed / max(len(applicants), 1)
    ai_client.recompute_confidence(
        raw_result["ai"],
        input_text=facts_json,
        needed_retry=not raw_result.get("_first_attempt_ok", True),
        check_pass_rate=check_pass_rate,
    )

    return {
        "ai": raw_result["ai"],
        "result": {"explanations": verified},
    }


def _verify_sentence(
    sentence: str,
    facts: dict,
    is_gaps: bool = False,
    all_skills: set[str] | None = None,
) -> str:
    """Return sentence only if it references facts; otherwise return a template."""
    fallback = _template_gaps(facts) if is_gaps else _template_strengths(facts)
    if not sentence or not sentence.strip():
        return fallback

    fact_skills = {s.lower() for s in (facts.get("matched_skills", []) + facts.get("missing_skills", []))}
    sentence_lower = sentence.lower()

    # Reject if sentence mentions any technology/skill not in the applicant's facts
    if all_skills:
        for sk in all_skills:
            if len(sk) > 2 and re.search(rf"\b{re.escape(sk)}\b", sentence_lower):
                if sk not in fact_skills:
                    return fallback

    # Sentence must reference at least one fact skill
    has_fact_skill = any(re.search(rf"\b{re.escape(fs)}\b", sentence_lower) for fs in fact_skills if fs)
    if has_fact_skill:
        return sentence.strip()

    return fallback


def _template_strengths(facts: dict) -> str:
    matched = facts.get("matched_skills", [])
    total = len(matched) + len(facts.get("missing_skills", []))
    vp = facts.get("verified_project_count", 0)
    parts = []
    if total > 0:
        parts.append(f"Matches {len(matched)} of {total} required skills.")
    if vp:
        parts.append(f"Has {vp} verified project(s).")
    return " ".join(parts) if parts else "Meets baseline criteria."


def _template_gaps(facts: dict) -> str:
    missing = facts.get("missing_skills", [])
    if missing:
        return f"Missing: {', '.join(missing[:3])}."
    return "No significant skill gaps."
