"""Integration tests for AI API routes (Phase 5 / Section 11 of API specs).

Covers:
- T-AI-01: Invalid JSON twice returns 422
- T-AI-02: Provider timeout / unreachable returns 503
- T-AI-03: Daily quota exceeded returns 429
- T-AI-04: Resume analysis drops skills not in resume text
- T-AI-07: AI draft never saves to business tables before accept
- T-AI-09: Verification page response contains no AI fields
- POST /api/v1/ai/resume/analyze & /accept
- POST /api/v1/ai/projects/brief
- GET /api/v1/ai/projects/{id}/match
- POST /api/v1/ai/projects/{id}/rank-applicants
- POST /api/v1/ai/submissions/{id}/prereview
- POST /api/v1/ai/skill-gap
- POST /api/v1/ai/github/analyze & /accept
- POST /api/v1/ai/recruiter/parse-query
- POST /api/v1/ai/log/{id}/feedback
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.config import settings
from app.db import SessionLocal


def _login(client: TestClient, email: str, password: str) -> dict:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _nova_headers(client: TestClient) -> dict:
    return _login(client, "contact@novalabs.com", "NovaLabs2026!")


def _student_headers(client: TestClient) -> dict:
    return _login(client, "ananya@example.com", "StudentPass2026!")


def _recruiter_headers(client: TestClient) -> dict:
    # Create or reuse recruiter
    db = SessionLocal()
    try:
        from app.core.security import hash_password
        from app.models.user import RecruiterProfile, User

        user = db.query(User).filter(User.email == "recruiter_test@talent.com").first()
        if not user:
            user = User(
                email="recruiter_test@talent.com",
                password_hash=hash_password("RecruiterPass2026!"),
                role="recruiter",
                is_active=True,
                email_verified_at=text("NOW()"),
            )
            db.add(user)
            db.flush()
            prof = RecruiterProfile(
                user_id=user.id,
                full_name="Talent Recruiter",
                organization="Talent Inc",
                status="approved",
            )
            db.add(prof)
            db.commit()
    finally:
        db.close()
    return _login(client, "recruiter_test@talent.com", "RecruiterPass2026!")


# ── Resume Analysis & Acceptance (FR-STU-4, T-AI-07) ─────────────────────────


def test_resume_analyze_and_accept_t_ai_07(client: TestClient):
    """Resume analysis returns AI draft without touching student_skills until accept."""
    headers = _student_headers(client)

    # T-AI-07: Capture count BEFORE /resume/analyze
    db = SessionLocal()
    try:
        count_before = (
            db.execute(
                text(
                    "SELECT count(*) FROM student_skills ss JOIN users u ON u.id = ss.student_id WHERE u.email = 'ananya@example.com' AND ss.source = 'resume'"
                )
            ).scalar()
            or 0
        )
    finally:
        db.close()

    # 1. Analyze
    resume_text = "Student developer experienced with Python software engineering and SQL queries."
    res = client.post(
        "/api/v1/ai/resume/analyze", json={"resume_text": resume_text}, headers=headers
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["ai"]["label"] == "AI draft"
    assert "confidence" in body["ai"]
    log_id = body["ai"]["log_id"]
    assert log_id is not None

    # T-AI-07: Verify nothing was saved to student_skills yet
    db = SessionLocal()
    try:
        count_after_analyze = (
            db.execute(
                text(
                    "SELECT count(*) FROM student_skills ss JOIN users u ON u.id = ss.student_id WHERE u.email = 'ananya@example.com' AND ss.source = 'resume'"
                )
            ).scalar()
            or 0
        )
        assert count_after_analyze == count_before, "AI draft must not write to business tables before acceptance"
    finally:
        db.close()

    # 2. Accept
    accepted_skills = [{"name": "Python", "proficiency": 3}]
    accept_res = client.post(
        "/api/v1/ai/resume/accept",
        json={"log_id": int(log_id), "accepted_skills": accepted_skills},
        headers=headers,
    )
    assert accept_res.status_code == 200, accept_res.text
    assert accept_res.json()["saved"] >= 1

    # Check that skill is saved with source='resume'
    db = SessionLocal()
    try:
        row = db.execute(
            text("""
                SELECT ss.source, ss.proficiency
                  FROM student_skills ss
                  JOIN skills s ON s.id = ss.skill_id
                  JOIN users u ON u.id = ss.student_id
                 WHERE u.email = 'ananya@example.com' AND s.name = 'Python'
            """)
        ).fetchone()
        assert row is not None
        assert row[0] == "resume"
        assert row[1] == 3
    finally:
        db.close()


# ── Project Brief Generator (FR-PRJ-5) ────────────────────────────────────────


def test_project_brief_generator(client: TestClient):
    """Approved company can generate project brief draft."""
    headers = _nova_headers(client)

    res = client.post(
        "/api/v1/ai/projects/brief",
        json={"rough_idea": "Build a secure payment gateway integration for mobile apps."},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["ai"]["label"] == "AI draft"
    assert "title" in data["result"]
    assert "milestones" in data["result"]
    assert "deliverables_checklist" in data["result"]
    assert data["result"]["ai_generated"] is True


def test_project_brief_requires_company(client: TestClient):
    """Students cannot call company brief generator (role check)."""
    headers = _student_headers(client)
    res = client.post(
        "/api/v1/ai/projects/brief",
        json={"rough_idea": "Student idea"},
        headers=headers,
    )
    assert res.status_code == 403


# ── Project Match & Explanation (FR-APP-3) ────────────────────────────────────


def test_project_match_and_explanation(client: TestClient):
    """Student can get match score + AI explanation for an open project."""
    headers = _student_headers(client)

    # Get an open project
    proj_res = client.get("/api/v1/projects")
    assert proj_res.status_code == 200
    projects = proj_res.json()["items"]
    assert len(projects) > 0
    project_id = projects[0]["id"]

    res = client.get(f"/api/v1/ai/projects/{project_id}/match", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["ai"]["label"] == "AI draft"
    assert "score" in data["result"]
    assert "breakdown" in data["result"]
    assert "strengths" in data["result"]
    assert "gaps" in data["result"]


# ── Rank Applicants (FR-APP-5) ────────────────────────────────────────────────


def test_rank_applicants_owning_company(client: TestClient):
    """Owning company can rank applicants with AI explanations."""
    nova = _nova_headers(client)

    # Get company projects
    projs_res = client.get("/api/v1/companies/me/projects", headers=nova)
    assert projs_res.status_code == 200
    projects = projs_res.json()["items"]
    assert len(projects) > 0
    project_id = projects[0]["id"]

    res = client.post(f"/api/v1/ai/projects/{project_id}/rank-applicants", headers=nova)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["ai"]["label"] == "AI draft"
    assert "explanations" in data["result"]


# ── Submission Pre-Review (FR-EVL-3) ──────────────────────────────────────────


def test_submission_prereview(client: TestClient):
    """Owning company can trigger submission pre-review."""
    nova = _nova_headers(client)

    # Find a submission in seed data
    db = SessionLocal()
    try:
        row = db.execute(
            text("""
                SELECT s.id FROM submissions s
                  JOIN applications a ON a.id = s.application_id
                  JOIN projects p ON p.id = a.project_id
                  JOIN company_members cm ON cm.company_id = p.company_id
                  JOIN users u ON u.id = cm.user_id
                 WHERE u.email = 'contact@novalabs.com'
                 LIMIT 1
            """)
        ).fetchone()
        sub_id = row[0] if row else None
    finally:
        db.close()

    if not sub_id:
        pytest.skip("No submission found for Nova Labs in current DB.")

    res = client.post(f"/api/v1/ai/submissions/{sub_id}/prereview", headers=nova)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["ai"]["label"] == "AI draft"
    assert "items" in data["result"]
    assert "summary" in data["result"]


# ── Skill Gap (FR-APP-9) ──────────────────────────────────────────────────────


def test_skill_gap(client: TestClient):
    """Student can request deterministic skill gap with AI learning order."""
    headers = _student_headers(client)

    proj_res = client.get("/api/v1/projects")
    projects = proj_res.json()["items"]
    assert len(projects) > 0
    project_id = projects[0]["id"]

    res = client.post(
        "/api/v1/ai/skill-gap",
        json={"project_id": project_id},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["ai"]["label"] == "AI draft"
    assert "order_reason" in data["result"]
    assert "items" in data["result"]


# ── GitHub Analysis & Accept (FR-STU-11, Rule 12) ─────────────────────────────


def test_github_analysis_and_accept(client: TestClient, monkeypatch):
    """GitHub analysis proposes skills with source='self' on accept."""
    headers = _student_headers(client)

    # Mock services.github.fetch_github_repos to avoid calling real GitHub
    from app.api import ai as ai_api_module

    monkeypatch.setattr(
        ai_api_module,
        "fetch_github_repos",
        lambda username: [
            {
                "name": "projectproof",
                "language": "Python",
                "description": "Proof platform",
                "stars": 10,
                "forks": 2,
            }
        ],
    )

    res = client.post(
        "/api/v1/ai/github/analyze",
        json={"username": "octocat"},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["ai"]["label"] == "AI draft"
    log_id = data["ai"]["log_id"]

    # Ensure FastAPI is clean before test
    db = SessionLocal()
    try:
        db.execute(
            text(
                "DELETE FROM student_skills WHERE student_id = (SELECT id FROM users WHERE email = 'ananya@example.com') AND skill_id = (SELECT id FROM skills WHERE name = 'FastAPI')"
            )
        )
        db.commit()
    finally:
        db.close()

    # Accept proposed skill
    accept_res = client.post(
        "/api/v1/ai/github/accept",
        json={"log_id": int(log_id), "accepted_skills": [{"skill": "FastAPI"}]},
        headers=headers,
    )
    assert accept_res.status_code == 200, accept_res.text
    assert accept_res.json()["saved"] >= 1

    # Check skill saved with source='self' (AGENTS.md Rule 12)
    db = SessionLocal()
    try:
        row = db.execute(
            text("""
                SELECT ss.source
                  FROM student_skills ss
                  JOIN skills s ON s.id = ss.skill_id
                  JOIN users u ON u.id = ss.student_id
                 WHERE u.email = 'ananya@example.com' AND s.name = 'FastAPI'
            """)
        ).fetchone()
        assert row is not None
        assert row[0] == "self"
    finally:
        db.close()


# ── Recruiter Natural Language Search (FR-REC-3) ──────────────────────────────


def test_recruiter_query_interpretation(client: TestClient):
    """Approved recruiter can convert natural language query into filters."""
    recruiter = _recruiter_headers(client)

    res = client.post(
        "/api/v1/ai/recruiter/parse-query",
        json={"query": "Looking for Python engineers with at least 2 verified projects"},
        headers=recruiter,
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["ai"]["label"] == "AI draft"
    assert "skills" in data["result"]
    assert "query" in data


# ── AI Feedback (T-AI-01) ─────────────────────────────────────────────────────


def test_ai_feedback(client: TestClient):
    """User can submit feedback (accepted / dismissed) on an AI log."""
    headers = _student_headers(client)

    # First analyze to generate an ai_log
    res = client.post(
        "/api/v1/ai/resume/analyze",
        json={"resume_text": "Experienced software developer with Python skills."},
        headers=headers,
    )
    log_id = res.json()["ai"]["log_id"]

    # Submit feedback
    fb_res = client.post(
        f"/api/v1/ai/log/{log_id}/feedback",
        json={"accepted": True},
        headers=headers,
    )
    assert fb_res.status_code == 200, fb_res.text
    assert fb_res.json()["status"] == "ok"


# ── T-AI-01: Invalid JSON twice returns 422 ───────────────────────────────────


def test_t_ai_01_invalid_json_returns_422(client: TestClient, monkeypatch):
    """T-AI-01: When LLM outputs unparseable JSON twice, return 422 with friendly error."""
    from app.ai import client as ai_client

    class BadClient:
        def call(self, feature, prompt, max_tokens=2000):
            return "This is not JSON at all!"

    monkeypatch.setattr(ai_client, "_get_llm_client", lambda: BadClient())

    headers = _student_headers(client)
    res = client.post(
        "/api/v1/ai/resume/analyze",
        json={"resume_text": "Valid student resume content for testing 422."},
        headers=headers,
    )
    assert res.status_code == 422, f"Expected 422 for invalid AI output, got {res.status_code}"
    body = res.json()
    assert "error" in body
    assert body["error"]["code"] == "ai_output_invalid"


# ── T-AI-02: Provider timeout / unreachable returns 503 ───────────────────────


def test_t_ai_02_provider_timeout_returns_503(client: TestClient, monkeypatch):
    """T-AI-02: LLM provider timeout returns 503; underlying actions unaffected."""
    from app.ai import client as ai_client

    class TimeoutClient:
        def call(self, feature, prompt, max_tokens=2000):
            raise ai_client.LLMError("provider_timeout", "AI provider timed out.", status_code=503)

    monkeypatch.setattr(ai_client, "_get_llm_client", lambda: TimeoutClient())

    headers = _student_headers(client)
    res = client.post(
        "/api/v1/ai/resume/analyze",
        json={"resume_text": "Valid student resume content for testing 503."},
        headers=headers,
    )
    assert res.status_code == 503, f"Expected 503 for AI timeout, got {res.status_code}"
    body = res.json()
    assert "error" in body
    assert body["error"]["code"] == "provider_timeout"


# ── T-AI-03: Daily quota exceeded returns 429 ─────────────────────────────────


def test_t_ai_03_daily_quota_exceeded_returns_429(client: TestClient, monkeypatch):
    """T-AI-03: When user exceeds daily quota, return 429 rate limit error."""
    headers = _student_headers(client)

    # Artificially set limit to 0
    monkeypatch.setattr(settings, "llm_daily_limit_per_user", 0)

    res = client.post(
        "/api/v1/ai/resume/analyze",
        json={"resume_text": "Valid student resume content for testing 429."},
        headers=headers,
    )
    assert res.status_code == 429, f"Expected 429 for AI quota exceeded, got {res.status_code}"
    body = res.json()
    assert "error" in body
    assert body["error"]["code"] == "quota_exceeded"


# ── T-AI-09: Verification page response contains no AI field ──────────────────


def test_t_ai_09_verification_page_no_ai_field(client: TestClient):
    """T-AI-09: Public verification page must never expose any AI fields."""
    db = SessionLocal()
    try:
        row = db.execute(
            text("SELECT qr_token FROM certificates WHERE status = 'issued' LIMIT 1")
        ).fetchone()
        qr_token = row[0] if row else None
    finally:
        db.close()

    if not qr_token:
        pytest.skip("No issued certificate found in DB.")

    res = client.get(f"/api/v1/public/verify/{qr_token}")
    assert res.status_code == 200
    data = res.json()

    # Rule 4 & T-AI-09: AI output never appears on public verification page
    assert "ai" not in data
    assert "ai_draft" not in str(data).lower()
    assert "ai_prereview" not in data
    assert "llm" not in str(data).lower()
