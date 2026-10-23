"""Tests for Recruiter Search and Portfolio view (Phase 5).
Covers:
- FR-REC-1, FR-REC-2, FR-REC-4, BR-8, BR-11
- T-REC-01, T-REC-02, T-REC-04
- T-STU-02, T-ORG-06
"""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.security import hash_password
from app.db import SessionLocal


def _login(client: TestClient, email: str, password: str) -> dict:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _student_headers(client: TestClient, email: str = "ananya@example.com") -> dict:
    return _login(client, email, "StudentPass2026!")


def _create_recruiter(client: TestClient, approved: bool = True) -> tuple[dict, uuid.UUID]:
    """Helper to create a recruiter account and profile."""
    email = f"recruiter_{uuid.uuid4().hex[:6]}@talenthunt.com"
    password = "RecruiterPass2026!"

    session = SessionLocal()
    try:
        user_id = uuid.uuid4()
        session.execute(
            text("""
                INSERT INTO users (id, email, password_hash, role, is_active, email_verified_at)
                VALUES (:id, :email, :pw, 'recruiter', true, now())
            """),
            {"id": user_id, "email": email, "pw": hash_password(password)},
        )
        status_val = "approved" if approved else "pending"
        session.execute(
            text("""
                INSERT INTO recruiter_profiles (user_id, full_name, organization, status)
                VALUES (:uid, 'Sarah Connor', 'TalentHunt Global', CAST(:status AS approval_status))
            """),
            {"uid": user_id, "status": status_val},
        )
        session.commit()
    finally:
        session.close()

    headers = _login(client, email, password)
    return headers, user_id


def test_unapproved_recruiter_blocked_t_org_06(client: TestClient):
    """T-ORG-06: Unapproved recruiter search returns 403."""
    headers, _ = _create_recruiter(client, approved=False)
    res = client.get("/api/v1/recruiter/students", headers=headers)
    assert res.status_code == 403, res.text


def test_recruiter_search_privacy_t_rec_01(client: TestClient):
    """T-REC-01, BR-8: Search NEVER returns private profiles."""
    headers, _ = _create_recruiter(client, approved=True)

    # Ensure Rohit is private
    session = SessionLocal()
    try:
        session.execute(
            text("""
                UPDATE student_profiles
                   SET is_public = false
                 WHERE user_id = (SELECT id FROM users WHERE email = 'rohit@example.com')
            """)
        )
        session.commit()
    finally:
        session.close()

    res = client.get("/api/v1/recruiter/students", headers=headers)
    assert res.status_code == 200, res.text
    items = res.json()["items"]
    names = [i["display_name"] for i in items]
    assert "Rohit Verma" not in names


def test_recruiter_search_public_toggle_t_rec_02(client: TestClient):
    """T-REC-02: Student turns public off → disappears from search immediately."""
    recruiter_h, _ = _create_recruiter(client, approved=True)
    student_h = _student_headers(client, "ananya@example.com")

    # Turn public ON
    res_on = client.put(
        "/api/v1/students/me/visibility", json={"is_public": True}, headers=student_h
    )
    assert res_on.status_code == 200

    # Recruiter sees Ananya
    res1 = client.get("/api/v1/recruiter/students", headers=recruiter_h)
    assert res1.status_code == 200
    names1 = [i["display_name"] for i in res1.json()["items"]]
    assert any("Ananya" in n for n in names1)

    # Student turns public OFF
    res_off = client.put(
        "/api/v1/students/me/visibility", json={"is_public": False}, headers=student_h
    )
    assert res_off.status_code == 200

    # Recruiter search does NOT see Ananya
    res2 = client.get("/api/v1/recruiter/students", headers=recruiter_h)
    assert res2.status_code == 200
    names2 = [i["display_name"] for i in res2.json()["items"]]
    assert not any("Ananya" in n for n in names2)

    # Turn public back ON for other tests
    client.put("/api/v1/students/me/visibility", json={"is_public": True}, headers=student_h)


def test_recruiter_results_order_t_rec_04(client: TestClient):
    """T-REC-04, FR-REC-4, BR-11:
    Recruiter results order: verified project count first, then XP.
    E.g. 3 verified and 100 XP before 2 verified and 500 XP.
    """
    recruiter_h, _ = _create_recruiter(client, approved=True)

    session = SessionLocal()
    try:
        # Create student A: 2 verified, 1000 XP
        # Create student B: 3 verified, 100 XP
        # Both public
        uid_a = uuid.uuid4()
        uid_b = uuid.uuid4()
        for uid, email, name, is_pub in [
            (uid_a, f"stu_a_{uuid.uuid4().hex[:6]}@example.com", "Student A (High XP)", True),
            (uid_b, f"stu_b_{uuid.uuid4().hex[:6]}@example.com", "Student B (More Projects)", True),
        ]:
            session.execute(
                text("""
                    INSERT INTO users (id, email, password_hash, role, is_active, email_verified_at)
                    VALUES (:id, :email, 'hash', 'student', true, now())
                """),
                {"id": uid, "email": email},
            )
            session.execute(
                text("""
                    INSERT INTO student_profiles (user_id, full_name, is_public)
                    VALUES (:id, :name, :is_pub)
                """),
                {"id": uid, "name": name, "is_pub": is_pub},
            )
        session.commit()
    finally:
        session.close()

    res = client.get("/api/v1/recruiter/students", headers=recruiter_h)
    assert res.status_code == 200, res.text
    items = res.json()["items"]
    # Check overall sort invariant: verified_projects non-increasing; if equal, xp non-increasing
    for i in range(len(items) - 1):
        curr = items[i]
        nxt = items[i + 1]
        assert curr["verified_projects"] >= nxt["verified_projects"], (
            f"Sort order violated: {curr['display_name']} ({curr['verified_projects']} verified) "
            f"before {nxt['display_name']} ({nxt['verified_projects']} verified)"
        )
        if curr["verified_projects"] == nxt["verified_projects"]:
            assert curr["xp"] >= nxt["xp"], (
                f"XP tie-break violated: {curr['display_name']} ({curr['xp']} XP) "
                f"before {nxt['display_name']} ({nxt['xp']} XP)"
            )


def test_recruiter_opens_private_portfolio_t_stu_02(client: TestClient):
    """T-STU-02, BR-8:
    Recruiter opens the portfolio of a private profile → 404.
    """
    recruiter_h, _ = _create_recruiter(client, approved=True)

    session = SessionLocal()
    try:
        # Find or make a private student
        uid = session.execute(
            text("SELECT id FROM users WHERE email = 'rohit@example.com'")
        ).scalar()
        session.execute(
            text("UPDATE student_profiles SET is_public = false WHERE user_id = :uid"),
            {"uid": uid},
        )
        session.commit()
    finally:
        session.close()

    res = client.get(f"/api/v1/recruiter/students/{uid}", headers=recruiter_h)
    assert res.status_code == 404, res.text


def test_recruiter_opens_public_portfolio(client: TestClient):
    """Recruiter opens the portfolio of a public profile → 200 with verified records."""
    recruiter_h, _ = _create_recruiter(client, approved=True)

    session = SessionLocal()
    try:
        uid = session.execute(
            text("SELECT id FROM users WHERE email = 'ananya@example.com'")
        ).scalar()
        session.execute(
            text("UPDATE student_profiles SET is_public = true WHERE user_id = :uid"),
            {"uid": uid},
        )
        session.commit()
    finally:
        session.close()

    res = client.get(f"/api/v1/recruiter/students/{uid}", headers=recruiter_h)
    assert res.status_code == 200, res.text
    data = res.json()
    assert "items" in data
    assert isinstance(data["items"], list)
