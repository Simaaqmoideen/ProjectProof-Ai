"""Shared AI service layer — the ONLY code that talks to an LLM provider.

Contract: run(feature, prompt_version, variables, output_model, user) → validated object.
Steps per call (docs/06 section 2):
  1. Quota check
  2. Build prompt from versioned file
  3. Call provider with timeout
  4. Parse + validate Pydantic model; retry once
  5. Feature-specific checks
  6. Compute confidence
  7. Write ai_logs row
  8. Return {ai: AIMeta, result: validated_object}
  9. Save nothing to business tables here.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings

T = TypeVar("T", bound=BaseModel)

_PROMPTS_DIR = Path(__file__).parent / "prompts"

# ── Mock provider ─────────────────────────────────────────────────────────────

_MOCK_RESPONSES: dict[str, Any] = {
    "resume_analysis": {
        "skills": [{"name": "Python", "evidence": "Built Flask API for university project"}],
        "education": [
            {"institution": "Example University", "degree": "B.Sc. Computer Science", "year": 2024}
        ],
        "projects": [
            {
                "title": "Library System",
                "summary": "Django web app",
                "technologies": ["Python", "Django"],
            }
        ],
        "experience": [],
        "certifications": [],
    },
    "brief_generator": {
        "title": "E-Commerce REST API",
        "description": "Build a scalable REST API for an e-commerce platform with product management, cart, and checkout flows.",
        "category": "Web Development",
        "difficulty": "intermediate",
        "duration_days": 30,
        "required_skills": ["Python", "REST API"],
        "milestones": [
            {
                "title": "Setup & Auth",
                "description": "Project scaffold and JWT authentication.",
                "due_day_offset": 7,
            },
            {
                "title": "Product Module",
                "description": "CRUD endpoints for products.",
                "due_day_offset": 14,
            },
            {
                "title": "Cart & Checkout",
                "description": "Cart management and order creation.",
                "due_day_offset": 21,
            },
            {"title": "Deployment", "description": "Dockerize and deploy.", "due_day_offset": 30},
        ],
        "deliverables_checklist": [
            "Authentication endpoints work",
            "Product CRUD tested",
            "Cart and checkout flow implemented",
            "README with setup instructions",
            "Postman collection included",
        ],
    },
    "match_explanation": {
        "explanations": [],
    },
    "pre_review": {
        "items": [],
        "overall_note": "AI draft review pending.",
    },
    "recruiter_search": {
        "skills": [],
        "min_xp": None,
        "min_verified_projects": None,
        "category": None,
        "verified_only": False,
    },
    "skill_gap": {
        "order_reason": "Start with the foundational skill before the specialized one.",
        "items": [],
    },
    "github_analysis": {
        "summary": "Active developer with contributions across multiple repositories.",
        "skills": [],
    },
    "mentor": {
        "response": "Consider breaking down the endpoint implementation into routes, models, and validation layers. Check FastAPI dependency injection documentation for database sessions.",
        "contains_code": False,
        "suggested_next_steps": [
            "Review SQLAlchemy documentation on async sessions",
            "Write a unit test for the authentication middleware",
        ],
    },
    "feedback_drafter": {
        "strengths": ["Clean separation of repository and service layers", "Good test coverage"],
        "improvements": ["Add rate limiting headers to public verification route"],
        "next_steps": ["Explore background workers for heavy PDF rendering"],
        "suggested_public_summary": "Successfully delivered full RESTful API with automated test suite and clean architecture.",
    },
    "resume_rewriter": {
        "bullets": [
            "Architected and implemented a secure RESTful API with automated milestone verification, reducing manual review latency.",
            "Integrated robust unit test suite covering auth, data integrity triggers, and rate-limiting rules.",
        ],
    },
}


from app.core.errors import AppError


class LLMError(AppError):
    """Raised when the LLM call fails unrecoverably."""

    def __init__(self, code: str, message: str, status_code: int = 500):
        super().__init__(code=code, message=message, status_code=status_code)


class _MockLLMClient:
    """Fake LLM client used in development and tests (llm_provider='mock')."""

    def call(self, feature: str, prompt: str, max_tokens: int = 2000) -> str:
        resp = _MOCK_RESPONSES.get(feature, {})
        return json.dumps(resp)


class _OpenAILLMClient:
    """Thin OpenAI client. Only imported when llm_provider='openai'."""

    def __init__(self, api_key: str):
        try:
            import openai  # type: ignore
        except ImportError as exc:
            raise LLMError(
                "provider_unavailable",
                "openai package not installed. Run: pip install openai",
                status_code=503,
            ) from exc
        self._client = openai.OpenAI(api_key=api_key)

    def call(self, feature: str, prompt: str, max_tokens: int = 2000) -> str:
        import openai  # type: ignore

        try:
            resp = self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
                timeout=settings.ai_timeout_seconds
                if hasattr(settings, "ai_timeout_seconds")
                else 30,
            )
            return resp.choices[0].message.content or "{}"
        except openai.RateLimitError as exc:
            raise LLMError(
                "provider_rate_limit", "AI provider rate limit exceeded.", status_code=429
            ) from exc
        except openai.APITimeoutError as exc:
            raise LLMError("provider_timeout", "AI provider timed out.", status_code=503) from exc
        except openai.APIError as exc:
            raise LLMError("provider_error", f"AI provider error: {exc}", status_code=503) from exc


def _get_llm_client():
    if settings.llm_provider == "openai":
        return _OpenAILLMClient(settings.llm_api_key)
    return _MockLLMClient()


# ── Prompt loading ────────────────────────────────────────────────────────────


def _load_prompt(feature: str, version: str, variables: dict[str, str]) -> str:
    """Load versioned prompt file and substitute {{VAR}} placeholders.

    Falls back to a minimal inline prompt if the file does not exist yet.
    """
    prompt_file = _PROMPTS_DIR / feature / f"{version}.md"
    if prompt_file.exists():
        template = prompt_file.read_text(encoding="utf-8")
    else:
        # Minimal fallback — feature name + variables serialised as JSON data block.
        template = (
            f"You are a JSON-only assistant for the '{feature}' task.\n"
            "Return ONLY valid JSON matching the required schema.\n"
            "Input data:\n```\n{{DATA}}\n```"
        )
        variables = {"DATA": json.dumps(variables, ensure_ascii=False)}

    for key, value in variables.items():
        template = template.replace(f"{{{{{key}}}}}", value)
    return template


# ── Confidence ────────────────────────────────────────────────────────────────


def _compute_confidence(
    input_text: str,
    needed_retry: bool,
    check_pass_rate: float = 1.0,
) -> str:
    """Compute low/medium/high from verifiable signals (docs/06 section 3)."""
    if len(input_text) < 50:
        return "low"
    conf = "high"
    if needed_retry:
        conf = "medium"
    if check_pass_rate < 0.5:
        conf = "low"
    elif check_pass_rate < 0.8 and conf == "high":
        conf = "medium"
    return conf


# ── Quota check ───────────────────────────────────────────────────────────────


def _check_quota(db: Session, user_id: uuid.UUID) -> None:
    """Raise LLMError(429) if the user has exceeded their daily AI quota."""
    row = db.execute(
        text("""
            SELECT COUNT(*) FROM ai_logs
             WHERE user_id = :uid
               AND created_at >= NOW() - INTERVAL '24 hours'
        """),
        {"uid": user_id},
    ).scalar()
    if (row or 0) >= settings.llm_daily_limit_per_user:
        raise LLMError(
            "quota_exceeded", "Daily AI usage limit reached. Try again tomorrow.", status_code=429
        )


# ── ai_logs write ─────────────────────────────────────────────────────────────


def _write_log(
    db: Session,
    user_id: uuid.UUID,
    feature: str,
    prompt_version: str,
    input_ref: str,
    output: dict,
    confidence: str,
    latency_ms: int,
) -> str:
    """Insert an ai_logs row and return its bigint ID as a string.
    Never logs raw personal text (AGENTS.md rule 9).
    """
    row = db.execute(
        text("""
            INSERT INTO ai_logs
                (user_id, feature, prompt_version, model, input_ref,
                 output, confidence, latency_ms, created_at)
            VALUES
                (:uid, :feature, :pv, :model, :input_ref,
                 CAST(:output AS jsonb), CAST(:conf AS ai_confidence), :lat, NOW())
            RETURNING id
        """),
        {
            "uid": user_id,
            "feature": feature,
            "pv": prompt_version,
            "model": settings.llm_provider,
            "input_ref": input_ref,
            "output": json.dumps(output),
            "conf": confidence,
            "lat": latency_ms,
        },
    ).fetchone()
    return str(row[0]) if row else "0"


# ── Main entry point ──────────────────────────────────────────────────────────


def run(
    *,
    db: Session,
    user_id: uuid.UUID,
    feature: str,
    prompt_version: str = "v1",
    variables: dict[str, str],
    output_model: type[T],
    input_text: str = "",
    check_pass_rate: float = 1.0,
) -> dict[str, Any]:
    """Call the LLM, validate output, log, return {ai: AIMeta, result: T}.

    This is the only function in the codebase that calls an LLM provider.
    """
    from app.ai.schemas import AIMeta

    _check_quota(db, user_id)

    prompt = _load_prompt(feature, prompt_version, variables)
    client = _get_llm_client()

    needed_retry = False
    start = time.monotonic()
    raw = client.call(feature, prompt)
    first_attempt_ok = True

    try:
        parsed = json.loads(raw)
        result = output_model.model_validate(parsed)
    except Exception:
        first_attempt_ok = False
        # One repair retry
        repair_prompt = (
            f"{prompt}\n\n"
            "Your previous response could not be parsed. "
            "Return ONLY valid JSON with no extra text."
        )
        try:
            raw = client.call(feature, repair_prompt)
            parsed = json.loads(raw)
            result = output_model.model_validate(parsed)
            needed_retry = True
        except Exception as exc:
            raise LLMError(
                "ai_output_invalid", f"AI output could not be validated: {exc}", status_code=422
            ) from exc

    latency_ms = int((time.monotonic() - start) * 1000)
    confidence = _compute_confidence(input_text, needed_retry, check_pass_rate)

    # input_ref = SHA-256 of the raw input text (never the text itself)
    input_ref = hashlib.sha256(input_text.encode()).hexdigest()[:16] if input_text else "n/a"

    log_id = _write_log(
        db,
        user_id=user_id,
        feature=feature,
        prompt_version=prompt_version,
        input_ref=input_ref,
        output=result.model_dump(),
        confidence=confidence,
        latency_ms=latency_ms,
    )
    db.commit()  # commit the ai_logs row so it persists for subsequent accept/feedback routes

    return {
        "ai": AIMeta(label="AI draft", confidence=confidence, log_id=log_id).model_dump(),
        "result": result,
        "_first_attempt_ok": first_attempt_ok,
    }
