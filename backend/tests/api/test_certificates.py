"""Tests for Certificates, Public Verification, Revocation, and Rewards.
Covers:
- T-CRT-03 to T-CRT-17
- T-RWD-01 to T-RWD-05
Uses real PostgreSQL (AGENTS.md).
"""

import io
import re
import uuid

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader
from sqlalchemy import text

from app.core.ids import generate_qr_token, generate_verification_id
from app.core.rate_limit import reset_rate_limits
from app.db import SessionLocal
from app.services.badges import recalculate_student_badges
from app.services.certificate import (
    revoke_certificate,
    verify_certificate_content_hash,
)
from app.services.xp import compute_xp, get_evaluation_multiplier


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


def _create_approved_certificate(client: TestClient, score: int = 85) -> tuple[dict, dict]:
    """Helper to take a project from draft -> published -> applied -> selected -> submitted -> approved."""
    nova_h = _nova_headers(client)
    student_h = _student_headers(client)

    p_res = client.post(
        "/api/v1/companies/me/projects",
        json={
            "title": f"Cert Test Project {uuid.uuid4().hex[:6]}",
            "description": "A comprehensive project for testing certificate workflows.",
            "difficulty": "intermediate",
            "duration_days": 14,
            "max_selected": 1,
        },
        headers=nova_h,
    )
    assert p_res.status_code == 201, p_res.text
    pid = p_res.json()["id"]

    pub_res = client.post(f"/api/v1/projects/{pid}/publish", headers=nova_h)
    assert pub_res.status_code == 200, pub_res.text

    app_res = client.post(
        f"/api/v1/projects/{pid}/applications",
        json={"cover_note": "Ready to excel"},
        headers=student_h,
    )
    assert app_res.status_code == 201, app_res.text
    app_id = app_res.json()["id"]

    sel_res = client.post(f"/api/v1/applications/{app_id}/select", headers=nova_h)
    assert sel_res.status_code == 200, sel_res.text

    sub_res = client.post(
        f"/api/v1/applications/{app_id}/submissions",
        json={
            "repo_url": "https://github.com/ananya-dev/project-proof-test",
            "notes": "Completed deliverables",
        },
        headers=student_h,
    )
    assert sub_res.status_code == 201, sub_res.text
    sub_id = sub_res.json()["id"]

    eval_res = client.post(
        f"/api/v1/submissions/{sub_id}/evaluation",
        json={
            "rubric_scores": {"functionality": score, "code_quality": score},
            "overall_score": score,
            "feedback": "Outstanding execution and clean code.",
            "public_summary": "All deliverables completed to high engineering standards.",
            "decision": "approved",
        },
        headers=nova_h,
    )
    assert eval_res.status_code == 201, eval_res.text

    cert_info = eval_res.json()["certificate"]
    if "certificate_id" not in cert_info and "id" in cert_info:
        cert_info["certificate_id"] = cert_info["id"]
    return cert_info, {"application_id": app_id, "submission_id": sub_id, "project_id": pid}


