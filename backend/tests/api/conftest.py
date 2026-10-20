"""conftest.py for tests/api — resets seed company/user state before each test.

The seed DB is shared across test runs. Some Phase 1 tests suspend Nova Labs or
Keystone Soft as part of their scenarios, and Phase 2 project tests accumulate
open projects that hit the FR-ORG-5 limit (max 2 open projects).
This fixture ensures seed company/user state is clean before each test.
"""
import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models.project import Project
from app.models.user import Company, CompanyMember, User


def _ensure_seed_companies_active(db) -> None:
    """Make sure Nova Labs and Keystone Soft are approved+active with no open projects."""
    for user_email in [
        "contact@novalabs.com",
        "contact@keystonesoft.io",
    ]:
        # Reactivate user if suspended
        user = db.query(User).filter(User.email == user_email).first()
        if user and not user.is_active:
            user.is_active = True

        # Reapprove company if suspended/rejected
        member = db.query(CompanyMember).join(User, CompanyMember.user_id == User.id).filter(
            User.email == user_email
        ).first()
        if member:
            company = db.query(Company).filter(Company.id == member.company_id).first()
            if company and company.status != "approved":
                company.status = "approved"

            # Close all open projects from previous runs (prevents FR-ORG-5 limit breach)
            if member:
                open_projs = db.query(Project).filter(
                    Project.company_id == member.company_id,
                    Project.status == "open",
                ).all()
                for proj in open_projs:
                    proj.status = "closed"

    db.commit()


def _clean_seed_student_applications(db) -> None:
    """Clear test applications for seed students so tests don't hit the 3-active application limit."""
    from sqlalchemy import text
    seed_student_emails = ["ananya@example.com", "rohit@example.com", "priya@example.com", "dev@example.com"]
    student_users = db.query(User).filter(User.email.in_(seed_student_emails)).all()
    student_ids = [u.id for u in student_users]
    if student_ids:
        # Delete appeals for these students
        db.execute(text("DELETE FROM appeals WHERE student_id = ANY(:sids)"), {"sids": student_ids})
        # Delete uncertified applications for these students
        db.execute(text("""
            DELETE FROM applications
            WHERE student_id = ANY(:sids)
              AND id NOT IN (SELECT application_id FROM certificates)
        """), {"sids": student_ids})
        db.commit()


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def restore_seed_accounts():
    """Test isolation: restore seed company state and student applications before every test."""
    db = SessionLocal()
    try:
        _ensure_seed_companies_active(db)
        _clean_seed_student_applications(db)
    finally:
        db.close()
    yield
