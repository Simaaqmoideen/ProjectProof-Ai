"""Seed test and demo data into ProjectProof AI database."""
from datetime import UTC, datetime

from app.core.security import hash_password
from app.db import SessionLocal
from app.models.user import (
    Company,
    CompanyMember,
    RecruiterProfile,
    StudentProfile,
    User,
)
from app.services.audit_service import AuditService


def seed_database():
    db = SessionLocal()
    try:
        now = datetime.now(UTC)
        print("Seeding database...")

        # 1. Admin user
        admin = db.query(User).filter(User.email == "admin@projectproof.ai").first()
        if not admin:
            admin = User(
                email="admin@projectproof.ai",
                password_hash=hash_password("AdminSecure2026!"),
                role="admin",
                is_active=True,
                email_verified_at=now,
            )
            db.add(admin)
            db.flush()
            AuditService.log(db, action="seed_admin", actor_id=admin.id, entity_type="user", entity_id=str(admin.id))
            print("Created admin: admin@projectproof.ai")

        # 2. Company 1: Nova Labs (approved)
        c1_user = db.query(User).filter(User.email == "contact@novalabs.com").first()
        if not c1_user:
            c1_user = User(
                email="contact@novalabs.com",
                password_hash=hash_password("NovaLabs2026!"),
                role="company",
                is_active=True,
                email_verified_at=now,
            )
            db.add(c1_user)
            db.flush()

            c1 = Company(
                name="Nova Labs",
                website="https://novalabs.com",
                email_domain="novalabs.com",
                description="Specialists in enterprise backend and cloud distributed systems.",
                registration_doc_key="docs/novalabs_reg.pdf",
                status="approved",
                trust_score=50,
                reviewed_by=admin.id,
                reviewed_at=now,
            )
            db.add(c1)
            db.flush()

            db.add(CompanyMember(company_id=c1.id, user_id=c1_user.id, member_role="owner"))
            print("Created approved company: Nova Labs")

        # 3. Company 2: Keystone Soft (approved)
        c2_user = db.query(User).filter(User.email == "contact@keystonesoft.io").first()
        if not c2_user:
            c2_user = User(
                email="contact@keystonesoft.io",
                password_hash=hash_password("Keystone2026!"),
                role="company",
                is_active=True,
                email_verified_at=now,
            )
            db.add(c2_user)
            db.flush()

            c2 = Company(
                name="Keystone Soft",
                website="https://keystonesoft.io",
                email_domain="keystonesoft.io",
                description="Modern full-stack web and developer tooling agency.",
                registration_doc_key="docs/keystone_reg.pdf",
                status="approved",
                trust_score=50,
                reviewed_by=admin.id,
                reviewed_at=now,
            )
            db.add(c2)
            db.flush()

            db.add(CompanyMember(company_id=c2.id, user_id=c2_user.id, member_role="owner"))
            print("Created approved company: Keystone Soft")

        # 4. Company 3: BrightWave Tech (pending, free email)
        c3_user = db.query(User).filter(User.email == "brightwave.tech@gmail.com").first()
        if not c3_user:
            c3_user = User(
                email="brightwave.tech@gmail.com",
                password_hash=hash_password("BrightWave2026!"),
                role="company",
                is_active=True,
                email_verified_at=now,
            )
            db.add(c3_user)
            db.flush()

            c3 = Company(
                name="BrightWave Tech",
                website="https://brightwavetech.net",
                email_domain="gmail.com",
                description="Early stage startup developing AI powered tools.",
                registration_doc_key=None,
                status="pending",
                trust_score=50,
            )
            db.add(c3)
            db.flush()

            db.add(CompanyMember(company_id=c3.id, user_id=c3_user.id, member_role="owner"))
            print("Created pending company: BrightWave Tech")

        # 5. Students
        students_data = [
            ("ananya@example.com", "Ananya Sharma", "B.Tech Computer Science", "National Institute of Tech", 2026),
            ("rohit@example.com", "Rohit Verma", "Full-Stack Web Enthusiast", "Delhi Technological University", 2026),
            ("priya@example.com", "Priya Nair", "Data Science & ML Major", "IIT Madras", 2025),
        ]
        for email, full_name, headline, college, grad_year in students_data:
            s_user = db.query(User).filter(User.email == email).first()
            if not s_user:
                s_user = User(
                    email=email,
                    password_hash=hash_password("StudentPass2026!"),
                    role="student",
                    is_active=True,
                    email_verified_at=now,
                )
                db.add(s_user)
                db.flush()

                db.add(StudentProfile(
                    user_id=s_user.id,
                    full_name=full_name,
                    headline=headline,
                    college=college,
                    graduation_year=grad_year,
                    is_public=True,
                ))
                print(f"Created student: {full_name}")

        # 6. Recruiter: Apex Staffing
        r_user = db.query(User).filter(User.email == "recruiter@apexsearch.com").first()
        if not r_user:
            r_user = User(
                email="recruiter@apexsearch.com",
                password_hash=hash_password("Recruiter2026!"),
                role="recruiter",
                is_active=True,
                email_verified_at=now,
            )
            db.add(r_user)
            db.flush()

            db.add(RecruiterProfile(
                user_id=r_user.id,
                full_name="Vikram Mehta",
                organization="Apex Talent Search",
                work_email_domain="apexsearch.com",
                status="pending",
            ))
            print("Created pending recruiter: Vikram Mehta (Apex Talent Search)")

        db.commit()
        print("Database seeding completed successfully.")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