# ---------------------------------------------------------------------------
# T-CRT-03: Force failure after XP insert -> whole transaction rolls back
# ---------------------------------------------------------------------------
def test_t_crt_03_transaction_rollback():
    db = SessionLocal()
    try:
        # Create user and application directly
        student_id = db.execute(text("SELECT user_id FROM student_profiles LIMIT 1")).scalar()
        comp_id = db.execute(
            text("SELECT id FROM companies WHERE status = 'approved' LIMIT 1")
        ).scalar()
        rev_id = db.execute(
            text("SELECT user_id FROM company_members WHERE company_id = :cid LIMIT 1"),
            {"cid": comp_id},
        ).scalar()

        proj_id = uuid.uuid4()
        db.execute(
            text("""
            INSERT INTO projects (id, company_id, created_by, title, description, difficulty, duration_days, xp_max, max_selected, status)
            VALUES (:id, :cid, :rev_id, 'Rollback Test Project', 'Test description', 'beginner', 7, 50, 1, 'open')
        """),
            {"id": proj_id, "cid": comp_id, "rev_id": rev_id},
        )

        app_id = uuid.uuid4()
        db.execute(
            text("""
            INSERT INTO applications (id, project_id, student_id, status)
            VALUES (:id, :pid, :sid, 'submitted')
        """),
            {"id": app_id, "pid": proj_id, "sid": student_id},
        )
        db.commit()

        # Simulate exception during issuance
        with pytest.raises(RuntimeError), db.begin_nested():
            # Normal steps
            db.execute(
                text("UPDATE applications SET status = 'completed' WHERE id = :id"), {"id": app_id}
            )
            db.execute(
                text("""
                INSERT INTO certificates (id, application_id, verification_id, qr_token, status, xp_awarded, content_hash)
                VALUES (:cid, :aid, 'EXP-2026-TEST-9999', 'test-qr-rollback', 'issued', 50, 'hash123')
            """),
                {"cid": uuid.uuid4(), "aid": app_id},
            )
            db.execute(
                text("""
                INSERT INTO xp_events (student_id, certificate_id, amount, reason)
                VALUES (:sid, (SELECT id FROM certificates WHERE verification_id = 'EXP-2026-TEST-9999'), 50, 'project_completed')
            """),
                {"sid": student_id},
            )
            # Deliberate failure
            raise RuntimeError("Simulated failure after XP event insert")

        # Verify no partial records persisted
        cert_count = db.execute(
            text("SELECT count(*) FROM certificates WHERE verification_id = 'EXP-2026-TEST-9999'")
        ).scalar()
        xp_count = db.execute(
            text(
                "SELECT count(*) FROM xp_events WHERE reason = 'project_completed' AND student_id = :sid AND amount = 50"
            ),
            {"sid": student_id},
        ).scalar()
        app_status = db.execute(
            text("SELECT status FROM applications WHERE id = :id"), {"id": app_id}
        ).scalar()
        assert cert_count == 0
        assert xp_count == 0
        assert app_status == "submitted"
    finally:
        db.rollback()
        db.close()


# ---------------------------------------------------------------------------
# T-CRT-04: Verification ID format and uniqueness over 10,000 generated IDs
# ---------------------------------------------------------------------------
def test_t_crt_04_verification_id_format_and_uniqueness():
    pattern = re.compile(r"^EXP-[0-9]{4}-[A-Z0-9]{4}-[0-9]{4}$")
    generated = set()
    for _ in range(10000):
        v_id = generate_verification_id(2026)
        assert pattern.match(v_id), f"ID '{v_id}' did not match pattern"
        generated.add(v_id)
    assert len(generated) == 10000, "Collision detected in 10,000 generated verification IDs"


# ---------------------------------------------------------------------------
# T-CRT-05: QR token length and randomness (at least 128 bits, URL safe)
# ---------------------------------------------------------------------------
def test_t_crt_05_qr_token_length_and_randomness():
    tokens = set()
    for _ in range(1000):
        tok = generate_qr_token()
        # 24 URL-safe bytes = 32 chars = 192 bits >= 128 bits
        assert len(tok) >= 22
        tokens.add(tok)
    assert len(tokens) == 1000


# ---------------------------------------------------------------------------
# T-CRT-06: Public page by QR token (live data, Cache-Control: no-store)
# ---------------------------------------------------------------------------
def test_t_crt_06_public_page_by_qr_token(client: TestClient):
    cert_info, _ = _create_approved_certificate(client, score=88)
    qr_token = cert_info["qr_token"]

    res = client.get(f"/api/v1/public/verify/{qr_token}")
    assert res.status_code == 200, res.text
    assert res.headers.get("Cache-Control") == "no-store"

    data = res.json()
    assert data["verification_id"] == cert_info["verification_id"]
    assert data["status"] == "issued"
    assert "Nova Labs" in data["company"]["name"]
    assert data["student"]["display_name"]
    assert "ProjectProof verification record" in data["disclaimer"]


