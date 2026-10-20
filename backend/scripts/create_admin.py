"""Create an admin from the command line. Admins are never created by public sign-up (FR-AUTH-6)."""
import argparse
import sys
from datetime import UTC, datetime

from app.core.security import hash_password, validate_password_strength
from app.db import SessionLocal
from app.models.user import User
from app.services.audit_service import AuditService


def create_admin(email: str, password: str) -> None:
    validate_password_strength(password)

    db = SessionLocal()
    try:
        clean_email = email.strip().lower()
        existing = db.query(User).filter(User.email == clean_email).first()
        if existing:
            if existing.role != "admin":
                print(f"Error: User {clean_email} already exists with role {existing.role}")
                sys.exit(1)
            print(f"Admin user {clean_email} already exists. Updating password...")
            existing.password_hash = hash_password(password)
            existing.is_active = True
            existing.email_verified_at = datetime.now(UTC)
        else:
            admin_user = User(
                email=clean_email,
                password_hash=hash_password(password),
                role="admin",
                is_active=True,
                email_verified_at=datetime.now(UTC),
            )
            db.add(admin_user)
            db.flush()

            AuditService.log(
                db,
                action="admin_created_cli",
                actor_id=admin_user.id,
                entity_type="user",
                entity_id=str(admin_user.id),
                detail={"email": clean_email},
            )

        db.commit()
        print(f"Admin user {clean_email} created successfully.")
    except Exception as e:
        db.rollback()
        print(f"Failed to create admin: {e}")
        sys.exit(1)
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Create an admin user for ProjectProof AI.")
    parser.add_argument("--email", default="admin@projectproof.ai", help="Admin email address")
    parser.add_argument("--password", default="AdminSecure2026!", help="Admin password (at least 10 chars)")
    args = parser.parse_args()

    create_admin(args.email, args.password)


if __name__ == "__main__":
    main()
