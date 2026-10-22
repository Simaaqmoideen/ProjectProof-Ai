"""AI Mentor Chatbot feature — FR-WRK-5 (docs/06-ai-modules-specification.md Section 6.6).

Scoped exclusively to the student's active project workspace.
Provides hints, explains concepts/errors, points to documentation.
Never writes complete solutions.
Logged to ai_logs for auditability.
"""

import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.ai import client as ai_client
from app.ai.schemas import MentorChatOutput
from app.core.errors import BadRequestError, ForbiddenError, NotFoundError


def chat(
    db: Session,
    user_id: uuid.UUID,
    application_id: uuid.UUID,
    message: str,
    milestone_id: uuid.UUID | None = None,
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Provide AI mentor guidance for an active workspace."""
    # 1. Verify application ownership and active state
    app_row = db.execute(
        text("""
            SELECT a.id, a.student_id, a.status, p.id as project_id, p.title, p.description,
                   p.category, p.difficulty
              FROM applications a
              JOIN projects p ON p.id = a.project_id
             WHERE a.id = :aid
        """),
        {"aid": application_id},
    ).fetchone()

    if not app_row:
        raise NotFoundError("Application not found.")

    if app_row[1] != user_id:
        raise ForbiddenError("You can only chat with the mentor for your own application.")

    if app_row[2] not in ("in_progress", "submitted", "changes_requested"):
        raise BadRequestError(
            f"AI Mentor is only available for active projects (current status: {app_row[2]})."
        )

    # 2. Load milestone context if specified
    milestone_info = "Overall project guidance"
    if milestone_id:
        m_row = db.execute(
            text("""
                SELECT title, description, due_day_offset
                  FROM milestones
                 WHERE id = :mid AND project_id = :pid
            """),
            {"mid": milestone_id, "pid": app_row[3]},
        ).fetchone()
        if m_row:
            milestone_info = f"Milestone: {m_row[0]} — {m_row[1] or 'No description'}"

    # 3. Format history safely (last 6 turns max)
    history_str = "None"
    if history:
        bounded_hist = history[-6:]
        lines = []
        for turn in bounded_hist:
            role = "Student" if turn.get("role") == "user" else "Mentor"
            content = turn.get("content", "").replace("\n", " ")[:300]
            lines.append(f"{role}: {content}")
        history_str = "\n".join(lines)

    # 4. Invoke LLM via central runner
    variables = {
        "project_title": app_row[4],
        "project_description": (app_row[5] or "")[:800],
        "project_category": app_row[6] or "General",
        "project_difficulty": app_row[7] or "intermediate",
        "milestone_info": milestone_info,
        "user_message": message[:1000],
        "chat_history": history_str,
    }

    res = ai_client.run(
        db=db,
        user_id=user_id,
        feature="mentor",
        prompt_version="v1",
        variables=variables,
        output_model=MentorChatOutput,
        input_text=message[:500],
    )

    log_id = res.get("ai", {}).get("log_id")
    if log_id:
        db.execute(
            text("""
                UPDATE ai_logs
                   SET output = output || jsonb_build_object('application_id', :aid)
                 WHERE id = CAST(:lid AS bigint)
            """),
            {"aid": str(application_id), "lid": log_id},
        )
        db.commit()

    mentor_output: MentorChatOutput = res["result"]
    return {
        "ai": res["ai"],
        "result": mentor_output.model_dump(),
    }
