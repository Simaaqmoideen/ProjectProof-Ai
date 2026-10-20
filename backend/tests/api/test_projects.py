"""Tests for projects API — T-PRJ-01, T-PRJ-02, T-PRJ-03.
Uses a real PostgreSQL test database (AGENTS.md: no mocks for DB).
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


def _student_headers(client: TestClient) -> dict:
    return _login(client, "ananya@example.com", "StudentPass2026!")


def _admin_headers(client: TestClient) -> dict:
    return _login(client, "admin@projectproof.ai", "AdminSecure2026!")


def _create_open_project(
    client: TestClient,
    headers: dict,
    title: str | None = None,
    difficulty: str = "beginner",
    duration_days: int = 14,
) -> str:
    title = title or f"Test Project {uuid.uuid4().hex[:6]}"
    draft_res = client.post("/api/v1/companies/me/projects", json={
        "title": title,
        "description": "A detailed test project description for Phase 2.",
        "difficulty": difficulty,
        "duration_days": duration_days,
        "category": "development",
    }, headers=headers)
    assert draft_res.status_code == 201, f"Failed to create draft: {draft_res.text}"
    project_id = draft_res.json()["id"]

    pub_res = client.post(f"/api/v1/projects/{project_id}/publish", headers=headers)
    assert pub_res.status_code == 200, f"Failed to publish: {pub_res.text}"
    return project_id


# ── T-PRJ-01: xp_max is server-computed; client cannot supply it ─────────────

class TestTPrj01:
    def test_client_supplied_xp_max_is_rejected(self, client: TestClient):
        """T-PRJ-01 (FR-PRJ-3, BR-1): Request with xp_max is rejected 400."""
        headers = _nova_headers(client)
        res = client.post("/api/v1/companies/me/projects", json={
            "title": "XP Injection Attempt",
            "description": "Attempt to set xp_max directly.",
            "difficulty": "advanced",
            "duration_days": 30,
            "xp_max": 9999,
        }, headers=headers)
        assert res.status_code == 400
        body = res.json()["error"]
        assert body["code"] in ("validation_error",)
        assert "xp_max" in body["message"].lower() or any(
            d.get("field") == "xp_max" for d in body.get("details", [])
        )

    def test_server_computes_xp_max(self, client: TestClient):
        """T-PRJ-01 (BR-1): xp_max returned by server matches formula."""
        from app.config import settings
        headers = _nova_headers(client)
        res = client.post("/api/v1/companies/me/projects", json={
            "title": "XP Formula Test Project",
            "description": "Checking server-side xp_max computation via formula.",
            "difficulty": "intermediate",
            "duration_days": 20,
        }, headers=headers)
        assert res.status_code == 201
        expected = round(min(
            settings.xp_cap,
            settings.xp_base_per_day * 20 * settings.difficulty_multiplier["intermediate"] * 1.2
        ))
        assert res.json()["xp_max"] == expected

    def test_student_cannot_create_project(self, client: TestClient):
        """T-PRJ-01: Student cannot create a project → 403."""
        headers = _student_headers(client)
        res = client.post("/api/v1/companies/me/projects", json={
            "title": "Student Hack",
            "description": "Student should not be able to do this.",
            "difficulty": "beginner",
            "duration_days": 7,
        }, headers=headers)
        assert res.status_code == 403

    def test_unauthenticated_cannot_create_project(self, client: TestClient):
        """T-PRJ-01: Unauthenticated request → 401/403."""
        res = client.post("/api/v1/companies/me/projects", json={
            "title": "No Auth",
            "description": "This should fail without auth.",
            "difficulty": "beginner",
            "duration_days": 7,
        })
        assert res.status_code in (401, 403)


# ── T-PRJ-02: Browse and filter open projects ─────────────────────────────────

class TestTPrj02:
    def test_browse_open_projects_returns_list(self, client: TestClient):
        """T-PRJ-02 (FR-PRJ-6): GET /projects returns paginated list."""
        # Ensure at least one project is open
        nova_h = _nova_headers(client)
        _create_open_project(client, nova_h, title="Browse Test Project")

        res = client.get("/api/v1/projects")
        assert res.status_code == 200
        body = res.json()
        assert "items" in body
        assert "total" in body
        assert isinstance(body["items"], list)
        assert body["total"] >= 1

    def test_browse_filter_by_category(self, client: TestClient):
        """T-PRJ-02 (FR-PRJ-6): Category filter returns matching projects only."""
        nova_h = _nova_headers(client)
        title = f"Design Project {uuid.uuid4().hex[:6]}"
        draft_res = client.post("/api/v1/companies/me/projects", json={
            "title": title,
            "description": "A design project for category filter testing.",
            "difficulty": "beginner",
            "duration_days": 7,
            "category": "design",
        }, headers=nova_h)
        assert draft_res.status_code == 201
        pid = draft_res.json()["id"]
        client.post(f"/api/v1/projects/{pid}/publish", headers=nova_h)

        res = client.get("/api/v1/projects?category=design")
        assert res.status_code == 200
        for item in res.json()["items"]:
            assert item["category"] == "design"

    def test_browse_search_by_title(self, client: TestClient):
        """T-PRJ-02 (FR-PRJ-6): Search query finds matching project title."""
        nova_h = _nova_headers(client)
        unique_token = uuid.uuid4().hex[:10]
        title = f"Unique{unique_token}Project"
        draft_res = client.post("/api/v1/companies/me/projects", json={
            "title": title,
            "description": "Searchable project for testing the search endpoint.",
            "difficulty": "beginner",
            "duration_days": 5,
        }, headers=nova_h)
        assert draft_res.status_code == 201
        pid = draft_res.json()["id"]
        client.post(f"/api/v1/projects/{pid}/publish", headers=nova_h)

        res = client.get(f"/api/v1/projects?search={unique_token}")
        assert res.status_code == 200
        assert any(unique_token in item["title"] for item in res.json()["items"])

    def test_browse_student_sees_match_score(self, client: TestClient):
        """T-PRJ-02 / FR-APP-3: Student browsing sees match info attached."""
        nova_h = _nova_headers(client)
        _create_open_project(client, nova_h, title="Match Score Visibility Test")

        student_h = _student_headers(client)
        res = client.get("/api/v1/projects", headers=student_h)
        assert res.status_code == 200
        # At least one item should have 'match' key (may be None if no student profile)
        items = res.json()["items"]
        assert len(items) > 0
        # match key should be present (value can be None or a dict)
        assert "match" in items[0]

    def test_closed_draft_projects_not_in_browse(self, client: TestClient):
        """T-PRJ-02 (FR-PRJ-6): Closed/draft projects are NOT in browse list."""
        nova_h = _nova_headers(client)
        draft_res = client.post("/api/v1/companies/me/projects", json={
            "title": "Hidden Draft Project",
            "description": "This draft should not appear in browse.",
            "difficulty": "beginner",
            "duration_days": 5,
        }, headers=nova_h)
        assert draft_res.status_code == 201
        pid = draft_res.json()["id"]
        # Don't publish — stays draft

        res = client.get("/api/v1/projects")
        assert res.status_code == 200
        ids = [item["id"] for item in res.json()["items"]]
        assert pid not in ids


# ── T-PRJ-03: Project status transitions ─────────────────────────────────────

class TestTPrj03:
    def test_publish_then_close_project(self, client: TestClient):
        """T-PRJ-03 (FR-PRJ-3, FR-PRJ-4): Draft → Open → Closed."""
        headers = _nova_headers(client)
        draft_res = client.post("/api/v1/companies/me/projects", json={
            "title": "Status Transition Test Project",
            "description": "Testing draft to open to closed transition.",
            "difficulty": "beginner",
            "duration_days": 10,
        }, headers=headers)
        assert draft_res.status_code == 201
        pid = draft_res.json()["id"]
        assert draft_res.json()["status"] == "draft"

        # Publish
        pub_res = client.post(f"/api/v1/projects/{pid}/publish", headers=headers)
        assert pub_res.status_code == 200
        assert pub_res.json()["status"] == "open"

        # Close
        close_res = client.post(f"/api/v1/projects/{pid}/close", headers=headers)
        assert close_res.status_code == 200
        assert close_res.json()["status"] == "closed"

    def test_cannot_close_draft(self, client: TestClient):
        """T-PRJ-03 (FR-PRJ-4): Cannot close a draft project."""
        headers = _nova_headers(client)
        draft_res = client.post("/api/v1/companies/me/projects", json={
            "title": "Cannot Close Draft",
            "description": "This should fail to close because it is a draft.",
            "difficulty": "beginner",
            "duration_days": 7,
        }, headers=headers)
        assert draft_res.status_code == 201
        pid = draft_res.json()["id"]

        close_res = client.post(f"/api/v1/projects/{pid}/close", headers=headers)
        assert close_res.status_code == 400

    def test_cancel_open_project(self, client: TestClient):
        """T-PRJ-03 (FR-PRJ-5): Open project can be cancelled."""
        headers = _nova_headers(client)
        pid = _create_open_project(client, headers, title="Cancel Open Project")

        cancel_res = client.post(f"/api/v1/projects/{pid}/cancel", headers=headers)
        assert cancel_res.status_code == 200
        assert cancel_res.json()["status"] == "cancelled"

    def test_cancel_draft_project(self, client: TestClient):
        """T-PRJ-03 (FR-PRJ-5): Draft project can be cancelled."""
        headers = _keystone_headers(client)
        draft_res = client.post("/api/v1/companies/me/projects", json={
            "title": "Cancel Draft Project",
            "description": "Test that a draft project can be cancelled.",
            "difficulty": "beginner",
            "duration_days": 5,
        }, headers=headers)
        assert draft_res.status_code == 201
        pid = draft_res.json()["id"]

        cancel_res = client.post(f"/api/v1/projects/{pid}/cancel", headers=headers)
        assert cancel_res.status_code == 200
        assert cancel_res.json()["status"] == "cancelled"

    def test_other_company_cannot_close_project(self, client: TestClient):
        """T-PRJ-03 (FR-PRJ-4, AGENTS.md rule 6): Company B cannot close Company A's project."""
        nova_h = _nova_headers(client)
        keystone_h = _keystone_headers(client)
        pid = _create_open_project(client, nova_h, title="Nova Only Project")

        close_res = client.post(f"/api/v1/projects/{pid}/close", headers=keystone_h)
        assert close_res.status_code == 404  # Ownership check → 404 per rule 6

    def test_update_draft_project(self, client: TestClient):
        """T-PRJ-03 (FR-PRJ-2): Company can update title/description of a draft."""
        headers = _nova_headers(client)
        draft_res = client.post("/api/v1/companies/me/projects", json={
            "title": "Original Title",
            "description": "Original description for updating.",
            "difficulty": "beginner",
            "duration_days": 10,
        }, headers=headers)
        assert draft_res.status_code == 201
        pid = draft_res.json()["id"]

        update_res = client.put(f"/api/v1/projects/{pid}", json={
            "title": "Updated Title",
            "description": "Updated description after creation.",
        }, headers=headers)
        assert update_res.status_code == 200
        assert update_res.json()["title"] == "Updated Title"

    def test_cannot_update_published_project(self, client: TestClient):
        """T-PRJ-03 (FR-PRJ-2): Cannot edit an already-open project."""
        headers = _nova_headers(client)
        pid = _create_open_project(client, headers, title="Published No Edit")

        update_res = client.put(f"/api/v1/projects/{pid}", json={
            "title": "Edit After Publish",
        }, headers=headers)
        assert update_res.status_code == 400

    def test_pending_company_cannot_publish(self, client: TestClient):
        """T-ORG-01 (FR-ORG-2): Pending company trying to publish → 403."""
        brightwave_h = _login(client, "brightwave.tech@gmail.com", "BrightWave2026!")

        draft_res = client.post("/api/v1/companies/me/projects", json={
            "title": "BrightWave Draft",
            "description": "A pending company's draft project.",
            "difficulty": "beginner",
            "duration_days": 7,
        }, headers=brightwave_h)
        assert draft_res.status_code in (201, 403)  # Pending company may not even create
        if draft_res.status_code == 201:
            pid = draft_res.json()["id"]
            pub_res = client.post(f"/api/v1/projects/{pid}/publish", headers=brightwave_h)
            assert pub_res.status_code == 403