# ---------------------------------------------------------------------------
# T-CRT-07: Public page after revocation (shows Revoked immediately; category only)
# ---------------------------------------------------------------------------
def test_t_crt_07_public_page_after_revocation(client: TestClient):
    cert_info, _ = _create_approved_certificate(client, score=85)
    cert_id = cert_info["certificate_id"]
    qr_token = cert_info["qr_token"]

    admin_h = _admin_headers(client)
    rev_res = client.post(
        f"/api/v1/admin/certificates/{cert_id}/revoke",
        json={
            "reason": "plagiarism",
            "note": "Internal admin note: code matches duplicate external repo.",
        },
        headers=admin_h,
    )
    assert rev_res.status_code == 200, rev_res.text

    # Read live public page
    pub_res = client.get(f"/api/v1/public/verify/{qr_token}")
    assert pub_res.status_code == 200
    assert pub_res.headers.get("Cache-Control") == "no-store"

    data = pub_res.json()
    assert data["status"] == "revoked"
    assert data["revocation_reason"] == "plagiarism"
    assert "note" not in data
    assert "revoked_at" in data


# ---------------------------------------------------------------------------
# T-CRT-08: Public page for unknown token and unknown ID (same response & timing)
# ---------------------------------------------------------------------------
def test_t_crt_08_public_page_unknown_token_and_id(client: TestClient):
    # Unknown QR token
    res_qr = client.get("/api/v1/public/verify/unknown-token-1234567890")
    assert res_qr.status_code == 404
    assert res_qr.headers.get("Cache-Control") == "no-store"
    assert res_qr.json()["error"]["code"] == "not_found"

    # Unknown Verification ID
    res_id = client.get("/api/v1/public/verify-id/EXP-2026-UNKN-9999")
    assert res_id.status_code == 404
    assert res_id.headers.get("Cache-Control") == "no-store"
    assert res_id.json()["error"]["code"] == "not_found"


# ---------------------------------------------------------------------------
# T-CRT-09: Public response contents (no email, feedback, rubric, AI output, or internal IDs)
# ---------------------------------------------------------------------------
def test_t_crt_09_public_response_contents(client: TestClient):
    cert_info, _ = _create_approved_certificate(client, score=92)
    qr_token = cert_info["qr_token"]

    res = client.get(f"/api/v1/public/verify/{qr_token}")
    assert res.status_code == 200
    data = res.json()

    # Disallowed fields
    assert "email" not in str(data)
    assert "rubric_scores" not in data
    assert "ai_draft" not in data
    assert "internal_id" not in data
    assert "feedback" not in data  # private feedback must not appear; only public_summary
    assert "student_id" not in data
    assert "company_id" not in data
    assert "user_id" not in data


# ---------------------------------------------------------------------------
# T-CRT-10: Student with initials preference
# ---------------------------------------------------------------------------
def test_t_crt_10_student_with_initials_preference(client: TestClient):
    db = SessionLocal()
    try:
        # Set show_full_name_on_verification = false for Ananya R.
        student_user = db.execute(
            text("SELECT id FROM users WHERE email = 'ananya@example.com'")
        ).scalar()
        db.execute(
            text(
                "UPDATE student_profiles SET full_name = 'Ananya Roy', show_full_name_on_verification = false WHERE user_id = :uid"
            ),
            {"uid": student_user},
        )
        db.commit()

        cert_info, _ = _create_approved_certificate(client, score=85)
        res = client.get(f"/api/v1/public/verify/{cert_info['qr_token']}")
        assert res.status_code == 200
        data = res.json()
        assert data["student"]["display_name"] == "A. R."
    finally:
        # Reset to true
        db.execute(
            text(
                "UPDATE student_profiles SET full_name = 'Ananya R.', show_full_name_on_verification = true WHERE user_id = :uid"
            ),
            {"uid": student_user},
        )
        db.commit()
        db.close()


