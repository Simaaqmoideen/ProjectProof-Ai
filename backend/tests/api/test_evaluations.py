"""Tests for Submissions, Evaluations, Appeals, and Certificate Transaction.
Covers T-EVL-01 through T-EVL-08, and T-CRT-01, T-CRT-02.
Uses real PostgreSQL (AGENTS.md).
"""
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import get_db


def _login(client: TestClient, email: str, password: str) -> dict:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _nova_headers(client: TestClient) -> dict:
    return _login(client, "contact@novalabs.com", "NovaLabs2026!")


def _keystone_headers(client: TestClient) -> dict:
    return _login(client, "contact@keystonesoft.io", "Keystone2026!")


def _student_headers(client: TestClient, email: str = "ananya@example.com") -> dict:
    return _login(client, email, "StudentPass2026!")


def _admin_headers(client: TestClient) -> dict:
    return _login(client, "admin@projectproof.ai", "AdminSecure2026!")


def _setup_in_progress_application(client: TestClient):
    """Helper to get an application in 'in_progress' status."""
    nova_h = _nova_headers(client)
    student_h = _student_headers(client)

    p_res = client.post("/api/v1/companies/me/projects", json={
        "title": f"Eval Test Project {uuid.uuid4().hex[:6]}",
        "description": "A project for evaluation and submission testing with required description.",
        "difficulty": "intermediate",
        "duration_days": 14,
        "max_selected": 1,
    }, headers=nova_h)
    assert p_res.status_code == 201, p_res.text
    pid = p_res.json()["id"]

    pub_res = client.post(f"/api/v1/projects/{pid}/publish", headers=nova_h)
    assert pub_res.status_code == 200, pub_res.text

    app_res = client.post(f"/api/v1/projects/{pid}/applications", json={
        "cover_note": "Ready to submit excellent work.",
    }, headers=student_h)
    assert app_res.status_code == 201, app_res.text
    app_id = app_res.json()["id"]

    sel_res = client.post(f"/api/v1/applications/{app_id}/select", headers=nova_h)
    assert sel_res.status_code == 200, sel_res.text

    return pid, app_id, nova_h, student_h


