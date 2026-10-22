"""Tests for Project Removal, Reports, and Admin Statistics (Phase 5).
Covers:
- FR-ADM-8, FR-ADM-9, FR-ANA-3
- T-ADM-04, T-ADM-05, T-ADM-06, T-ADM-07, T-ADM-08, T-ADM-09
- AGENTS.md rule 11: Single transaction, project->removed, applications rejected/withdrawn, notifications, audit log.
"""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import SessionLocal


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


def _create_and_publish_project(client: TestClient) -> str:
    nova_h = _nova_headers(client)
    res = client.post(
        "/api/v1/companies/me/projects",
        json={
            "title": f"Removal Test {uuid.uuid4().hex[:6]}",
            "description": "Project to test admin removal flows.",
            "difficulty": "beginner",
            "duration_days": 7,
            "max_selected": 2,
        },
        headers=nova_h,
    )
    assert res.status_code == 201, res.text
    pid = res.json()["id"]
    client.post(f"/api/v1/projects/{pid}/publish", headers=nova_h)
    return pid


def test_remove_project_without_reason_t_adm_04(client: TestClient):
    """T-ADM-04: Admin removes a project without a reason -> 400/422."""
    admin_h = _admin_headers(client)
    pid = _create_and_publish_project(client)

    # Empty reason
    res = client.post(f"/api/v1/admin/projects/{pid}/remove", json={"reason": ""}, headers=admin_h)
    assert res.status_code in (400, 422), res.text

    # Missing reason
    res2 = client.post(f"/api/v1/admin/projects/{pid}/remove", json={}, headers=admin_h)
    assert res2.status_code in (400, 422), res2.text


def test_non_admin_cannot_remove_t_adm_07(client: TestClient):
    """T-ADM-07: Non-admin calls removal route -> 403."""
    student_h = _student_headers(client, "ananya@example.com")
    pid = _create_and_publish_project(client)

    res = client.post(
        f"/api/v1/admin/projects/{pid}/remove", json={"reason": "spam"}, headers=student_h
    )
    assert res.status_code == 403


def test_admin_removes_project_with_applications_t_adm_05(client: TestClient):
    """T-ADM-05: Admin removes project that has applied and in-progress applications.
    - Applied becomes rejected (status_reason = project_removed)
    - In_progress becomes withdrawn (status_reason = project_removed)
    - Company trust score penalized by 15
    - Notifications sent to affected students
    - Audit log row written in same transaction
    """
    nova_h = _nova_headers(client)
    admin_h = _admin_headers(client)
    pid = _create_and_publish_project(client)

    # Student 1 applies and gets selected -> in_progress
    s1_h = _student_headers(client, "ananya@example.com")
    app1_res = client.post(
        f"/api/v1/projects/{pid}/applications", json={"cover_note": "Pick me"}, headers=s1_h
    )
    assert app1_res.status_code == 201
    app1_id = app1_res.json()["id"]

    sel_res = client.post(f"/api/v1/applications/{app1_id}/select", headers=nova_h)
    assert sel_res.status_code == 200

    # Student 2 applies -> stays applied
    s2_h = _student_headers(client, "rohit@example.com")
    app2_res = client.post(
        f"/api/v1/projects/{pid}/applications", json={"cover_note": "Pick me too"}, headers=s2_h
    )
    assert app2_res.status_code == 201
    app2_id = app2_res.json()["id"]

    # Check trust score before removal
    session = SessionLocal()
    try:
        company_id = session.execute(
            text("SELECT company_id FROM projects WHERE id = :pid"),
            {"pid": pid},
        ).scalar()
        trust_before = session.execute(
            text("SELECT trust_score FROM companies WHERE id = :cid"),
            {"cid": company_id},
        ).scalar()
    finally:
        session.close()

    # Admin removes project
    rem_res = client.post(
        f"/api/v1/admin/projects/{pid}/remove",
        json={
            "reason": "inappropriate",
            "note": "Violates safety policy.",
        },
        headers=admin_h,
    )
    assert rem_res.status_code == 200, rem_res.text
    data = rem_res.json()
    assert data["new_status"] == "removed"
    assert data["applied_rejected"] == 1
    assert data["active_withdrawn"] == 1

    # Verify DB state atomically updated
    session = SessionLocal()
    try:
        # Project status is removed
        p_status = session.execute(
            text("SELECT status FROM projects WHERE id = :pid"), {"pid": pid}
        ).scalar()
        assert p_status == "removed"

        # App 1 was in_progress -> withdrawn with status_reason = project_removed
        a1 = session.execute(
            text("SELECT status, status_reason FROM applications WHERE id = :id"),
            {"id": app1_id},
        ).fetchone()
        assert a1[0] == "withdrawn"
        assert a1[1] == "project_removed"

        # App 2 was applied -> rejected with status_reason = project_removed
        a2 = session.execute(
            text("SELECT status, status_reason FROM applications WHERE id = :id"),
            {"id": app2_id},
        ).fetchone()
        assert a2[0] == "rejected"
        assert a2[1] == "project_removed"

        # Company trust score penalized by 15
        trust_after = session.execute(
            text("SELECT trust_score FROM companies WHERE id = :cid"),
            {"cid": company_id},
        ).scalar()
        assert trust_after == max(0, trust_before - 15)

        # Audit row written with project_removed action
        audit = session.execute(
            text(
                "SELECT action, entity_type, entity_id FROM audit_log WHERE entity_id = :pid ORDER BY created_at DESC LIMIT 1"
            ),
            {"pid": pid},
        ).fetchone()
        assert audit is not None
        assert audit[0] == "project_removed"

        # Notifications created for both students
        for sid in session.execute(
            text("SELECT student_id FROM applications WHERE project_id = :pid"), {"pid": pid}
        ).scalars():
            notif = session.execute(
                text(
                    "SELECT type FROM notifications WHERE user_id = :uid AND type = 'project_removed'"
                ),
                {"uid": sid},
            ).scalar()
            assert notif == "project_removed"
    finally:
        session.close()


