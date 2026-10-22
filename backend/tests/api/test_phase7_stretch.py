"""Tests for Phase 7 Stretch features:
- FR-ADM-7: Anomaly detection rules A1-A5 & admin scan endpoint
- FR-WRK-5: AI Mentor chatbot & company usage count
- FR-EVL-5: Evaluation feedback drafter
- FR-RWD-4: Verified record resume bullet rewriter
"""

import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import SessionLocal


@pytest.fixture
def test_setup():
    db = SessionLocal()
    try:
        from app.core.security import hash_password
        from app.models.user import Company, CompanyMember, StudentProfile, User

        # Ensure admin user
        admin = db.query(User).filter(User.email == "phase7_admin@platform.com").first()
        if not admin:
            admin = User(
                email="phase7_admin@platform.com",
                password_hash=hash_password("AdminPass123!"),
                role="admin",
                email_verified_at=datetime.now(UTC),
            )
            db.add(admin)
            db.commit()

        # Ensure student user
        student = db.query(User).filter(User.email == "phase7_student@univ.edu").first()
        if not student:
            student = User(
                email="phase7_student@univ.edu",
                password_hash=hash_password("StudentPass123!"),
                role="student",
                email_verified_at=datetime.now(UTC),
            )
            db.add(student)
            db.commit()
            sp = StudentProfile(user_id=student.id, full_name="Phase7 Student")
            db.add(sp)
            db.commit()

        # Ensure company user
        c_user = db.query(User).filter(User.email == "phase7_reviewer@acme.org").first()
        if not c_user:
            c_user = User(
                email="phase7_reviewer@acme.org",
                password_hash=hash_password("CompanyPass123!"),
                role="company",
                email_verified_at=datetime.now(UTC),
            )
            db.add(c_user)
            db.commit()
            comp = Company(
                name="Acme Stretch Labs",
                email_domain="acme.org",
                status="approved",
            )
            db.add(comp)
            db.commit()
            cm = CompanyMember(company_id=comp.id, user_id=c_user.id, member_role="owner")
            db.add(cm)
            db.commit()
    finally:
        db.close()


def _login(client: TestClient, email: str, password: str = "AdminPass123!") -> dict[str, str]:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_t_adm_07_anomaly_scan_and_flags_queue(client: TestClient, test_setup):
    """FR-ADM-7: Admin triggers anomaly detection scan and manages flags queue."""
    admin_h = _login(client, "phase7_admin@platform.com", "AdminPass123!")
    student_h = _login(client, "phase7_student@univ.edu", "StudentPass123!")

    # Non-admin cannot scan anomalies
    unauth = client.post("/api/v1/admin/anomalies/scan", headers=student_h)
    assert unauth.status_code == 403

    # Admin runs scan
    scan_res = client.post("/api/v1/admin/anomalies/scan", headers=admin_h)
    assert scan_res.status_code == 200, scan_res.text
    data = scan_res.json()
    assert "rules_executed" in data
    assert "flags" in data

    # Admin reads flags queue
    flags_res = client.get("/api/v1/admin/flags", headers=admin_h)
    assert flags_res.status_code == 200
    flags_data = flags_res.json()
    assert "items" in flags_data
    assert "total" in flags_data


def test_t_wrk_05_ai_mentor_chat_and_usage(client: TestClient, test_setup):
    """FR-WRK-5: AI Mentor provides Socratic guidance for active student workspace."""
    student_h = _login(client, "phase7_student@univ.edu", "StudentPass123!")
    company_h = _login(client, "phase7_reviewer@acme.org", "CompanyPass123!")

    # 1. Create a project and active application
    db = SessionLocal()
    try:
        from app.models.application import Application
        from app.models.project import Milestone, Project
        from app.models.user import Company, User

        c = db.query(Company).filter(Company.name == "Acme Stretch Labs").first()
        u = db.query(User).filter(User.email == "phase7_student@univ.edu").first()
        c_user = db.query(User).filter(User.email == "phase7_reviewer@acme.org").first()

        proj = Project(
            company_id=c.id,
            created_by=c_user.id,
            title="AI Mentor Test Project",
            description="Build a high performance caching service with Redis.",
            category="development",
            difficulty="intermediate",
            duration_days=14,
            xp_max=151,
            status="open",
        )
        db.add(proj)
        db.commit()

        ms = Milestone(
            project_id=proj.id,
            position=1,
            title="Milestone 1: Cache Invalidation",
            description="Implement LRU cache eviction and key expiry.",
            due_day_offset=5,
        )
        db.add(ms)
        db.commit()

        app = Application(
            project_id=proj.id,
            student_id=u.id,
            status="in_progress",  # Active workspace!
            match_score=85,
        )
        db.add(app)
        db.commit()
        app_id = app.id
        ms_id = ms.id
    finally:
        db.close()

    # 2. Student chats with AI Mentor
    chat_res = client.post(
        "/api/v1/ai/mentor/chat",
        json={
            "application_id": str(app_id),
            "milestone_id": str(ms_id),
            "message": "How should I design the key expiry algorithm for the cache?",
        },
        headers=student_h,
    )
    assert chat_res.status_code == 200, chat_res.text
    chat_data = chat_res.json()
    assert chat_data["ai"]["label"] == "AI draft"
    assert "response" in chat_data["result"]
    assert "suggested_next_steps" in chat_data["result"]

    # 3. Company checks mentor usage count
    usage_res = client.get(
        f"/api/v1/applications/{app_id}/mentor-usage",
        headers=company_h,
    )
    assert usage_res.status_code == 200, usage_res.text
    usage_data = usage_res.json()
    assert usage_data["total_exchanges"] >= 1
    assert "private" in usage_data["note"].lower()


