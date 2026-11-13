"""Seed test and demo data into ProjectProof AI database.

Produces:
  - 1 admin
  - 2 approved companies (Nova Labs, Keystone Soft) + 1 pending (BrightWave Tech)
  - 1 pending recruiter
  - 5 students (all public)
  - 6 open projects (3 per approved company)
  - 3 completed projects with certificates:
      * 2 issued (verification IDs printed to stdout for Playwright)
      * 1 revoked (QR token printed to stdout for Playwright)
"""

import hashlib
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import text

from app.core.ids import generate_verification_id
from app.core.security import hash_password
from app.db import SessionLocal
from app.models.application import Application, Evaluation, Submission
from app.models.project import Project
from app.models.user import (
    Company,
    CompanyMember,
    RecruiterProfile,
    StudentProfile,
    User,
)


def _get_or_create_user(db, email: str, password: str, role: str, now: datetime) -> User:
    u = db.query(User).filter(User.email == email).first()
    if not u:
        u = User(
            email=email,
            password_hash=hash_password(password),
            role=role,
            is_active=True,
            email_verified_at=now,
        )
        db.add(u)
        db.flush()
    return u


def seed_database():
    db = SessionLocal()
    try:
        now = datetime.now(UTC)
        print("Seeding database...")

        # ── 1. Admin ─────────────────────────────────────────────────────────
        admin = _get_or_create_user(db, "admin@projectproof.ai", "AdminSecure2026!", "admin", now)
        print("Admin: admin@projectproof.ai / AdminSecure2026!")

        # ── 2. Approved company 1: Nova Labs ─────────────────────────────────
        c1_user = _get_or_create_user(db, "contact@novalabs.com", "NovaLabs2026!", "company", now)
        c1 = db.query(Company).filter(Company.email_domain == "novalabs.com").first()
        if not c1:
            c1 = Company(
                name="Nova Labs",
                website="https://novalabs.com",
                email_domain="novalabs.com",
                description="Specialists in enterprise backend and cloud distributed systems.",
                registration_doc_key="docs/novalabs_reg.pdf",
                status="approved",
                trust_score=75,
                reviewed_by=admin.id,
                reviewed_at=now,
            )
            db.add(c1)
            db.flush()
            db.add(CompanyMember(company_id=c1.id, user_id=c1_user.id, member_role="owner"))
            print("Company: Nova Labs (approved)")

        # ── 3. Approved company 2: Keystone Soft ─────────────────────────────
        c2_user = _get_or_create_user(
            db, "contact@keystonesoft.io", "Keystone2026!", "company", now
        )
        c2 = db.query(Company).filter(Company.email_domain == "keystonesoft.io").first()
        if not c2:
            c2 = Company(
                name="Keystone Soft",
                website="https://keystonesoft.io",
                email_domain="keystonesoft.io",
                description="Modern full-stack web and developer tooling agency.",
                registration_doc_key="docs/keystone_reg.pdf",
                status="approved",
                trust_score=60,
                reviewed_by=admin.id,
                reviewed_at=now,
            )
            db.add(c2)
            db.flush()
            db.add(CompanyMember(company_id=c2.id, user_id=c2_user.id, member_role="owner"))
            print("Company: Keystone Soft (approved)")

        # ── 4. Pending company 3: BrightWave Tech ────────────────────────────
        c3_user = _get_or_create_user(
            db, "brightwave.tech@gmail.com", "BrightWave2026!", "company", now
        )
        c3 = db.query(Company).filter(Company.name == "BrightWave Tech").first()
        if not c3:
            c3 = Company(
                name="BrightWave Tech",
                website="https://brightwavetech.net",
                email_domain="brightwavetech.net",
                description="Early stage startup developing AI powered tools.",
                status="pending",
                trust_score=0,
            )
            db.add(c3)
            db.flush()
            db.add(CompanyMember(company_id=c3.id, user_id=c3_user.id, member_role="owner"))
            print("Company: BrightWave Tech (pending)")

        db.commit()

        # Refresh company objects after commit
        c1 = db.query(Company).filter(Company.email_domain == "novalabs.com").first()
        c2 = db.query(Company).filter(Company.email_domain == "keystonesoft.io").first()

        # ── 5. Students (5 total) ─────────────────────────────────────────────
        students_data = [
            (
                "ananya@example.com",
                "Ananya Sharma",
                "B.Tech Computer Science",
                "National Institute of Tech",
                2026,
            ),
            (
                "rohit@example.com",
                "Rohit Verma",
                "Full-Stack Web Enthusiast",
                "Delhi Technological University",
                2026,
            ),
            ("priya@example.com", "Priya Nair", "Data Science & ML Major", "IIT Madras", 2025),
            (
                "siddharth@example.com",
                "Siddharth Rao",
                "Cloud & DevOps Engineer",
                "Manipal Institute of Tech",
                2026,
            ),
            (
                "aisha@example.com",
                "Aisha Khan",
                "UI/UX and Frontend Developer",
                "BITS Pilani",
                2025,
            ),
        ]
        students: list[User] = []
        for email, full_name, headline, college, grad_year in students_data:
            s_user = _get_or_create_user(db, email, "StudentPass2026!", "student", now)
            if not db.query(StudentProfile).filter(StudentProfile.user_id == s_user.id).first():
                db.add(
                    StudentProfile(
                        user_id=s_user.id,
                        full_name=full_name,
                        headline=headline,
                        college=college,
                        graduation_year=grad_year,
                        is_public=True,
                        show_full_name_on_verification=True,
                    )
                )
                print(f"Student: {full_name}")
            students.append(s_user)
        db.commit()

        # ── 6. Pending recruiter: Apex Talent Search ─────────────────────────
        r_user = _get_or_create_user(
            db, "recruiter@apexsearch.com", "Recruiter2026!", "recruiter", now
        )
        if not db.query(RecruiterProfile).filter(RecruiterProfile.user_id == r_user.id).first():
            db.add(
                RecruiterProfile(
                    user_id=r_user.id,
                    full_name="Vikram Mehta",
                    organization="Apex Talent Search",
                    work_email_domain="apexsearch.com",
                    status="pending",
                )
            )
            print("Recruiter: Vikram Mehta (Apex Talent Search) [pending]")
        db.commit()

        # ── 7. Open projects (6 total: 3 per approved company) ───────────────
        open_projects_data = [
            (c1, c1_user, "API Gateway Microservices", "development", "intermediate", 21, 200),
            (c1, c1_user, "Cloud Cost Optimisation Dashboard", "data", "advanced", 28, 300),
            (c1, c1_user, "Developer Docs Portal", "design", "beginner", 14, 100),
            (c2, c2_user, "React Component Library", "development", "intermediate", 21, 200),
            (c2, c2_user, "A/B Testing SDK for Web", "development", "advanced", 28, 250),
            (c2, c2_user, "Accessibility Audit Toolkit", "design", "intermediate", 14, 150),
        ]
        for company, creator, title, category, difficulty, days, xp in open_projects_data:
            if not db.query(Project).filter(Project.title == title).first():
                db.add(
                    Project(
                        company_id=company.id,
                        created_by=creator.id,
                        title=title,
                        description=f"Demo open project: {title}. Real-world scope for portfolio building.",
                        category=category,
                        difficulty=difficulty,
                        duration_days=days,
                        xp_max=xp,
                        status="open",
                    )
                )
                print(f"Open project: {title}")
        db.commit()

        # ── 8. Completed projects with certificates ───────────────────────────
        # Pipeline: Project(closed) → Application(completed) → Submission → Evaluation(approved) → Certificate
        # Raw SQL INSERT for certificate to bypass ORM-level trigger restrictions in seed context.

        cert_configs = [
            {
                "title": "ML Pipeline for Churn Prediction",
                "student_idx": 2,  # Priya Nair
                "company": c1,
                "creator": c1_user,
                "xp": 300,
                "cert_status": "issued",
                "label": "ISSUED_1",
                "env_key": "PLAYWRIGHT_ISSUED_QR_TOKEN",
            },
            {
                "title": "Full-Stack E-Commerce Platform",
                "student_idx": 0,  # Ananya Sharma
                "company": c2,
                "creator": c2_user,
                "xp": 200,
                "cert_status": "issued",
                "label": "ISSUED_2",
                "env_key": "PLAYWRIGHT_ISSUED_QR_TOKEN_2",
            },
            {
                "title": "Plagiarised Open-Source Dashboard",
                "student_idx": 1,  # Rohit Verma
                "company": c1,
                "creator": c1_user,
                "xp": 0,
                "cert_status": "revoked",
                "label": "REVOKED",
                "env_key": "PLAYWRIGHT_REVOKED_QR_TOKEN",
            },
        ]

        for cfg in cert_configs:
            proj_title: str = cfg["title"]
            if db.query(Project).filter(Project.title == proj_title).first():
                print(f"Skipping (already exists): {proj_title}")
                continue

            company: Company = cfg["company"]
            creator: User = cfg["creator"]
            student: User = students[cfg["student_idx"]]
            xp: int = cfg["xp"] if cfg["xp"] > 0 else 200
            cert_status: str = cfg["cert_status"]

            # Closed project
            proj = Project(
                company_id=company.id,
                created_by=creator.id,
                title=proj_title,
                description=f"Completed demo project: {proj_title}.",
                category="development",
                difficulty="intermediate",
                duration_days=21,
                xp_max=xp,
                status="closed",
            )
            db.add(proj)
            db.flush()

            # Completed application
            completed_at = now - timedelta(days=10)
            app = Application(
                project_id=proj.id,
                student_id=student.id,
                status="completed",
                match_score=88,
                started_at=now - timedelta(days=31),
                completed_at=completed_at,
            )
            db.add(app)
            db.flush()

            # Submission (CHECK: repo_url IS NOT NULL OR file_key IS NOT NULL)
            slug = proj_title.lower().replace(" ", "-")
            sub = Submission(
                application_id=app.id,
                version=1,
                repo_url=f"https://github.com/demo-student/{slug}",
                notes="Final submission for demo certificate.",
            )
            db.add(sub)
            db.flush()

            # Approved evaluation
            ev = Evaluation(
                submission_id=sub.id,
                reviewer_id=creator.id,
                overall_score=90,
                feedback="Well-structured implementation with good test coverage.",
                public_summary="Student demonstrated strong practical skills throughout the project.",
                decision="approved",
            )
            db.add(ev)
            db.flush()

            # Certificate via raw SQL (bypasses ORM-level trigger for seed context)
            v_id = generate_verification_id(2026)
            qr = f"demo-{cert_status}-qr-{uuid.uuid4().hex[:8]}"
            chash = hashlib.sha256(proj_title.encode()).hexdigest()
            cert_id = uuid.uuid4()

            db.execute(
                text("""
                    INSERT INTO certificates
                        (id, application_id, verification_id, qr_token, content_hash,
                         xp_awarded, status, issued_at)
                    VALUES
                        (:id, :aid, :vid, :qr, :chash, :xp, 'issued', :issued_at)
                """),
                {
                    "id": cert_id,
                    "aid": app.id,
                    "vid": v_id,
                    "qr": qr,
                    "chash": chash,
                    "xp": xp,
                    "issued_at": completed_at,
                },
            )

            if cert_status == "revoked":
                db.execute(
                    text("""
                        UPDATE certificates
                        SET status            = 'revoked',
                            revoked_at        = :revoked_at,
                            revoked_by        = :revoked_by,
                            revocation_reason = 'plagiarism',
                            revocation_note   = 'Demo seed: plagiarism detected post-award.'
                        WHERE id = :cid
                    """),
                    {"revoked_at": now - timedelta(days=5), "revoked_by": admin.id, "cid": cert_id},
                )

            db.commit()
            label: str = cfg["label"]
            env_key: str = cfg["env_key"]
            print(
                f"\nCertificate [{label}] — {proj_title}"
                f"\n  Verification ID : {v_id}"
                f"\n  QR Token        : {qr}"
                f"\n  Status          : {cert_status}"
                f"\n  Playwright env  : {env_key}={qr}"
            )

        print("\nDatabase seeding completed successfully.")
        print("Copy the Playwright env vars above to run E2E tests against live data.\n")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