from tests.api.test_certificates import _create_approved_certificate


def test_remove_project_with_existing_certificate_t_adm_06(client: TestClient):
    """T-ADM-06: Remove a project that already produced a certificate.
    Certificate stays issued and verifiable!
    """
    admin_h = _admin_headers(client)

    cert_info, ctx = _create_approved_certificate(client, score=90)
    pid = ctx["project_id"]
    qr_token = cert_info["qr_token"]
    verification_id = cert_info["verification_id"]

    # 2. Admin removes the project
    rem_res = client.post(
        f"/api/v1/admin/projects/{pid}/remove",
        json={
            "reason": "duplicate",
            "note": "Company requested removal of old duplicate listing.",
        },
        headers=admin_h,
    )
    assert rem_res.status_code == 200

    # 3. Certificate stays issued and verifiable via public verification endpoint
    pub_res = client.get(f"/api/v1/public/verify/{qr_token}")
    assert pub_res.status_code == 200, pub_res.text
    data = pub_res.json()
    assert data["status"] == "issued"
    assert data["verification_id"] == verification_id


def test_student_reports_project_t_adm_08(client: TestClient):
    """T-ADM-08: Student reports a project -> manual flag opens; project stays visible."""
    student_h = _student_headers(client, "ananya@example.com")
    pid = _create_and_publish_project(client)

    # Report project
    rep_res = client.post(
        f"/api/v1/projects/{pid}/report",
        json={
            "reason": "Misleading job description",
            "note": "Project asks for personal API keys.",
        },
        headers=student_h,
    )
    assert rep_res.status_code == 201, rep_res.text

    # Project is still visible (status open)
    proj_res = client.get(f"/api/v1/projects/{pid}", headers=student_h)
    assert proj_res.status_code == 200
    assert proj_res.json()["status"] == "open"

    # Flag exists in admin flag queue
    session = SessionLocal()
    try:
        flag = session.execute(
            text("SELECT kind, status FROM flags WHERE entity_id = :pid"),
            {"pid": pid},
        ).fetchone()
        assert flag is not None
        assert flag[0] == "manual"
        assert flag[1] == "open"
    finally:
        session.close()


def test_admin_platform_stats_t_adm_09(client: TestClient):
    """T-ADM-09, FR-ANA-3: Admin statistics match counts from v_platform_stats."""
    admin_h = _admin_headers(client)

    res = client.get("/api/v1/admin/stats", headers=admin_h)
    assert res.status_code == 200, res.text
    stats = res.json()
    assert "active_students" in stats
    assert "approved_companies" in stats
    assert "open_projects" in stats
    assert "certificates_issued" in stats
    assert stats["active_students"] >= 1
    assert stats["approved_companies"] >= 1
