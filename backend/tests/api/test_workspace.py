"""Tests for Workspace API — T-WRK-01 through T-WRK-03, task progress, personal sub-tasks.
Uses real PostgreSQL (AGENTS.md).
"""
import uuid
from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import get_db


def _login(client: TestClient, email: str, password: str) -> dict:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _nova_headers(client: TestClient) -> dict:
    return _login(client, "contact@novalabs.com", "NovaLabs2026!")


def _student_headers(client: TestClient, email: str = "ananya@example.com") -> dict:
    return _login(client, email, "StudentPass2026!")


def _admin_headers(client: TestClient) -> dict:
    return _login(client, "admin@projectproof.ai", "AdminSecure2026!")


def _setup_active_workspace(client: TestClient):
    """Helper to create project with milestones, apply student, and select student."""
    nova_h = _nova_headers(client)
    student_h = _student_headers(client)

    # 1. Create project
    p_res = client.post("/api/v1/companies/me/projects", json={
        "title": f"Workspace Project {uuid.uuid4().hex[:6]}",
        "description": "A workspace testing project with multiple milestones and tasks.",
        "difficulty": "intermediate",
        "duration_days": 14,
        "max_selected": 2,
    }, headers=nova_h)
    assert p_res.status_code == 201, p_res.text
    pid = p_res.json()["id"]

    # 2. Add milestones with tasks
    m_res = client.put(f"/api/v1/projects/{pid}/milestones", json={
        "milestones": [
            {
                "title": "Milestone 1: Scaffold",
                "due_day_offset": 4,
                "tasks": [{"title": "Setup repository"}, {"title": "Configure database"}],
            },
            {
                "title": "Milestone 2: Completion",
                "due_day_offset": 14,
                "tasks": [{"title": "Implement core endpoints"}],
            },
        ]
    }, headers=nova_h)
    assert m_res.status_code == 200, m_res.text

    # 3. Publish project
    pub_res = client.post(f"/api/v1/projects/{pid}/publish", headers=nova_h)
    assert pub_res.status_code == 200, pub_res.text

    # 4. Student applies
    app_res = client.post(f"/api/v1/projects/{pid}/applications", json={
        "cover_note": "Ready to work on this!",
    }, headers=student_h)
    assert app_res.status_code == 201, app_res.text
    app_id = app_res.json()["id"]

    # 5. Company selects student
    sel_res = client.post(f"/api/v1/applications/{app_id}/select", headers=nova_h)
    assert sel_res.status_code == 200, sel_res.text

    return pid, app_id, nova_h, student_h


