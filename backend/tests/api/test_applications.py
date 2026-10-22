"""Tests for applications API — T-APP-01 through T-APP-06.
Uses real PostgreSQL (AGENTS.md: no mocks for DB).
Seed accounts from backend/scripts/seed.py.
"""

import uuid

from fastapi.testclient import TestClient

# ── Auth helpers ────────────────────────────────────────────────────────────


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


def _create_and_publish_project(
    client: TestClient,
    company_headers: dict,
    title: str | None = None,
    max_selected: int = 1,
) -> str:
    """Create and publish a project; return project_id."""
    title = title or f"App Test Project {uuid.uuid4().hex[:6]}"
    draft_res = client.post(
        "/api/v1/companies/me/projects",
        json={
            "title": title,
            "description": "A project for application testing with sufficient description.",
            "difficulty": "beginner",
            "duration_days": 14,
            "max_selected": max_selected,
        },
        headers=company_headers,
    )
    assert draft_res.status_code == 201, f"Create failed: {draft_res.text}"
    pid = draft_res.json()["id"]

    pub_res = client.post(f"/api/v1/projects/{pid}/publish", headers=company_headers)
    assert pub_res.status_code == 200, f"Publish failed: {pub_res.text}"
    return pid


def _apply(client: TestClient, student_headers: dict, project_id: str) -> dict:
    """Student applies; returns application JSON."""
    res = client.post(
        f"/api/v1/projects/{project_id}/applications",
        json={
            "cover_note": "Excited to work on this project!",
        },
        headers=student_headers,
    )
    assert res.status_code == 201, f"Apply failed: {res.text}"
    return res.json()


# ── T-APP-01: Student applies to an open project ─────────────────────────────


class TestTApp01:
    def test_student_can_apply(self, client: TestClient):
        """T-APP-01 (FR-APP-1): Student applies → 201 with match_score."""
        nova_h = _nova_headers(client)
        pid = _create_and_publish_project(client, nova_h, title="Apply Test Project")

        student_h = _student_headers(client)
        res = client.post(
            f"/api/v1/projects/{pid}/applications",
            json={
                "cover_note": "I am very interested in this project.",
            },
            headers=student_h,
        )
        assert res.status_code == 201
        body = res.json()
        assert body["project_id"] == pid
        assert body["status"] == "applied"
        assert "match_score" in body  # BR-3 stored on apply

    def test_cannot_apply_twice(self, client: TestClient):
        """T-APP-01 (FR-APP-1): Duplicate application → 409."""
        nova_h = _nova_headers(client)
        pid = _create_and_publish_project(client, nova_h, title="Duplicate Apply Test")

        # Create a fresh student for isolation
        suffix = uuid.uuid4().hex[:8]
        email = f"student_{suffix}@example.com"
        client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "StudentPass2026!",
                "role": "student",
                "full_name": f"Test Student {suffix}",
            },
        )
        login_res = client.post(
            "/api/v1/auth/login", json={"email": email, "password": "StudentPass2026!"}
        )
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        from app.core.security import create_email_verification_token

        user_id = login_res.json()["user"]["id"]
        vtoken = create_email_verification_token(user_id, email)
        client.post("/api/v1/auth/verify-email", json={"token": vtoken})

        client.post(
            f"/api/v1/projects/{pid}/applications", json={"cover_note": "First"}, headers=headers
        )
        res2 = client.post(
            f"/api/v1/projects/{pid}/applications", json={"cover_note": "Second"}, headers=headers
        )
        assert res2.status_code == 409

    def test_cannot_apply_to_closed_project(self, client: TestClient):
        """T-APP-01 (FR-APP-1): Apply to closed project → 404."""
        nova_h = _nova_headers(client)
        pid = _create_and_publish_project(client, nova_h, title="Closed Apply Test")
        client.post(f"/api/v1/projects/{pid}/close", headers=nova_h)

        student_h = _student_headers(client)
        res = client.post(f"/api/v1/projects/{pid}/applications", json={}, headers=student_h)
        assert res.status_code == 404

    def test_company_cannot_apply(self, client: TestClient):
        """T-APP-01 (FR-APP-1): Company account cannot apply → 403."""
        nova_h = _nova_headers(client)
        keystone_h = _keystone_headers(client)
        pid = _create_and_publish_project(client, nova_h, title="Company Cannot Apply")

        res = client.post(f"/api/v1/projects/{pid}/applications", json={}, headers=keystone_h)
        assert res.status_code == 403