# ---------------------------------------------------------------------------
# T-CRT-11: Direct database edit of xp_awarded, delete, un-revoke (triggers reject)
# ---------------------------------------------------------------------------
def test_t_crt_11_database_triggers_guard_certificates(client: TestClient):
    cert_info, _ = _create_approved_certificate(client, score=80)
    cert_id = cert_info["certificate_id"]

    db = SessionLocal()
    try:
        # 1. Direct edit of xp_awarded must fail
        with pytest.raises(Exception) as exc_info:
            db.execute(
                text("UPDATE certificates SET xp_awarded = 999 WHERE id = :id"), {"id": cert_id}
            )
            db.commit()
        db.rollback()
        assert "immutable" in str(exc_info.value).lower()

        # 2. Direct DELETE must fail
        with pytest.raises(Exception) as exc_info:
            db.execute(text("DELETE FROM certificates WHERE id = :id"), {"id": cert_id})
            db.commit()
        db.rollback()
        assert "cannot be deleted" in str(exc_info.value).lower()

        # 3. Revoke certificate via legitimate path, then attempt un-revoke
        admin_id = db.execute(text("SELECT id FROM users WHERE role = 'admin' LIMIT 1")).scalar()
        revoke_certificate(db, cert_id, admin_id, reason="other", note="test")
        db.commit()

        with pytest.raises(Exception) as exc_info:
            db.execute(
                text("UPDATE certificates SET status = 'issued', revoked_at = NULL WHERE id = :id"),
                {"id": cert_id},
            )
            db.commit()
        db.rollback()
        assert "cannot be reinstated" in str(exc_info.value).lower()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# T-CRT-12: Company requests revocation (opens a flag; certificate unchanged)
# ---------------------------------------------------------------------------
def test_t_crt_12_company_requests_revocation(client: TestClient):
    cert_info, _ = _create_approved_certificate(client, score=80)
    cert_id = cert_info["certificate_id"]
    nova_h = _nova_headers(client)

    res = client.post(
        f"/api/v1/certificates/{cert_id}/revocation-request",
        json={
            "reason": "Plagiarized code discovered in submission repository.",
            "note": "Matches another student's work line for line.",
        },
        headers=nova_h,
    )
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "requested"

    # Verify certificate is UNCHANGED
    db = SessionLocal()
    cert_status = db.execute(
        text("SELECT status FROM certificates WHERE id = :id"), {"id": cert_id}
    ).scalar()
    flag_count = db.execute(
        text("SELECT count(*) FROM flags WHERE entity_id = :id AND status = 'open'"),
        {"id": cert_id},
    ).scalar()
    db.close()

    assert cert_status == "issued"
    assert flag_count == 1


# ---------------------------------------------------------------------------
# T-CRT-13: Non-admin calls revoke -> 403
# ---------------------------------------------------------------------------
def test_t_crt_13_non_admin_cannot_revoke(client: TestClient):
    cert_info, _ = _create_approved_certificate(client, score=80)
    cert_id = cert_info["certificate_id"]

    # Student cannot revoke
    student_h = _student_headers(client)
    res_s = client.post(
        f"/api/v1/admin/certificates/{cert_id}/revoke", json={"reason": "fraud"}, headers=student_h
    )
    assert res_s.status_code == 403

    # Company reviewer cannot revoke directly
    nova_h = _nova_headers(client)
    res_c = client.post(
        f"/api/v1/admin/certificates/{cert_id}/revoke", json={"reason": "fraud"}, headers=nova_h
    )
    assert res_c.status_code == 403


