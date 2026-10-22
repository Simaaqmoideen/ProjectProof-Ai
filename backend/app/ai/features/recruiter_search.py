"""Recruiter plain-text search — FR-REC-3.

LLM converts free-text query to a structured filter object.
Server validates and executes parameterised queries — model never writes SQL.
See docs/06-ai-modules-specification.md section 6.7.
"""

from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.ai import client as ai_client
from app.ai.schemas import RecruiterSearchFilter

_FEATURE = "recruiter_search"
_PROMPT_VERSION = "v1"
_MAX_QUERY_CHARS = 500


def interpret_query(
    *,
    db: Session,
    user_id: uuid.UUID,
    query_text: str,
) -> dict:
    """Convert a natural-language recruiter query into a validated filter object.

    The returned filter is shown to the recruiter as chips (editable before running).
    No query is executed here; the router executes parameterised SQL against the filter.
    """
    query_text = query_text[:_MAX_QUERY_CHARS]
    variables = {"QUERY": query_text}

    raw_result = ai_client.run(
        db=db,
        user_id=user_id,
        feature=_FEATURE,
        prompt_version=_PROMPT_VERSION,
        variables=variables,
        output_model=RecruiterSearchFilter,
        input_text=query_text,
    )

    output: RecruiterSearchFilter = raw_result["result"]

    # Validate skills against skills table (allow-list)
    known_skills = {
        row[0].lower(): row[0] for row in db.execute(text("SELECT name FROM skills")).fetchall()
    }
    valid_skills = [known_skills[s.lower()] for s in output.skills if s.lower() in known_skills]

    # Validate category against known categories
    known_categories = {
        row[0]
        for row in db.execute(
            text("SELECT DISTINCT category FROM projects WHERE category IS NOT NULL")
        ).fetchall()
    }
    valid_category = output.category if output.category in known_categories else None

    validated_filter = {
        "skills": valid_skills,
        "min_xp": max(0, output.min_xp) if output.min_xp is not None else None,
        "min_verified_projects": max(0, output.min_verified_projects)
        if output.min_verified_projects is not None
        else None,
        "category": valid_category,
        "verified_only": output.verified_only,
    }

    return {
        "ai": raw_result["ai"],
        "result": validated_filter,
        "query": query_text,
    }