# ── T-APP-02: Student withdraws an application ────────────────────────────────


class TestTApp02:
    def test_student_can_withdraw(self, client: TestClient):
        """T-APP-02 (FR-APP-2): Student withdraws own 'applied' application → 200."""
        nova_h = _nova_headers(client)
        pid = _create_and_publish_project(client, nova_h, title="Withdraw Test Project")

        # Register isolated student
        suffix = uuid.uuid4().hex[:8]
        email = f"withdraw_{suffix}@example.com"
        client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "StudentPass2026!",
                "role": "student",
                "full_name": f"Withdraw Student {suffix}",
            },
        )
        login_res = client.post(
            "/api/v1/auth/login", json={"email": email, "password": "StudentPass2026!"}
        )
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        from app.core.security import create_email_verification_token

        user_id = login_res.json()["user"]["id"]
        vtoken = create_email_verification_token(user_id, email)
        client.post("/api/v1/auth/verify-email", json={"token": vtoken})

        app_res = client.post(f"/api/v1/projects/{pid}/applications", json={}, headers=headers)
        assert app_res.status_code == 201
        app_id = app_res.json()["id"]

        withdraw_res = client.post(f"/api/v1/applications/{app_id}/withdraw", headers=headers)
        assert withdraw_res.status_code == 200
        assert withdraw_res.json()["status"] == "withdrawn"

    def test_cannot_withdraw_others_application(self, client: TestClient):
        """T-APP-02 (FR-APP-2): Cannot withdraw another student's application → 404."""
        nova_h = _nova_headers(client)
        pid = _create_and_publish_project(client, nova_h, title="Other Student Withdraw Test")

        # Register two students
        suffix1 = uuid.uuid4().hex[:8]
        suffix2 = uuid.uuid4().hex[:8]
        for suffix in [suffix1, suffix2]:
            email = f"stu_{suffix}@example.com"
            client.post(
                "/api/v1/auth/register",
                json={
                    "email": email,
                    "password": "StudentPass2026!",
                    "role": "student",
                    "full_name": f"Student {suffix}",
                },
            )
            login_res = client.post(
                "/api/v1/auth/login", json={"email": email, "password": "StudentPass2026!"}
            )
            token = login_res.json()["access_token"]
            h = {"Authorization": f"Bearer {token}"}
            from app.core.security import create_email_verification_token

            uid = login_res.json()["user"]["id"]
            vtoken = create_email_verification_token(uid, email)
            client.post("/api/v1/auth/verify-email", json={"token": vtoken})
            if suffix == suffix1:
                app_res = client.post(f"/api/v1/projects/{pid}/applications", json={}, headers=h)
                assert app_res.status_code == 201
                app_id = app_res.json()["id"]
            else:
                student2_h = h

        withdraw_res = client.post(f"/api/v1/applications/{app_id}/withdraw", headers=student2_h)
        assert withdraw_res.status_code == 404


# ── T-APP-03: Company views applications ────────────────────────────────────


class TestTApp03:
    def test_company_can_list_applications(self, client: TestClient):
        """T-APP-03 (FR-APP-4): Company lists applicants for their project."""
        nova_h = _nova_headers(client)
        pid = _create_and_publish_project(client, nova_h, title="Company View Apps Test")

        student_h = _student_headers(client, "rohit@example.com")
        client.post(f"/api/v1/projects/{pid}/applications", json={}, headers=student_h)

        res = client.get(f"/api/v1/projects/{pid}/applications", headers=nova_h)
        assert res.status_code == 200
        body = res.json()
        assert "items" in body
        assert "total" in body
        assert body["total"] >= 1

    def test_company_cannot_view_others_applications(self, client: TestClient):
        """T-APP-03 (FR-APP-4, rule 6): Company B cannot list Company A's project applications."""
        nova_h = _nova_headers(client)
        keystone_h = _keystone_headers(client)
        pid = _create_and_publish_project(client, nova_h, title="Nova Private Project")

        res = client.get(f"/api/v1/projects/{pid}/applications", headers=keystone_h)
        assert res.status_code == 404

    def test_student_cannot_list_project_applications(self, client: TestClient):
        """T-APP-03 (FR-APP-4): Student cannot access company's applicant list."""
        nova_h = _nova_headers(client)
        pid = _create_and_publish_project(client, nova_h, title="Student Cannot View")

        student_h = _student_headers(client)
        res = client.get(f"/api/v1/projects/{pid}/applications", headers=student_h)
        assert res.status_code == 403