class TestEvaluations:
    def test_t_evl_01_submission_versions_and_fourth_rejected(self, client: TestClient):
        """T-EVL-01 (FR-EVL-1): Submissions up to 3 versions; 4th version rejected."""
        _pid, app_id, nova_h, student_h = _setup_in_progress_application(client)

        # Version 1
        sub1 = client.post(f"/api/v1/applications/{app_id}/submissions", json={
            "repo_url": "https://github.com/student/project-v1",
            "notes": "Initial delivery",
        }, headers=student_h)
        assert sub1.status_code == 201
        assert sub1.json()["version"] == 1

        # Simulate changes requested so student can submit v2
        client.post(f"/api/v1/submissions/{sub1.json()['id']}/evaluation", json={
            "overall_score": 50,
            "feedback": "Needs improvement on error handling.",
            "decision": "changes_requested",
        }, headers=nova_h)

        # Version 2
        sub2 = client.post(f"/api/v1/applications/{app_id}/submissions", json={
            "repo_url": "https://github.com/student/project-v2",
            "notes": "Fixed error handling",
        }, headers=student_h)
        assert sub2.status_code == 201
        assert sub2.json()["version"] == 2

        # Simulate changes requested so student can submit v3
        client.post(f"/api/v1/submissions/{sub2.json()['id']}/evaluation", json={
            "overall_score": 55,
            "feedback": "Better, but fix documentation.",
            "decision": "changes_requested",
        }, headers=nova_h)

        # Version 3
        sub3 = client.post(f"/api/v1/applications/{app_id}/submissions", json={
            "repo_url": "https://github.com/student/project-v3",
            "notes": "Added complete docs",
        }, headers=student_h)
        assert sub3.status_code == 201
        assert sub3.json()["version"] == 3

        # Simulate changes requested again
        client.post(f"/api/v1/submissions/{sub3.json()['id']}/evaluation", json={
            "overall_score": 58,
            "feedback": "One more pass needed.",
            "decision": "changes_requested",
        }, headers=nova_h)

        # 4th submission version -> Rejected (400)
        sub4 = client.post(f"/api/v1/applications/{app_id}/submissions", json={
            "repo_url": "https://github.com/student/project-v4",
            "notes": "Fourth attempt",
        }, headers=student_h)
        assert sub4.status_code == 400

    def test_t_evl_02_empty_or_invalid_deliverable(self, client: TestClient):
        """T-EVL-02 (FR-EVL-1): Submission requires at least one deliverable."""
        _pid, app_id, _nova_h, student_h = _setup_in_progress_application(client)

        # Neither repo_url nor file_key
        sub = client.post(f"/api/v1/applications/{app_id}/submissions", json={
            "notes": "Only notes, no deliverable",
        }, headers=student_h)
        assert sub.status_code == 422 or sub.status_code == 400

    def test_t_evl_03_approve_with_score_below_60_fails(self, client: TestClient):
        """T-EVL-03 (FR-EVL-4): Approve with overall score below 60 -> 409 Conflict."""
        _pid, app_id, nova_h, student_h = _setup_in_progress_application(client)

        sub = client.post(f"/api/v1/applications/{app_id}/submissions", json={
            "repo_url": "https://github.com/student/project-test",
        }, headers=student_h)
        sub_id = sub.json()["id"]

        eval_res = client.post(f"/api/v1/submissions/{sub_id}/evaluation", json={
            "overall_score": 55,
            "feedback": "Tried hard but not enough milestones met.",
            "decision": "approved",
        }, headers=nova_h)
        assert eval_res.status_code == 409  # Conflict: score < 60 cannot be approved

    def test_t_evl_04_reviewer_from_another_company_evaluates(self, client: TestClient):
        """T-EVL-04 (FR-EVL-4): Reviewer from another company evaluates -> 404."""
        _pid, app_id, _nova_h, student_h = _setup_in_progress_application(client)
        keystone_h = _keystone_headers(client)

        sub = client.post(f"/api/v1/applications/{app_id}/submissions", json={
            "repo_url": "https://github.com/student/project-test",
        }, headers=student_h)
        sub_id = sub.json()["id"]

        # Keystone Soft attempts to evaluate Nova Labs' project submission
        eval_res = client.post(f"/api/v1/submissions/{sub_id}/evaluation", json={
            "overall_score": 85,
            "feedback": "Trying to evaluate competitor project.",
            "decision": "approved",
        }, headers=keystone_h)
        assert eval_res.status_code == 404  # AGENTS.md rule 6: Another user's record returns 404

    def test_t_evl_05_changes_requested_and_resubmission(self, client: TestClient):
        """T-EVL-05 (FR-EVL-6): Changes requested, student resubmits -> back to submitted."""
        _pid, app_id, nova_h, student_h = _setup_in_progress_application(client)

        sub1 = client.post(f"/api/v1/applications/{app_id}/submissions", json={
            "repo_url": "https://github.com/student/v1",
        }, headers=student_h)
        sub1_id = sub1.json()["id"]

        eval_res = client.post(f"/api/v1/submissions/{sub1_id}/evaluation", json={
            "overall_score": 50,
            "feedback": "Please add unit tests and error handling.",
            "decision": "changes_requested",
        }, headers=nova_h)
        assert eval_res.status_code == 201
        assert eval_res.json()["application_status"] == "changes_requested"

        # Check application status is changes_requested
        ws_res = client.get(f"/api/v1/applications/{app_id}/workspace", headers=student_h)
        assert ws_res.json()["status"] == "changes_requested"

        # Student resubmits
        sub2 = client.post(f"/api/v1/applications/{app_id}/submissions", json={
            "repo_url": "https://github.com/student/v2-with-tests",
            "notes": "Added 100% test coverage.",
        }, headers=student_h)
        assert sub2.status_code == 201

        # Application is back to submitted
        ws_res2 = client.get(f"/api/v1/applications/{app_id}/workspace", headers=student_h)
        assert ws_res2.json()["status"] == "submitted"

    def test_t_evl_06_resubmission_after_window_fails(self, client: TestClient):
        """T-EVL-06 (FR-EVL-6): Resubmission after the window -> Application failed by scheduler."""
        _pid, app_id, nova_h, student_h = _setup_in_progress_application(client)
        admin_h = _admin_headers(client)

        sub = client.post(f"/api/v1/applications/{app_id}/submissions", json={
            "repo_url": "https://github.com/student/v1",
        }, headers=student_h)
        sub_id = sub.json()["id"]

        client.post(f"/api/v1/submissions/{sub_id}/evaluation", json={
            "overall_score": 50,
            "feedback": "Changes needed.",
            "decision": "changes_requested",
        }, headers=nova_h)

        # Artificially shift due_at to 10 days in the past (past due_at + 3 days)
        db = next(get_db())
        db.execute(
            text("UPDATE applications SET due_at = now() - interval '10 days' WHERE id = :id"),
            {"id": app_id},
        )
        db.commit()

        # Run check-late-resubmissions job
        job_res = client.post("/api/v1/admin/jobs/check-late-resubmissions", headers=admin_h)
        assert job_res.status_code == 200
        assert job_res.json()["failed"] >= 1

        # Application is now failed
        ws_res = client.get(f"/api/v1/applications/{app_id}/workspace", headers=student_h)
        assert ws_res.json()["status"] == "failed"

    def test_t_evl_07_and_08_appeals(self, client: TestClient):
        """T-EVL-07 & T-EVL-08 (BR-7, FR-EVL-7): Appeal within 7 days, second open appeal rejected."""
        _pid, app_id, nova_h, student_h = _setup_in_progress_application(client)

        sub = client.post(f"/api/v1/applications/{app_id}/submissions", json={
            "repo_url": "https://github.com/student/v1",
        }, headers=student_h)
        sub_id = sub.json()["id"]

        eval_res = client.post(f"/api/v1/submissions/{sub_id}/evaluation", json={
            "overall_score": 40,
            "feedback": "Unacceptable quality.",
            "decision": "rejected",
        }, headers=nova_h)
        eval_id = eval_res.json()["evaluation_id"]

        # Valid appeal within 7 days (day 0)
        app_res1 = client.post(f"/api/v1/evaluations/{eval_id}/appeal", json={
            "reason": "I believe the reviewer misunderstood the architecture pattern used.",
        }, headers=student_h)
        assert app_res1.status_code == 201
        assert app_res1.json()["status"] == "open"

        # T-EVL-08: Second open appeal on the same evaluation -> 409
        app_res2 = client.post(f"/api/v1/evaluations/{eval_id}/appeal", json={
            "reason": "Another appeal while the first is still open.",
        }, headers=student_h)
        assert app_res2.status_code == 409

        # T-EVL-07 (day 8 test): Artificially shift evaluated_at to 10 days ago and close open appeal
        db = next(get_db())
        db.execute(text("UPDATE appeals SET status = 'withdrawn' WHERE evaluation_id = :id"), {"id": eval_id})
        db.execute(text("UPDATE evaluations SET evaluated_at = now() - interval '10 days' WHERE id = :id"), {"id": eval_id})
        db.commit()

        # Appeal on day 10 (> 7 days) -> 400
        expired_res = client.post(f"/api/v1/evaluations/{eval_id}/appeal", json={
            "reason": "Appealing after the 7 days window has elapsed.",
        }, headers=student_h)
        assert expired_res.status_code == 400

    def test_t_crt_01_and_02_approve_evaluation_certificate_transaction(self, client: TestClient):
        """T-CRT-01 & T-CRT-02 (FR-CRT-1): Single atomic certificate transaction & double-click protection."""
        _pid, app_id, nova_h, student_h = _setup_in_progress_application(client)

        sub = client.post(f"/api/v1/applications/{app_id}/submissions", json={
            "repo_url": "https://github.com/student/perfect-work",
            "notes": "All milestones met.",
        }, headers=student_h)
        sub_id = sub.json()["id"]

        # Approve evaluation with score 85
        eval_res = client.post(f"/api/v1/submissions/{sub_id}/evaluation", json={
            "rubric_scores": {"functionality": 90, "code_quality": 85, "documentation": 80},
            "overall_score": 85,
            "feedback": "Exceptional delivery, clean code and tests.",
            "public_summary": "All 2 milestones met with high code quality.",
            "decision": "approved",
        }, headers=nova_h)
        assert eval_res.status_code == 201
        data = eval_res.json()
        assert data["application_status"] == "completed"
        assert data["certificate"] is not None

        cert = data["certificate"]
        assert cert["status"] == "issued"
        assert cert["verification_id"].startswith("EXP-2026-")
        assert cert["xp_awarded"] > 0

        # Verify DB records created in the transaction (T-CRT-01)
        db = next(get_db())
        xp_row = db.execute(
            text("SELECT amount, reason FROM xp_events WHERE student_id = (SELECT student_id FROM applications WHERE id = :id)"),
            {"id": app_id},
        ).fetchone()
        assert xp_row is not None
        assert xp_row[0] == cert["xp_awarded"]

        audit_row = db.execute(
            text("SELECT action, entity_type FROM audit_log WHERE entity_type = 'certificate' AND entity_id = :cid"),
            {"cid": str(cert["id"])},
        ).fetchone()
        assert audit_row is not None
        assert audit_row[0] == "issue_certificate"

        # T-CRT-02: Double click / retry approve on the application -> returns single certificate
        sub2_call = client.post(f"/api/v1/submissions/{sub_id}/evaluation", json={
            "overall_score": 85,
            "feedback": "Exceptional delivery retry.",
            "decision": "approved",
        }, headers=nova_h)
        # Should be rejected with 409 because already evaluated
        assert sub2_call.status_code == 409
