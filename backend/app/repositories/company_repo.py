import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.user import Company, CompanyMember, User


class CompanyRepository:
    @staticmethod
    def get_by_id(db: Session, company_id: uuid.UUID) -> Company | None:
        stmt = select(Company).where(Company.id == company_id)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_by_user_id(db: Session, user_id: uuid.UUID) -> Company | None:
        stmt = (
            select(Company)
            .join(CompanyMember, CompanyMember.company_id == Company.id)
            .where(CompanyMember.user_id == user_id)
        )
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_membership(db: Session, user_id: uuid.UUID) -> CompanyMember | None:
        stmt = select(CompanyMember).where(CompanyMember.user_id == user_id)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_by_domain(
        db: Session, domain: str, exclude_company_id: uuid.UUID | None = None
    ) -> list[Company]:
        stmt = select(Company).where(
            Company.email_domain == domain.strip().lower(),
            Company.status != "rejected",
        )
        if exclude_company_id:
            stmt = stmt.where(Company.id != exclude_company_id)
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def create_company(
        db: Session,
        name: str,
        website: str | None,
        email_domain: str | None,
        description: str | None,
        registration_doc_key: str | None,
        trust_score: int = 0,
        status: str = "pending",
    ) -> Company:
        company = Company(
            name=name,
            website=website,
            email_domain=email_domain.strip().lower() if email_domain else None,
            description=description,
            registration_doc_key=registration_doc_key,
            trust_score=trust_score,
            status=status,
        )
        db.add(company)
        db.flush()
        return company

    @staticmethod
    def add_member(
        db: Session,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
        member_role: str = "owner",
    ) -> CompanyMember:
        member = CompanyMember(
            company_id=company_id,
            user_id=user_id,
            member_role=member_role,
        )
        db.add(member)
        db.flush()
        return member

    @staticmethod
    def update_profile(
        db: Session,
        company_id: uuid.UUID,
        description: str | None = None,
        website: str | None = None,
    ) -> None:
        values = {}
        if description is not None:
            values["description"] = description
        if website is not None:
            values["website"] = website
        if values:
            stmt = update(Company).where(Company.id == company_id).values(**values)
            db.execute(stmt)

    @staticmethod
    def update_status(
        db: Session,
        company_id: uuid.UUID,
        status: str,
        reviewed_by: uuid.UUID | None = None,
        rejection_reason: str | None = None,
        trust_score: int | None = None,
    ) -> None:
        """Parameterised update — no string concatenation (AGENTS.md rule 5)."""
        values: dict = {
            "status": status,
            "reviewed_by": reviewed_by,
            "reviewed_at": datetime.now(UTC),
            "rejection_reason": rejection_reason,
        }
        # BR-6: trust_score is only updated when the admin explicitly approves.
        if trust_score is not None:
            values["trust_score"] = trust_score
        stmt = update(Company).where(Company.id == company_id).values(**values)
        db.execute(stmt)

    @staticmethod
    def list_by_status(db: Session, status: str | None = None) -> list[Company]:
        stmt = select(Company)
        if status:
            stmt = stmt.where(Company.status == status)
        stmt = stmt.order_by(Company.created_at.desc())
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def get_owner_user(db: Session, company_id: uuid.UUID) -> User | None:
        stmt = (
            select(User)
            .join(CompanyMember, CompanyMember.user_id == User.id)
            .where(CompanyMember.company_id == company_id, CompanyMember.member_role == "owner")
        )
        return db.execute(stmt).scalar_one_or_none()