def test_t_evl_05_feedback_drafter(client: TestClient, test_setup):
    """FR-EVL-5: Reviewer drafts structured feedback from rough notes."""
    company_h = _login(client, "phase7_reviewer@acme.org", "CompanyPass123!")

    # Create project, application, submission
    db = SessionLocal()
    try:
        from app.models.application import Application, Submission
        from app.models.project import Project
        from app.models.user import Company, User

        c = db.query(Company).filter(Company.name == "Acme Stretch Labs").first()
        u = db.query(User).filter(User.email == "phase7_student@univ.edu").first()
        c_user = db.query(User).filter(User.email == "phase7_reviewer@acme.org").first()

        proj = Project(
            company_id=c.id,
            created_by=c_user.id,
            title="Feedback Drafter Test Project",
            description="Build a high performance caching service.",
            category="development",
            difficulty="intermediate",
            duration_days=14,
            xp_max=150,
            status="open",
        )
        db.add(proj)
        db.commit()

        app = Application(
            project_id=proj.id,
            student_id=u.id,
            status="in_progress",
            match_score=85,
        )
        db.add(app)
        db.commit()

        sub = Submission(
            application_id=app.id,
            version=1,
            repo_url="https://github.com/student/cache-service",
            notes="Implemented full LRU cache with comprehensive tests.",
        )
        db.add(sub)
        db.commit()
        sub_id = sub.id
    finally:
        db.close()

    # Company reviewer drafts feedback
    res = client.post(
        "/api/v1/ai/evaluations/draft-feedback",
        json={
            "submission_id": str(sub_id),
            "rough_notes": "Great clean code structure. Excellent test suite. Needs better benchmark documentation.",
            "rubric_scores": {"code_quality": 5, "tests": 5, "docs": 3},
        },
        headers=company_h,
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["ai"]["label"] == "AI draft"
    assert "strengths" in data["result"]
    assert "improvements" in data["result"]
    assert "next_steps" in data["result"]
    assert "suggested_public_summary" in data["result"]


def test_t_rwd_04_resume_bullet_rewriter(client: TestClient, test_setup, monkeypatch):
    """FR-RWD-4: Verified certificate generates STAR-formatted resume bullets."""
    student_h = _login(client, "phase7_student@univ.edu", "StudentPass123!")

    # Create verified certificate
    db = SessionLocal()
    try:
        import hashlib

        from app.models.application import Application
        from app.models.project import Project
        from app.models.user import Company, User

        c = db.query(Company).filter(Company.name == "Acme Stretch Labs").first()
        u = db.query(User).filter(User.email == "phase7_student@univ.edu").first()
        c_user = db.query(User).filter(User.email == "phase7_reviewer@acme.org").first()

        proj = Project(
            company_id=c.id,
            created_by=c_user.id,
            title="Verified Resume Project",
            description="Production grade microservices architecture.",
            category="development",
            difficulty="advanced",
            duration_days=30,
            xp_max=250,
            status="closed",
        )
        db.add(proj)
        db.commit()

        app = Application(
            project_id=proj.id,
            student_id=u.id,
            status="completed",
            match_score=95,
        )
        db.add(app)
        db.commit()
        from app.core.ids import generate_qr_token, generate_verification_id

        cert_id = uuid.uuid4()
        v_id = generate_verification_id(2026)
        qr = generate_qr_token()
        chash = hashlib.sha256(b"dummy_proof").hexdigest()

        db.execute(
            text("""
                INSERT INTO certificates (id, application_id, verification_id, qr_token, content_hash, xp_awarded, status, issued_at)
                VALUES (:id, :aid, :vid, :qr, :chash, 250, 'issued', now())
            """),
            {"id": cert_id, "aid": app.id, "vid": v_id, "qr": qr, "chash": chash},
        )
        db.commit()
    finally:
        db.close()

    from app.ai import client as ai_client

    captured = {}
    original_run = ai_client.run

    def capture_run(**kwargs):
        captured.update(kwargs)
        return original_run(**kwargs)

    monkeypatch.setattr(ai_client, "run", capture_run)
    res = client.post(
        "/api/v1/ai/rewrite/resume-bullets",
        json={"certificate_id": str(cert_id)},
        headers=student_h,
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["ai"]["label"] == "AI draft"
    assert len(data["result"]["bullets"]) >= 1

    assert captured["input_text"] == "\n".join(
        captured["variables"][key] for key in ("project_title", "skills", "public_summary")
    )
    assert "Verified Resume Project" in captured["input_text"]
    assert data["ai"]["log_id"]
    db = SessionLocal()
    try:
        log = db.execute(
            text("SELECT input_ref FROM ai_logs WHERE id = :lid"),
            {"lid": int(data["ai"]["log_id"])},
        ).scalar_one()
        assert log == hashlib.sha256(captured["input_text"].encode()).hexdigest()[:16]
    finally:
        db.close()