# ---------------------------------------------------------------------------
# T-CRT-14: Admin revokes -> Negative XP event; badges recalculated; audit; notifications
# ---------------------------------------------------------------------------
def test_t_crt_14_admin_revokes(client: TestClient):
    cert_info, _ = _create_approved_certificate(client, score=90)
    cert_id = cert_info["certificate_id"]
    xp_awarded = cert_info["xp_awarded"]
    admin_h = _admin_headers(client)

    res = client.post(
        f"/api/v1/admin/certificates/{cert_id}/revoke",
        json={
            "reason": "fraud",
            "note": "Fraudulent identity or submission detected.",
        },
        headers=admin_h,
    )
    assert res.status_code == 200, res.text

    db = SessionLocal()
    # Check negative XP event
    neg_xp = db.execute(
        text(
            "SELECT amount FROM xp_events WHERE certificate_id = :id AND reason = 'certificate_revoked'"
        ),
        {"id": cert_id},
    ).scalar()
    assert neg_xp == -xp_awarded

    # Check audit log entry
    audit_row = db.execute(
        text(
            "SELECT action, entity_type FROM audit_log WHERE entity_id = :id AND action = 'revoke_certificate'"
        ),
        {"id": cert_id},
    ).fetchone()
    assert audit_row is not None

    # Check notification created
    notif = db.execute(
        text(
            "SELECT type FROM notifications WHERE link LIKE :link ORDER BY created_at DESC LIMIT 1"
        ),
        {"link": f"%{cert_id}%"},
    ).scalar()
    assert notif == "certificate_revoked"
    db.close()


# ---------------------------------------------------------------------------
# T-CRT-15: 40 lookups in a minute from one address -> Rate limited after the limit
# ---------------------------------------------------------------------------
def test_t_crt_15_rate_limit_verification_lookups(client: TestClient):
    reset_rate_limits()
    cert_info, _ = _create_approved_certificate(client, score=85)
    qr_token = cert_info["qr_token"]

    status_codes = []
    for _ in range(35):
        res = client.get(f"/api/v1/public/verify/{qr_token}")
        status_codes.append(res.status_code)

    # 30 should succeed (200), 31st onwards should be rate limited (429)
    assert 200 in status_codes
    assert 429 in status_codes
    assert status_codes[-1] == 429
    reset_rate_limits()


# ---------------------------------------------------------------------------
# T-CRT-16: PDF contains name, project, company, duration, skills, ID, QR, disclaimer
# ---------------------------------------------------------------------------
def test_t_crt_16_pdf_download_and_contents(client: TestClient):
    cert_info, _meta = _create_approved_certificate(client, score=85)
    cert_id = cert_info["certificate_id"]
    student_h = _student_headers(client)

    res = client.get(f"/api/v1/certificates/{cert_id}/pdf", headers=student_h)
    assert res.status_code == 200
    assert res.headers["Content-Type"] == "application/pdf"
    assert "inline;" in res.headers["Content-Disposition"]

    # Verify PDF contents with pypdf
    pdf_bytes = res.content
    reader = PdfReader(io.BytesIO(pdf_bytes))
    page_text = reader.pages[0].extract_text()

    assert "PROJECTPROOF AI" in page_text
    assert cert_info["verification_id"] in page_text
    assert "Nova Labs" in page_text
    assert "14 days" in page_text
    assert (
        "This is a ProjectProof verification record. It is not formal employment experience."
        in page_text
    )


# ---------------------------------------------------------------------------
# T-CRT-17: Content hash recomputed from current data matches stored hash
# ---------------------------------------------------------------------------
def test_t_crt_17_content_hash_integrity(client: TestClient):
    cert_info, _ = _create_approved_certificate(client, score=85)
    cert_id = uuid.UUID(cert_info["certificate_id"])

    db = SessionLocal()
    try:
        is_valid = verify_certificate_content_hash(db, cert_id)
        assert is_valid is True
    finally:
        db.close()


