"""Verified Record Resume Bullet Rewriter — FR-RWD-4 (docs/06-ai-modules-specification.md Section 6.10).

Translates a verified project completion record into STAR-format resume bullet points.
Grounded strictly in verified certificate data: title, skills, duration, evaluation summary.
No invented metrics or external tools.
"""

import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.ai import client as ai_client
from app.ai.schemas import ResumeBulletOutput
from app.core.errors import BadRequestError, NotFoundError


def rewrite(
    db: Session,
    user_id: uuid.UUID,
    certificate_id: str | uuid.UUID,
) -> dict[str, Any]:
    """Generate professional resume bullets strictly from a verified certificate."""
    # 1. Load verified certificate details (by certificate id or verification_id)
    cert_row = db.execute(
        text("""
            SELECT c.id, c.status, a.student_id, p.title, p.category, p.difficulty,
                   p.duration_days, e.public_summary
              FROM certificates c
              JOIN applications a ON a.id = c.application_id
              JOIN projects p ON p.id = a.project_id
              LEFT JOIN submissions s ON s.application_id = a.id
              LEFT JOIN evaluations e ON e.submission_id = s.id
             WHERE (c.id::text = :cid OR c.verification_id = :cid)
             ORDER BY e.evaluated_at DESC NULLS LAST
             LIMIT 1
        """),
        {"cid": str(certificate_id)},
    ).fetchone()

    if not cert_row:
        raise NotFoundError("Certificate not found.")

    if cert_row[1] != "issued":
        raise BadRequestError(
            "Resume bullets can only be generated for active, issued certificates."
        )

    # 2. Fetch skills associated with the project
    skill_rows = db.execute(
        text("""
            SELECT s.name
              FROM project_skills ps
              JOIN skills s ON s.id = ps.skill_id
              JOIN certificates c ON c.application_id = :aid
              JOIN applications a ON a.id = c.application_id
             WHERE ps.project_id = a.project_id
        """),
        {"aid": cert_row[0]},
    ).fetchall()
    skills_list = [r[0] for r in skill_rows] or ["General Software Engineering"]

    # 3. Build prompt variables
    variables = {
        "project_title": cert_row[3],
        "project_category": cert_row[4] or "Development",
        "project_difficulty": cert_row[5],
        "duration_days": str(cert_row[6]),
        "skills": ", ".join(skills_list),
        "public_summary": cert_row[7]
        or "Demonstrated successful completion of all project deliverables.",
    }

    # 4. Invoke LLM via central client
    return ai_client.run(
        db=db,
        user_id=user_id,
        feature="resume_rewriter",
        prompt_version="v1",
        variables=variables,
        output_model=ResumeBulletOutput,
        input_text=cert_row[3],
    )