# ── T-APP-04: Select applicant ───────────────────────────────────────────────


class TestTApp04:
    def test_company_can_select_applicant(self, client: TestClient):
        """T-APP-04 (FR-APP-5): Company selects applicant → status 'in_progress', due_at set."""
        nova_h = _nova_headers(client)
        pid = _create_and_publish_project(client, nova_h, title="Select Applicant Test")

        student_h = _student_headers(client, "priya@example.com")
        app_res = client.post(f"/api/v1/projects/{pid}/applications", json={}, headers=student_h)
        assert app_res.status_code == 201
        app_id = app_res.json()["id"]

        select_res = client.post(f"/api/v1/applications/{app_id}/select", headers=nova_h)
        assert select_res.status_code == 200
        body = select_res.json()
        assert body["status"] == "in_progress"
        assert body["started_at"] is not None
        assert body["due_at"] is not None

    def test_max_selected_limit_enforced(self, client: TestClient):
        """T-APP-04 (FR-APP-5): Cannot select more than max_selected applicants."""
        nova_h = _nova_headers(client)
        # max_selected = 1
        pid = _create_and_publish_project(
            client, nova_h, title="Max Selected Limit Test", max_selected=1
        )

        # Two fresh students apply
        app_ids = []
        for i in range(2):
            suffix = uuid.uuid4().hex[:8]
            email = f"maxsel_{suffix}@example.com"
            client.post(
                "/api/v1/auth/register",
                json={
                    "email": email,
                    "password": "StudentPass2026!",
                    "role": "student",
                    "full_name": f"MaxSel Student {i}",
                },
            )
            login_res = client.post(
                "/api/v1/auth/login", json={"email": email, "password": "StudentPass2026!"}
            )
            token = login_res.json()["access_token"]
            h = {"Authorization": f"Bearer {token}"}
            from app.core.security import create_email_verification_token

            uid = login_res.json()["user"]["id"]
            vtoken = create_email_verification_token(uid, email)
            client.post("/api/v1/auth/verify-email", json={"token": vtoken})
            app_res = client.post(f"/api/v1/projects/{pid}/applications", json={}, headers=h)
            assert app_res.status_code == 201
            app_ids.append(app_res.json()["id"])

        # Select first → success
        sel1 = client.post(f"/api/v1/applications/{app_ids[0]}/select", headers=nova_h)
        assert sel1.status_code == 200

        # Select second → 403 (max reached)
        sel2 = client.post(f"/api/v1/applications/{app_ids[1]}/select", headers=nova_h)
        assert sel2.status_code == 403

    def test_cannot_select_from_other_company_project(self, client: TestClient):
        """T-APP-04 (rule 6): Company B cannot select applicant from Company A's project."""
        nova_h = _nova_headers(client)
        keystone_h = _keystone_headers(client)
        pid = _create_and_publish_project(client, nova_h, title="Nova Select Only")

        student_h = _student_headers(client)
        app_res = client.post(f"/api/v1/projects/{pid}/applications", json={}, headers=student_h)
        assert app_res.status_code == 201
        app_id = app_res.json()["id"]

        select_res = client.post(f"/api/v1/applications/{app_id}/select", headers=keystone_h)
        assert select_res.status_code == 404


# ── T-APP-05: Reject applicant ───────────────────────────────────────────────