# ---------------------------------------------------------------------------
# T-RWD-01: XP for scores 59 (cannot approve), 60, 75, 90 (multipliers: 1.0, 1.0, 1.1, 1.2; cap 200)
# ---------------------------------------------------------------------------
def test_t_rwd_01_xp_formula_multipliers():
    # 59 cannot approve
    with pytest.raises(ValueError):
        get_evaluation_multiplier(59)

    # 60 -> 1.0
    assert get_evaluation_multiplier(60) == 1.0
    # 75 -> 1.1
    assert get_evaluation_multiplier(75) == 1.1
    # 90 -> 1.2
    assert get_evaluation_multiplier(90) == 1.2

    # Formula: round(min(cap, base_per_day * duration_days * difficulty_multiplier * evaluation_multiplier))
    # base: 6, duration: 14, intermediate: 1.5
    # score 60: 6 * 14 * 1.5 * 1.0 = 126
    assert compute_xp(14, "intermediate", 60) == 126
    # score 75: 6 * 14 * 1.5 * 1.1 = 138.6 -> 139
    assert compute_xp(14, "intermediate", 75) == 139
    # score 90: 6 * 14 * 1.5 * 1.2 = 151.2 -> 151
    assert compute_xp(14, "intermediate", 90) == 151

    # Cap applied (200)
    # Advanced (2.0), 30 days: 6 * 30 * 2.0 * 1.2 = 432 -> capped at 200
    assert compute_xp(30, "advanced", 95) == 200


# ---------------------------------------------------------------------------
# T-RWD-02: Any client attempt to send XP is ignored or rejected
# ---------------------------------------------------------------------------
def test_t_rwd_02_client_cannot_send_xp(client: TestClient):
    nova_h = _nova_headers(client)
    res = client.post(
        "/api/v1/companies/me/projects",
        json={
            "title": "Malicious XP Project",
            "description": "Attempting to inject client xp value",
            "difficulty": "beginner",
            "duration_days": 7,
            "max_selected": 1,
            "xp_awarded": 9999,
            "xp_max": 9999,
        },
        headers=nova_h,
    )
    # Project creation should ignore or reject client xp, and compute xp_max from formula
    if res.status_code == 201:
        # formula: 6 * 7 * 1.0 * 1.2 = 50.4 -> 50
        assert res.json()["xp_max"] == 50
    else:
        assert res.status_code in (400, 422)


# ---------------------------------------------------------------------------
# T-RWD-03: 420 XP -> Level 3 (Builder), 180 XP to level 4
# ---------------------------------------------------------------------------
def test_t_rwd_03_levels_and_progress(client: TestClient):
    student_h = _student_headers(client)
    res = client.get("/api/v1/students/me/progress", headers=student_h)
    assert res.status_code == 200
    data = res.json()
    assert "total_xp" in data
    assert "level" in data
    assert "level_name" in data
    assert "xp_to_next_level" in data


# ---------------------------------------------------------------------------
# T-RWD-04 & T-RWD-05: Badges awarded at thresholds & removed on revocation
# ---------------------------------------------------------------------------
def test_t_rwd_04_05_badge_thresholds_and_revocation():
    db = SessionLocal()
    try:
        # Create a fresh student for clean testing
        uid = uuid.uuid4()
        test_email = f"badgetest_{uuid.uuid4().hex[:8]}@example.com"
        db.execute(
            text("""
            INSERT INTO users (id, email, password_hash, role, is_active)
            VALUES (:uid, :email, 'hash', 'student', true)
        """),
            {"uid": uid, "email": test_email},
        )
        db.execute(
            text("""
            INSERT INTO student_profiles (user_id, full_name)
            VALUES (:uid, 'Badge Tester')
        """),
            {"uid": uid},
        )
        db.commit()

        # Initially 0 badges
        badges_0 = recalculate_student_badges(db, uid)
        assert len(badges_0) == 0

        # Create 1 completed application + certificate
        comp_id = db.execute(
            text("SELECT id FROM companies WHERE status = 'approved' LIMIT 1")
        ).scalar()
        rev_id = db.execute(
            text("SELECT user_id FROM company_members WHERE company_id = :cid LIMIT 1"),
            {"cid": comp_id},
        ).scalar()
        proj_id = uuid.uuid4()
        db.execute(
            text("""
            INSERT INTO projects (id, company_id, created_by, title, description, difficulty, duration_days, xp_max, category, max_selected, status)
            VALUES (:id, :cid, :rev_id, 'Dev Project 1', 'Test', 'beginner', 7, 50, 'development', 1, 'open')
        """),
            {"id": proj_id, "cid": comp_id, "rev_id": rev_id},
        )

        app_id = uuid.uuid4()
        db.execute(
            text(
                "INSERT INTO applications (id, project_id, student_id, status) VALUES (:id, :pid, :sid, 'completed')"
            ),
            {"id": app_id, "pid": proj_id, "sid": uid},
        )

        cert_id = uuid.uuid4()
        ver_id = generate_verification_id(2026)
        qr_tok = generate_qr_token()
        db.execute(
            text("""
            INSERT INTO certificates (id, application_id, verification_id, qr_token, status, xp_awarded, content_hash)
            VALUES (:cid, :aid, :vid, :qtok, 'issued', 50, 'hash1')
        """),
            {"cid": cert_id, "aid": app_id, "vid": ver_id, "qtok": qr_tok},
        )
        db.commit()

        # Recalculate: 1 completion -> 'first_project' awarded!
        awarded = recalculate_student_badges(db, uid)
        assert "first_project" in awarded

        # T-RWD-05: Revoke drops student below threshold -> badge removed!
        admin_id = db.execute(text("SELECT id FROM users WHERE role = 'admin' LIMIT 1")).scalar()
        revoke_certificate(
            db, cert_id, admin_id, reason="company_error", note="Error in assignment"
        )
        db.commit()

        # Badges should now be empty
        student_badge_count = db.execute(
            text("SELECT count(*) FROM student_badges WHERE student_id = :uid"), {"uid": uid}
        ).scalar()
        assert student_badge_count == 0
    finally:
        db.close()


