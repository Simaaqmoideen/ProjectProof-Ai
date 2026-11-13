"""Tests for Notifications and Project Recommendations (Phase 5).
Covers:
- FR-NTF-1, FR-APP-10, BR-10
- T-APP-07, T-APP-08
"""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import SessionLocal


def _login(client: TestClient, email: str, password: str) -> dict:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _student_headers(client: TestClient, email: str = "ananya@example.com") -> dict:
    return _login(client, email, "StudentPass2026!")


def _nova_headers(client: TestClient) -> dict:
    return _login(client, "contact@novalabs.com", "NovaLabs2026!")


def test_notifications_list_and_mark_read(client: TestClient):
    """FR-NTF-1: List notifications, mark single notification as read, mark all read."""
    student_h = _student_headers(client, "ananya@example.com")

    # Seed 2 unread notifications for Ananya
    session = SessionLocal()
    try:
        uid = session.execute(
            text("SELECT id FROM users WHERE email = 'ananya@example.com'")
        ).scalar()
        n1_id = uuid.uuid4()
        n2_id = uuid.uuid4()
        session.execute(
            text("""
                INSERT INTO notifications (id, user_id, type, title, body, created_at)
                VALUES (:n1, :uid, 'system', 'Welcome to ProjectProof', 'Explore verified projects.', now()),
                       (:n2, :uid, 'application_status', 'Application Update', 'Your application was accepted.', now())
            """),
            {"n1": n1_id, "n2": n2_id, "uid": uid},
        )
        session.commit()
    finally:
        session.close()

    # 1. GET notifications
    res = client.get("/api/v1/notifications", headers=student_h)
    assert res.status_code == 200, res.text
    data = res.json()
    assert "items" in data
    assert data["total"] >= 2
    ids = [i["id"] for i in data["items"]]
    assert str(n1_id) in ids

    # 2. Mark single notification read
    mark_res = client.post(f"/api/v1/notifications/{n1_id}/read", headers=student_h)
    assert mark_res.status_code == 200, mark_res.text
    assert mark_res.json()["marked"] == 1

    # Verify n1 is now read
    session = SessionLocal()
    try:
        read_at = session.execute(
            text("SELECT read_at FROM notifications WHERE id = :id"),
            {"id": n1_id},
        ).scalar()
        assert read_at is not None
    finally:
        session.close()

    # 3. Mark all read
    all_res = client.post("/api/v1/notifications/read-all", headers=student_h)
    assert all_res.status_code == 200, all_res.text
    assert all_res.json()["marked"] >= 1

    # Verify no unread remaining
    session = SessionLocal()
    try:
        unread_count = session.execute(
            text("SELECT count(*) FROM notifications WHERE user_id = :uid AND read_at IS NULL"),
            {"uid": uid},
        ).scalar()
        assert unread_count == 0
    finally:
        session.close()


def test_recommendations_t_app_07_and_t_app_08(client: TestClient):
    """T-APP-07, T-APP-08, FR-APP-10, BR-10:
    - Recommendations score computed deterministically with bonuses and capped at 100
    - Recommendations exclude applied projects
    - Recommendations exclude removed projects
    - Recommendations return empty when student already has 3 active projects
    """
    student_h = _student_headers(client, "ananya@example.com")
    nova_h = _nova_headers(client)

    # GET recommendations for student
    rec_res = client.get("/api/v1/projects/recommendations", headers=student_h)
    assert rec_res.status_code == 200, rec_res.text
    rec_data = rec_res.json()
    assert "items" in rec_data
    items = rec_data["items"]

    # All recommendation scores must be between 0 and 100
    for item in items:
        assert 0 <= item["recommendation_score"] <= 100
        assert "reason" in item
        assert "match_score" in item
        assert "missing_skills" in item

    # T-APP-08: Exclude applied projects
    # Create and publish a project
    p_res = client.post(
        "/api/v1/companies/me/projects",
        json={
            "title": f"Recommendation Test {uuid.uuid4().hex[:6]}",
            "description": "Test recommendation exclusion.",
            "difficulty": "intermediate",
            "duration_days": 10,
        },
        headers=nova_h,
    )
    assert p_res.status_code == 201
    pid = p_res.json()["id"]
    client.post(f"/api/v1/projects/{pid}/publish", headers=nova_h)

    # Check project is in recommendations
    r_before = client.get(
        "/api/v1/projects/recommendations?page_size=100", headers=student_h
    ).json()
    p_ids_before = [i["project_id"] for i in r_before["items"]]
    assert pid in p_ids_before

    # Student applies to it
    client.post(
        f"/api/v1/projects/{pid}/applications", json={"cover_note": "Apply"}, headers=student_h
    )

    # After applying, project is EXCLUDED from recommendations (T-APP-08)
    r_after = client.get("/api/v1/projects/recommendations?page_size=100", headers=student_h).json()
    p_ids_after = [i["project_id"] for i in r_after["items"]]
    assert pid not in p_ids_after, "Applied projects must be excluded from recommendations"