class TestTApp05:
    def test_company_can_reject_applicant(self, client: TestClient):
        """T-APP-05 (FR-APP-6): Company rejects applicant → status 'rejected'."""
        nova_h = _nova_headers(client)
        pid = _create_and_publish_project(client, nova_h, title="Reject Test Project")

        suffix = uuid.uuid4().hex[:8]
        email = f"reject_{suffix}@example.com"
        client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "StudentPass2026!",
                "role": "student",
                "full_name": f"Reject Student {suffix}",
            },
        )
        login_res = client.post(
            "/api/v1/auth/login", json={"email": email, "password": "StudentPass2026!"}
        )
        token = login_res.json()["access_token"]
        student_h = {"Authorization": f"Bearer {token}"}
        from app.core.security import create_email_verification_token

        uid = login_res.json()["user"]["id"]
        vtoken = create_email_verification_token(uid, email)
        client.post("/api/v1/auth/verify-email", json={"token": vtoken})

        app_res = client.post(f"/api/v1/projects/{pid}/applications", json={}, headers=student_h)
        assert app_res.status_code == 201
        app_id = app_res.json()["id"]

        reject_res = client.post(
            f"/api/v1/applications/{app_id}/reject",
            json={"reason": "Not a good fit."},
            headers=nova_h,
        )
        assert reject_res.status_code == 200
        assert reject_res.json()["status"] == "rejected"

    def test_cannot_reject_already_selected(self, client: TestClient):
        """T-APP-05 (FR-APP-6): Cannot reject an in_progress application."""
        nova_h = _nova_headers(client)
        pid = _create_and_publish_project(client, nova_h, title="No Reject In Progress")

        suffix = uuid.uuid4().hex[:8]
        email = f"noreject_{suffix}@example.com"
        client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "StudentPass2026!",
                "role": "student",
                "full_name": f"NoReject Student {suffix}",
            },
        )
        login_res = client.post(
            "/api/v1/auth/login", json={"email": email, "password": "StudentPass2026!"}
        )
        token = login_res.json()["access_token"]
        student_h = {"Authorization": f"Bearer {token}"}
        from app.core.security import create_email_verification_token

        uid = login_res.json()["user"]["id"]
        vtoken = create_email_verification_token(uid, email)
        client.post("/api/v1/auth/verify-email", json={"token": vtoken})

        app_res = client.post(f"/api/v1/projects/{pid}/applications", json={}, headers=student_h)
        assert app_res.status_code == 201
        app_id = app_res.json()["id"]

        # Select first
        client.post(f"/api/v1/applications/{app_id}/select", headers=nova_h)

        # Try to reject now
        reject_res = client.post(
            f"/api/v1/applications/{app_id}/reject",
            json={"reason": "After select reject"},
            headers=nova_h,
        )
        assert reject_res.status_code == 400


# ── T-APP-06: Compare applicants ─────────────────────────────────────────────


class TestTApp06:
    def test_company_can_compare_applicants(self, client: TestClient):
        """T-APP-06 (FR-APP-7): Compare endpoint returns sorted applicants with match scores."""
        nova_h = _nova_headers(client)
        pid = _create_and_publish_project(
            client, nova_h, title="Compare Applicants Test", max_selected=5
        )

        # Have 2 students apply
        for email in ["ananya@example.com", "rohit@example.com"]:
            student_h = _student_headers(client, email)
            res = client.post(f"/api/v1/projects/{pid}/applications", json={}, headers=student_h)
            # 409 is ok if already applied from another test run
            assert res.status_code in (201, 409)

        res = client.get(f"/api/v1/projects/{pid}/applications/compare", headers=nova_h)
        assert res.status_code == 200
        body = res.json()
        assert body["project_id"] == pid
        assert "applicants" in body
        # Each item has match_score, match_breakdown, missing_skills
        for item in body["applicants"]:
            assert "match_score" in item
            assert "match_breakdown" in item
            assert "missing_skills" in item

    def test_compare_sorted_by_match_score(self, client: TestClient):
        """T-APP-06 (FR-APP-7): Comparison result is sorted descending by match_score."""
        nova_h = _nova_headers(client)
        pid = _create_and_publish_project(client, nova_h, title="Compare Sort Test", max_selected=5)

        for email in ["priya@example.com", "rohit@example.com"]:
            student_h = _student_headers(client, email)
            client.post(f"/api/v1/projects/{pid}/applications", json={}, headers=student_h)

        res = client.get(f"/api/v1/projects/{pid}/applications/compare", headers=nova_h)
        assert res.status_code == 200
        scores = [item["match_score"] for item in res.json()["applicants"]]
        assert scores == sorted(scores, reverse=True)

    def test_student_cannot_access_compare(self, client: TestClient):
        """T-APP-06 (FR-APP-7): Student cannot access compare endpoint → 403."""
        nova_h = _nova_headers(client)
        pid = _create_and_publish_project(client, nova_h, title="Compare Access Control")

        student_h = _student_headers(client)
        res = client.get(f"/api/v1/projects/{pid}/applications/compare", headers=student_h)
        assert res.status_code == 403
