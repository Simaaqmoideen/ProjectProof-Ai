"""GitHub repo analysis AI feature — FR-STU-11.

Deterministic data from GitHub API + LLM proposes skills and a summary.
See docs/06-ai-modules-specification.md section 6.9.
AGENTS.md rule 12: GitHub data is never proof; saved skills get source='self'.
"""

from __future__ import annotations

import re
import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.ai import client as ai_client
from app.ai.schemas import GitHubAnalysisOutput

_FEATURE = "github_analysis"
_PROMPT_VERSION = "v1"


def analyse(
    *,
    db: Session,
    user_id: uuid.UUID,
    github_data: dict,
) -> dict:
    """Analyse pre-fetched public GitHub data and propose skills + summary.

    github_data must contain: repos (list of name/description/language/topics/stars/forks/last_push).
    No source code is sent to the model.
    Prompt injection note: repo descriptions are untrusted text, passed as data only.

    Checks (sec 6.9):
    - each skill must exist in skills table
    - each skill's evidence must be a repo name or language from the input
    - items without valid evidence are dropped
    """
    import json

    # Strip any personal data before sending to model
    repos_safe = []
    repo_names: set[str] = set()
    repo_languages: set[str] = set()
    for repo in github_data.get("repos", [])[:30]:  # limit to 30 repos
        name = str(repo.get("name", ""))
        lang = str(repo.get("language", "") or "")
        repos_safe.append(
            {
                "name": name,
                "description": str(repo.get("description", "") or "")[:200],  # truncate untrusted
                "language": lang,
                "topics": [str(t) for t in (repo.get("topics") or [])[:5]],
                "stars": int(repo.get("stars", 0)),
                "forks": int(repo.get("forks", 0)),
            }
        )
        if name.strip():
            repo_names.add(name.strip().lower())
        if lang.strip():
            repo_languages.add(lang.strip().lower())

    input_json = json.dumps(repos_safe)
    variables = {"GITHUB_DATA": input_json}

    raw_result = ai_client.run(
        db=db,
        user_id=user_id,
        feature=_FEATURE,
        prompt_version=_PROMPT_VERSION,
        variables=variables,
        output_model=GitHubAnalysisOutput,
        input_text=input_json,
    )

    output: GitHubAnalysisOutput = raw_result["result"]

    # Validate skills against skills table
    known_skills = {
        row[0].lower(): row[0] for row in db.execute(text("SELECT name FROM skills")).fetchall()
    }

    valid_skills = []
    for sg in output.skills:
        if sg.skill.lower() not in known_skills:
            continue  # not in skills table
        evidence_lower = sg.evidence.lower()
        # Match complete repo names and languages, including punctuation and spaces.
        if any(
            re.search(rf"(?<!\w){re.escape(term)}(?!\w)", evidence_lower)
            for term in repo_names | repo_languages
        ):
            valid_skills.append(
                {
                    "skill": known_skills[sg.skill.lower()],
                    "evidence": sg.evidence,
                }
            )

    check_pass_rate = len(valid_skills) / max(len(output.skills), 1) if output.skills else 1.0

    ai_client.recompute_confidence(
        raw_result["ai"],
        input_text=input_json,
        check_pass_rate=check_pass_rate,
    )

    return {
        "ai": raw_result["ai"],
        "result": {
            "summary": output.summary,
            "skills": valid_skills,
            "label": "self-linked, not verified",
        },
    }


def accept_skills(
    *,
    db: Session,
    user_id: uuid.UUID,
    log_id: str,
    accepted_skills: list[dict],
) -> dict:
    """Save accepted GitHub skills with source='self' (AGENTS.md rule 12).

    This is the only place github_analysis skills reach business tables.
    """
    row = db.execute(
        text("""
            SELECT id FROM ai_logs
             WHERE id = CAST(:lid AS bigint) AND user_id = :uid AND feature = 'github_analysis'
        """),
        {"lid": log_id, "uid": user_id},
    ).fetchone()
    if not row:
        return {"saved": 0, "message": "Log not found."}

    saved = 0
    for item in accepted_skills:
        skill_name = item.get("skill", "")
        skill_row = db.execute(
            text("SELECT id FROM skills WHERE lower(name) = lower(:name)"),
            {"name": skill_name},
        ).fetchone()
        if not skill_row:
            continue
        # source='self' — GitHub data is never proof (rule 12)
        db.execute(
            text("""
                INSERT INTO student_skills (student_id, skill_id, proficiency, source)
                VALUES (:uid, :sid, 2, 'self'::skill_source)
                ON CONFLICT (student_id, skill_id) DO NOTHING
            """),
            {"uid": user_id, "sid": skill_row[0]},
        )
        saved += 1

    db.execute(
        text("UPDATE ai_logs SET accepted = TRUE WHERE id = CAST(:lid AS bigint)"),
        {"lid": log_id},
    )
    db.commit()
    return {"saved": saved, "message": f"Saved {saved} skill(s) from GitHub analysis."}