class TestWorkspace:
    def test_t_wrk_01_due_dates_equal_start_date_plus_offset(self, client: TestClient):
        """T-WRK-01 (FR-WRK-1): Due dates equal start date plus offset."""
        _pid, app_id, nova_h, student_h = _setup_active_workspace(client)

        res = client.get(f"/api/v1/applications/{app_id}/workspace", headers=student_h)
        assert res.status_code == 200, res.text
        data = res.json()

        assert data["application_id"] == app_id
        assert data["status"] == "in_progress"
        assert data["started_at"] is not None

        started = datetime.fromisoformat(data["started_at"])
        milestones = data["milestones"]
        assert len(milestones) == 2

        m1 = milestones[0]
        assert m1["due_day_offset"] == 4
        assert m1["due_date"] is not None
        due1 = datetime.fromisoformat(m1["due_date"])
        diff1 = (due1 - started).total_seconds()
        assert abs(diff1 - (4 * 86400)) < 2.0  # within 2 seconds

        m2 = milestones[1]
        assert m2["due_day_offset"] == 14
        due2 = datetime.fromisoformat(m2["due_date"])
        diff2 = (due2 - started).total_seconds()
        assert abs(diff2 - (14 * 86400)) < 2.0

        # Also company can view workspace
        comp_res = client.get(f"/api/v1/applications/{app_id}/workspace", headers=nova_h)
        assert comp_res.status_code == 200

    def test_t_wrk_02_student_checks_in_another_student_application(self, client: TestClient):
        """T-WRK-02 (FR-WRK-2): Student checks in on another student's application -> 404."""
        _pid, app_id, nova_h, student_h = _setup_active_workspace(client)

        # Get milestone id
        ws_res = client.get(f"/api/v1/applications/{app_id}/workspace", headers=student_h)
        m_id = ws_res.json()["milestones"][0]["id"]

        # Different student (Dev)
        dev_h = _student_headers(client, email="rohit@example.com")
        unauth_checkin = client.post(f"/api/v1/applications/{app_id}/checkins", json={
            "milestone_id": m_id,
            "note": "Hacking into another student application",
        }, headers=dev_h)
        assert unauth_checkin.status_code == 404  # AGENTS.md rule 6: Another user's record returns 404

        # Proper owner student can check in
        checkin_res = client.post(f"/api/v1/applications/{app_id}/checkins", json={
            "milestone_id": m_id,
            "note": "Scaffold completed with full tests passing.",
            "evidence_url": "https://github.com/example/repo/commit/123",
        }, headers=student_h)
        assert checkin_res.status_code == 201
        checkin_id = checkin_res.json()["id"]

        # Company reviews check-in
        rev_res = client.post(f"/api/v1/checkins/{checkin_id}/review", json={
            "status": "accepted",
            "review_note": "Great job on the initial scaffold!",
        }, headers=nova_h)
        assert rev_res.status_code == 200
        assert rev_res.json()["status"] == "accepted"

    def test_task_progress_and_personal_subtasks(self, client: TestClient):
        """FR-WRK-7 & FR-WRK-8: Task progress and student personal sub-tasks."""
        _pid, app_id, _nova_h, student_h = _setup_active_workspace(client)

        ws_res = client.get(f"/api/v1/applications/{app_id}/workspace", headers=student_h)
        m1 = ws_res.json()["milestones"][0]
        company_task_id = m1["tasks"][0]["id"]

        # Update company task progress to done
        prog_res = client.put(
            f"/api/v1/applications/{app_id}/tasks/{company_task_id}/progress",
            json={"status": "done"},
            headers=student_h,
        )
        assert prog_res.status_code == 200
        assert prog_res.json()["status"] == "done"

        # Student creates personal sub-task
        subtask_res = client.post(
            f"/api/v1/applications/{app_id}/milestones/{m1['id']}/tasks",
            json={"title": "My personal debug task", "description": "Review docker logs"},
            headers=student_h,
        )
        assert subtask_res.status_code == 201
        subtask_id = subtask_res.json()["id"]

        # Attempt to delete company task -> 409 Conflict (FR-WRK-8)
        del_comp = client.delete(f"/api/v1/applications/{app_id}/tasks/{company_task_id}", headers=student_h)
        assert del_comp.status_code == 409

        # Student deletes own personal sub-task -> 204 No Content
        del_sub = client.delete(f"/api/v1/applications/{app_id}/tasks/{subtask_id}", headers=student_h)
        assert del_sub.status_code == 204

    def test_t_wrk_03_overdue_job_notifies_both_sides_once(self, client: TestClient):
        """T-WRK-03 (FR-WRK-4): Overdue job notifies both sides once."""
        _pid, app_id, _nova_h, _student_h = _setup_active_workspace(client)
        admin_h = _admin_headers(client)

        # Artificially shift started_at 30 days in the past so milestones are overdue
        db = next(get_db())
        db.execute(
            text("UPDATE applications SET started_at = now() - interval '30 days' WHERE id = :id"),
            {"id": app_id},
        )
        db.commit()

        # Run check-overdue job
        job_res1 = client.post("/api/v1/admin/jobs/check-overdue", headers=admin_h)
        assert job_res1.status_code == 200
        assert job_res1.json()["notified"] >= 1

        # Run check-overdue job a second time: duplicate notifications should NOT be sent
        job_res2 = client.post("/api/v1/admin/jobs/check-overdue", headers=admin_h)
        assert job_res2.status_code == 200
        assert job_res2.json()["notified"] == 0
