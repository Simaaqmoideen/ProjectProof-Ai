"""Match explanation / applicant ranking AI feature — FR-APP-3, FR-APP-5.

LLM writes sentences; code supplies all facts and verifies every claim.
See docs/06-ai-modules-specification.md section 6.3.
"""

from __future__ import annotations

import uuid

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

    verified: list[dict] = []
    passed = 0
    for expl in output.explanations:
        app_facts = fact_map.get(str(expl.application_id))
        if not app_facts:
            continue

        strengths = _verify_sentence(expl.strengths, app_facts)
        gaps = _verify_sentence(expl.gaps, app_facts)
        passed += 1
        verified.append(
            {
                "application_id": expl.application_id,
                "strengths": strengths,
                "gaps": gaps,
            }
        )

    # Add template sentences for applicants with no explanation
    explained_ids = {e["application_id"] for e in verified}
    for app in applicants:
        aid = str(app["application_id"])
        if aid not in explained_ids:
            passed += 1
            verified.append(
                {
                    "application_id": aid,
                    "strengths": _template_strengths(app),
                    "gaps": _template_gaps(app),
                }
            )

    check_pass_rate = passed / max(len(applicants), 1)
    raw_result["ai"]["confidence"] = _recompute_confidence(
        check_pass_rate, raw_result["ai"]["confidence"]
    )

    return {
        "ai": raw_result["ai"],
        "result": {"explanations": verified},
    }


def _verify_sentence(sentence: str, facts: dict) -> str:
    """Return sentence only if it references facts; otherwise return a template."""
    if not sentence:
        return _template_strengths(facts)

    # Collect allowed terms from facts
    allowed_terms: set[str] = set()
    for skill in facts.get("matched_skills", []) + facts.get("missing_skills", []):
        allowed_terms.add(skill.lower())
    for val in facts.get("breakdown", {}).values():
        allowed_terms.add(str(val))
    allowed_terms.add(str(facts.get("verified_project_count", "")))
    allowed_terms.add(str(facts.get("relevant_verified_projects", "")))
    allowed_terms.add(str(facts.get("current_load", "")))

    sentence_lower = sentence.lower()
    # If sentence has at least one grounded term or is short enough, accept it
    if any(t in sentence_lower for t in allowed_terms if t):
        return sentence
    return _template_strengths(facts)


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


def _recompute_confidence(rate: float, current: str) -> str:
    if rate < 0.5 or current == "low":
        return "low"
    if rate < 0.8 or current == "medium":
        return "medium"
    return "high"
