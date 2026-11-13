"""Resume analysis AI feature — FR-STU-4.

Extracts structured data from resume text.
All checks enforce docs/06-ai-modules-specification.md section 6.1.
"""

from __future__ import annotations

import re
import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.ai import client as ai_client
from app.ai.schemas import ResumeAnalysisOutput

_MAX_RESUME_CHARS = 15_000
_FEATURE = "resume_analysis"
_PROMPT_VERSION = "v1"


def analyse(
    *,
    db: Session,
    user_id: uuid.UUID,
    resume_text: str,
) -> dict:
    """Run LLM resume analysis and return structured draft + AI meta.

    Checks (sec 6.1):
    - Each skill must exist in the skills table (case-insensitive).
    - Each evidence string must appear approximately in the resume text.
    - Unknown skills are flagged for admin review, not silently kept.
    """
    # Truncate + log if needed
    truncated = False
    if len(resume_text) > _MAX_RESUME_CHARS:
        resume_text = resume_text[:_MAX_RESUME_CHARS]
        truncated = True

    variables = {
        "RESUME_TEXT": resume_text,
        "MAX_CHARS": str(_MAX_RESUME_CHARS),
    }

    raw_result = ai_client.run(
        db=db,
        user_id=user_id,
        feature=_FEATURE,
        prompt_version=_PROMPT_VERSION,
        variables=variables,
        output_model=ResumeAnalysisOutput,
        input_text=resume_text,
    )

    output: ResumeAnalysisOutput = raw_result["result"]

    # --- Check 1: skills must exist in skills table OR be flagged for review
    known_skill_names = {
        row[0].lower() for row in db.execute(text("SELECT name FROM skills")).fetchall()
    }
    valid_skills = []
    unknown_skills = []
    resume_lower = resume_text.lower()

    for skill in output.skills:
        # Check evidence in resume text: require most meaningful tokens (>3 chars) to appear
        evidence_words = [w for w in re.findall(r"\w+", skill.evidence.lower()) if len(w) > 3]
        if not evidence_words:
            evidence_found = skill.evidence.lower() in resume_lower if skill.evidence else False
        else:
            matches = sum(1 for w in evidence_words if w in resume_lower)
            evidence_found = matches >= max(1, int(len(evidence_words) * 0.5))

        if not evidence_found:
            continue  # drop: evidence does not sufficiently match resume text

        if skill.name.lower() in known_skill_names:
            valid_skills.append(skill)
        else:
            unknown_skills.append(skill.name)

    check_pass_rate = len(valid_skills) / max(len(output.skills), 1)

    ai_client.recompute_confidence(
        raw_result["ai"],
        input_text=resume_text,
        check_pass_rate=check_pass_rate,
    )

    return {
        "ai": raw_result["ai"],
        "result": {
            "skills": [s.model_dump() for s in valid_skills],
            "education": [e.model_dump() for e in output.education],
            "projects": [p.model_dump() for p in output.projects],
            "experience": [ex.model_dump() for ex in output.experience],
            "certifications": [c.model_dump() for c in output.certifications],
            "unknown_skills_for_review": unknown_skills,
        },
        "truncated": truncated,
    }


def accept_skills(
    *,
    db: Session,
    user_id: uuid.UUID,
    log_id: str,
    accepted_skills: list[dict],
) -> dict:
    """Save accepted skills from the review screen (FR-STU-4).

    Each accepted skill is saved with source='resume' at proficiency=2 by default.
    This is the ONLY place resume-analysis skills are written to business tables.
    """
    # Verify log_id belongs to this user and feature
    row = db.execute(
        text("""
            SELECT id FROM ai_logs
             WHERE id = CAST(:lid AS bigint) AND user_id = :uid AND feature = 'resume_analysis'
        """),
        {"lid": log_id, "uid": user_id},
    ).fetchone()
    if not row:
        return {"saved": 0, "message": "Log not found or already processed."}

    saved = 0
    for item in accepted_skills:
        skill_name = item.get("name", "")
        proficiency = int(item.get("proficiency", 2))
        skill_row = db.execute(
            text("SELECT id FROM skills WHERE lower(name) = lower(:name)"),
            {"name": skill_name},
        ).fetchone()
        if not skill_row:
            continue
        db.execute(
            text("""
                INSERT INTO student_skills (student_id, skill_id, proficiency, source)
                VALUES (:uid, :sid, :prof, 'resume'::skill_source)
                ON CONFLICT (student_id, skill_id)
                DO UPDATE SET
                    proficiency = EXCLUDED.proficiency,
                    source = CASE WHEN student_skills.source = 'verified_project'::skill_source THEN 'verified_project'::skill_source ELSE 'resume'::skill_source END
            """),
            {"uid": user_id, "sid": skill_row[0], "prof": proficiency},
        )
        saved += 1

    # Mark log as accepted
    db.execute(
        text("UPDATE ai_logs SET accepted = TRUE WHERE id = CAST(:lid AS bigint)"),
        {"lid": log_id},
    )
    db.commit()
    return {"saved": saved, "message": f"Saved {saved} skill(s) from resume analysis."}
