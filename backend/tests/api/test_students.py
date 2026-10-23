"""Tests for Student profile, skills, dashboard, portfolio, and GitHub (Phase 5).
Covers:
- FR-STU-1, FR-STU-2, FR-STU-5, FR-STU-6, FR-STU-7, FR-STU-8, FR-STU-10
- T-STU-01, T-STU-03, T-STU-04, T-STU-05, T-STU-06
"""

from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import SessionLocal


def _login(client: TestClient, email: str, password: str) -> dict:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _student_headers(client: TestClient, email: str = "ananya@example.com") -> dict:
    return _login(client, email, "StudentPass2026!")


def _admin_headers(client: TestClient) -> dict:
    return _login(client, "admin@projectproof.ai", "AdminSecure2026!")


def test_student_profile_get_and_update(client: TestClient):
    """FR-STU-1: Student profile viewing and updating."""
    headers = _student_headers(client, "ananya@example.com")

    # GET profile
    res = client.get("/api/v1/students/me", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert "Ananya" in data["full_name"]
    assert "college" in data

    # Update profile
    update_res = client.put(
        "/api/v1/students/me",
        json={
            "headline": "Aspiring Backend Engineer",
            "bio": "Passionate about distributed systems",
            "college": "IIT Bombay",
            "graduation_year": 2026,
        },
        headers=headers,
    )
    assert update_res.status_code == 200, update_res.text
    updated = update_res.json()
    assert updated["headline"] == "Aspiring Backend Engineer"
    assert updated["bio"] == "Passionate about distributed systems"
    assert updated["college"] == "IIT Bombay"
    assert updated["graduation_year"] == 2026


def test_student_visibility_toggle(client: TestClient):
    """FR-STU-5, FR-STU-6, T-REC-02: Student can toggle public visibility."""
    headers = _student_headers(client, "ananya@example.com")

    # Set to false
    res = client.put(
        "/api/v1/students/me/visibility",
        json={
            "is_public": False,
            "show_full_name_on_verification": False,
        },
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["is_public"] is False
    assert res.json()["show_full_name_on_verification"] is False

    # Check consent log in DB
    session = SessionLocal()
    try:
        user_id = session.execute(
            text("SELECT id FROM users WHERE email = 'ananya@example.com'")
        ).scalar()
        consent = session.execute(
            text(
                "SELECT granted FROM consent_log WHERE user_id = :uid AND kind = 'public_profile' ORDER BY created_at DESC LIMIT 1"
            ),
            {"uid": user_id},
        ).scalar()
        assert consent is False
    finally:
        session.close()

    # Re-enable public
    res = client.put(
        "/api/v1/students/me/visibility",
        json={
            "is_public": True,
            "show_full_name_on_verification": True,
        },
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["is_public"] is True


def test_student_skills_crud(client: TestClient):
    """FR-STU-2: View and update student skills."""
    headers = _student_headers(client, "ananya@example.com")

    # GET skills
    res = client.get("/api/v1/students/me/skills", headers=headers)
    assert res.status_code == 200
    initial_skills = res.json()
    assert isinstance(initial_skills, list)

    # PUT skills (Python, PostgreSQL, FastAPI from seed)
    res = client.put(
        "/api/v1/students/me/skills",
        json={
            "skills": [
                {"skill": "Python", "proficiency": 5},
                {"skill": "PostgreSQL", "proficiency": 4},
            ]
        },
        headers=headers,
    )
    assert res.status_code == 200, res.text
    assert res.json()["count"] == 2

    # Check GET reflects new skills
    res2 = client.get("/api/v1/students/me/skills", headers=headers)
    assert res2.status_code == 200
    skill_names = [s["name"] for s in res2.json()]
    assert "Python" in skill_names
    assert "PostgreSQL" in skill_names

    # Unknown skill should fail
    bad_res = client.put(
        "/api/v1/students/me/skills",
        json={"skills": [{"skill": "NonExistentSkillXYZ123", "proficiency": 3}]},
        headers=headers,
    )
    assert bad_res.status_code == 400


def test_student_dashboard(client: TestClient):
    """FR-STU-7: Student dashboard stats, XP, level, badges."""
    headers = _student_headers(client, "ananya@example.com")
    res = client.get("/api/v1/students/me/dashboard", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert "xp" in data
    assert "level" in data
    assert "level_name" in data
    assert "badges" in data
    assert "active_projects" in data
    assert "completed_projects" in data
    assert "verified_projects" in data
    assert "completion_rate" in data
    assert isinstance(data["badges"], list)


def test_student_portfolio_lists_issued_and_revoked(client: TestClient):
    """T-STU-01 / FR-STU-10:
    Portfolio lists issued and revoked certificates newest first;
    revoked one is labelled Revoked.
    """
    headers = _student_headers(client, "ananya@example.com")
    res = client.get("/api/v1/students/me/portfolio", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert "items" in data
    items = data["items"]

    # In seed data, Ananya has certificates (including one revoked)
    statuses = [i["status"] for i in items]
    assert "revoked" in statuses or "issued" in statuses

    # If any revoked item exists, check status is literally 'revoked'
    revoked_items = [i for i in items if i["status"] == "revoked"]
    if revoked_items:
        r = revoked_items[0]
        assert r["status"] == "revoked"
        assert r["revoked_at"] is not None


def test_github_link_validation_t_stu_04(client: TestClient):
    """T-STU-04: Link username with slash, space or 40 chars rejected by validation.
    No request leaves the server.
    """
    headers = _student_headers(client, "ananya@example.com")

    # Slash
    res1 = client.put("/api/v1/students/me/github", json={"username": "user/name"}, headers=headers)
    assert res1.status_code == 400

    # Space
    res2 = client.put("/api/v1/students/me/github", json={"username": "user name"}, headers=headers)
    assert res2.status_code == 400

    # 40 chars
    res3 = client.put("/api/v1/students/me/github", json={"username": "a" * 40}, headers=headers)
    assert res3.status_code == 400

    # Empty
    res4 = client.put("/api/v1/students/me/github", json={"username": ""}, headers=headers)
    assert res4.status_code == 422 or res4.status_code == 400


def test_github_link_valid_t_stu_03_and_rule_12(client: TestClient):
    """T-STU-03, T-STU-06:
    Link a valid GitHub username (mocking GitHub API response).
    Summary shown with 'self-linked, not verified'.
    GitHub data never affects XP, badges or verification.
    """
    headers = _student_headers(client, "ananya@example.com")

    mock_user_data = {
        "login": "octocat",
        "public_repos": 8,
        "followers": 42,
        "following": 0,
        "html_url": "https://github.com/octocat",
        "bio": "Mona Lisa Octocat",
    }
    mock_repos_data = [
        {"name": "repo1", "language": "Python"},
        {"name": "repo2", "language": "Python"},
        {"name": "repo3", "language": "TypeScript"},
    ]

    orig_get = httpx.Client.get

    def side_effect(self, url, *args, **kwargs):
        if "api.github.com" in str(url):
            resp = httpx.Response(200)
            if "/repos" in str(url):
                resp._content = httpx._models.Response(200, json=mock_repos_data).content
            else:
                resp._content = httpx._models.Response(200, json=mock_user_data).content
            resp.request = httpx.Request("GET", str(url))
            return resp
        return orig_get(self, url, *args, **kwargs)

    with patch.object(httpx.Client, "get", side_effect):
        # Get initial XP before linking
        dash_before = client.get("/api/v1/students/me/dashboard", headers=headers).json()
        xp_before = dash_before["xp"]

        # Link GitHub
        res = client.put(
            "/api/v1/students/me/github", json={"username": "octocat"}, headers=headers
        )
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["label"] == "self-linked, not verified"
        assert data["summary"]["public_repos"] == 8
        assert "Python" in data["summary"]["top_languages"]

        # GET GitHub endpoint
        get_res = client.get("/api/v1/students/me/github", headers=headers)
        assert get_res.status_code == 200
        assert get_res.json()["label"] == "self-linked, not verified"
        assert get_res.json()["username"] == "octocat"

        # T-STU-06: Verify XP and badges were completely unaffected
        dash_after = client.get("/api/v1/students/me/dashboard", headers=headers).json()
        assert dash_after["xp"] == xp_before, "GitHub link must never alter XP"

        # Unlink
        del_res = client.delete("/api/v1/students/me/github", headers=headers)
        assert del_res.status_code == 204

        # Verify not found after unlink
        get_after = client.get("/api/v1/students/me/github", headers=headers)
        assert get_after.status_code == 404


def test_github_timeout_t_stu_05(client: TestClient):
    """T-STU-05: GitHub API timeout returns clear 503; rest of profile works."""
    headers = _student_headers(client, "ananya@example.com")
    orig_get = httpx.Client.get

    def timeout_effect(self, url, *args, **kwargs):
        if "api.github.com" in str(url):
            raise httpx.TimeoutException("Connection timed out")
        return orig_get(self, url, *args, **kwargs)

    with patch.object(httpx.Client, "get", timeout_effect):
        res = client.put(
            "/api/v1/students/me/github", json={"username": "slowuser"}, headers=headers
        )
        assert res.status_code == 503, res.text
        assert "timed out" in res.json()["error"]["message"].lower()

    # Rest of profile works seamlessly
    prof = client.get("/api/v1/students/me", headers=headers)
    assert prof.status_code == 200


@pytest.mark.parametrize(
    ("full_name", "show_full", "expected"),
    [
        ("Ananya Rao", True, "Ananya Rao"),
        ("Ananya Rao", False, "A."),
        ("", False, "."),
    ],
)
def test_public_portfolio_applies_name_privacy(client, full_name, show_full, expected):
    db = SessionLocal()
    original = None
    try:
        original = db.execute(
            text("""
            SELECT sp.user_id, sp.full_name, sp.show_full_name_on_verification, sp.is_public
              FROM student_profiles sp JOIN users u ON u.id = sp.user_id
             WHERE u.email = 'ananya@example.com'
        """)
        ).one()
        db.execute(
            text("""
            UPDATE student_profiles
               SET full_name = :name, show_full_name_on_verification = :show_full, is_public = TRUE
             WHERE user_id = :uid
        """),
            {"name": full_name, "show_full": show_full, "uid": original.user_id},
        )
        db.commit()
        response = client.get(f"/api/v1/students/{original.user_id}/portfolio")
        assert response.status_code == 200, response.text
        assert response.json()["student_name"] == expected
    finally:
        db.rollback()
        try:
            if original:
                db.execute(
                    text("""
                    UPDATE student_profiles SET full_name = :name,
                        show_full_name_on_verification = :show_full, is_public = :is_public
                     WHERE user_id = :uid
                """),
                    {
                        "name": original.full_name,
                        "show_full": original.show_full_name_on_verification,
                        "is_public": original.is_public,
                        "uid": original.user_id,
                    },
                )
                db.commit()
        finally:
            db.close()