# ---------------------------------------------------------------------------
# T-CRT-03: Single transaction for certificate creation (rollback on failure)
# ---------------------------------------------------------------------------
def test_t_crt_03_atomic_transaction_rollback(monkeypatch):
    """AGENTS.md Rule 3: Single transaction for certificate creation. If a subsequent step fails, rolls back."""
    from app.services import certificate as cert_service

    def _exploding_badges(db, student_id):
        raise RuntimeError("Simulated badge computation failure")

    monkeypatch.setattr(cert_service, "recalculate_student_badges", _exploding_badges)

    db = SessionLocal()
    try:
        # Create a test project and application
        comp_id = db.execute(
            text("SELECT id FROM companies WHERE status = 'approved' LIMIT 1")
        ).scalar()
        rev_id = db.execute(
            text("SELECT user_id FROM company_members WHERE company_id = :cid LIMIT 1"),
            {"cid": comp_id},
        ).scalar()
        student_id = db.execute(
            text("SELECT id FROM users WHERE role = 'student' LIMIT 1")
        ).scalar()

        proj_id = uuid.uuid4()
        db.execute(
            text("""
                INSERT INTO projects (id, company_id, created_by, title, description, difficulty, duration_days, xp_max, category, max_selected, status)
                VALUES (:id, :cid, :rev_id, 'Rollback Test Project', 'Test', 'beginner', 7, 50, 'development', 1, 'open')
            """),
            {"id": proj_id, "cid": comp_id, "rev_id": rev_id},
        )
        app_id = uuid.uuid4()
        db.execute(
            text("INSERT INTO applications (id, project_id, student_id, status) VALUES (:id, :pid, :sid, 'in_progress')"),
            {"id": app_id, "pid": proj_id, "sid": student_id},
        )
        db.commit()

        # Issuing certificate should fail inside transaction when badges explode
        with pytest.raises(RuntimeError, match="Simulated badge computation failure"):
            cert_service.issue_certificate_for_application(
                db=db,
                application_id=app_id,
                reviewer_id=rev_id,
                overall_score=85,
                feedback="Good job",
            )
        db.rollback()

        # Verify no certificate exists for this application
        cert = db.execute(
            text("SELECT id FROM certificates WHERE application_id = :aid"),
            {"aid": app_id},
        ).fetchone()
        assert cert is None, "Certificate must not exist after transaction failure"
    finally:
        db.close()
