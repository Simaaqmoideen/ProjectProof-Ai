import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.core.errors import BadRequestError, ConflictError, NotFoundError
from app.models.user import Company, RecruiterProfile, User
from app.repositories.audit_repo import AuditRepository
from app.repositories.company_repo import CompanyRepository
from app.repositories.flag_repo import FlagRepository
from app.repositories.recruiter_repo import RecruiterRepository
from app.repositories.token_repo import TokenRepository
from app.repositories.user_repo import UserRepository
from app.schemas.admin import CompanyApprovalItem, RecruiterApprovalItem
from app.services.audit_service import AuditService
from app.services.company_service import CompanyService


class AdminService:
    @staticmethod
    def get_company_queue(db: Session, status: str | None = "pending") -> list[CompanyApprovalItem]:
        companies = CompanyRepository.list_by_status(db, status=status)
        results = []
        for c in companies:
            owner = CompanyRepository.get_owner_user(db, c.id)
            owner_email = owner.email if owner else None
            checks = CompanyService.compute_automated_checks(db, c, owner_email)
            results.append(
                CompanyApprovalItem(
                    id=c.id,
                    name=c.name,
                    website=c.website,
                    email_domain=c.email_domain,
                    description=c.description,
                    registration_doc_key=c.registration_doc_key,
                    status=c.status,
                    trust_score=c.trust_score,
                    created_at=c.created_at,
                    owner_email=owner_email,
                    automated_checks=checks,
                )
            )
        return results

    @staticmethod
    def approve_company(
        db: Session, admin: User, company_id: uuid.UUID, ip: str | None = None
    ) -> Company:
        """FR-ADM-1: Approve company from the queue; sets trust score to 50 (BR-6) in the same transaction."""
        company = CompanyRepository.get_by_id(db, company_id)
        if not company:
            raise NotFoundError("Company not found.")

        # BR-6: Trust score starts at 50 when approved.
        CompanyRepository.update_status(
            db=db,
            company_id=company_id,
            status="approved",
            reviewed_by=admin.id,
            trust_score=settings.trust_score_initial,
        )

        # FR-ADM-5: Audit every admin state change in the same transaction.
        AuditService.log(
            db=db,
            action="company_approved",
            actor_id=admin.id,
            entity_type="company",
            entity_id=str(company_id),
            detail={"name": company.name, "trust_score_set": settings.trust_score_initial},
            ip=ip,
        )

        db.refresh(company)
        return company

    @staticmethod
    def reject_company(
        db: Session,
        admin: User,
        company_id: uuid.UUID,
        reason: str | None = None,
        ip: str | None = None,
    ) -> Company:
        company = CompanyRepository.get_by_id(db, company_id)
        if not company:
            raise NotFoundError("Company not found.")

        CompanyRepository.update_status(
            db=db,
            company_id=company_id,
            status="rejected",
            reviewed_by=admin.id,
            rejection_reason=reason,
        )

        AuditService.log(
            db=db,
            action="company_rejected",
            actor_id=admin.id,
            entity_type="company",
            entity_id=str(company_id),
            detail={"reason": reason},
            ip=ip,
        )

        db.refresh(company)
        return company

    @staticmethod
    def suspend_company(
        db: Session,
        admin: User,
        company_id: uuid.UUID,
        reason: str | None = None,
        ip: str | None = None,
    ) -> Company:
        """FR-ADM-6: Suspend company. FR-ORG-7: Close open projects. FR-ADM-5: Audit in same transaction."""
        company = CompanyRepository.get_by_id(db, company_id)
        if not company:
            raise NotFoundError("Company not found.")

        CompanyRepository.update_status(
            db=db,
            company_id=company_id,
            status="suspended",
            reviewed_by=admin.id,
            rejection_reason=reason,
        )

        # FR-ORG-7 & T-ORG-07: Suspending a company closes its open projects. Existing certificates stay valid.
        # Close open projects in projects table if any exist

        db.execute(
            text(
                "UPDATE projects SET status = 'closed', updated_at = now() WHERE company_id = :cid AND status = 'open'"
            ),
            {"cid": company_id},
        )

        # FR-ADM-5: Audit every admin state change in the same transaction.
        AuditService.log(
            db=db,
            action="company_suspended",
            actor_id=admin.id,
            entity_type="company",
            entity_id=str(company_id),
            detail={"reason": reason},
            ip=ip,
        )

        db.refresh(company)
        return company

    @staticmethod
    def get_recruiter_queue(
        db: Session, status: str | None = "pending"
    ) -> list[RecruiterApprovalItem]:
        items = RecruiterRepository.list_by_status(db, status=status)
        return [
            RecruiterApprovalItem(
                user_id=p.user_id,
                full_name=p.full_name,
                organization=p.organization,
                work_email_domain=p.work_email_domain,
                email=u.email,
                status=p.status,
                created_at=p.created_at,
            )
            for p, u in items
        ]

    @staticmethod
    def approve_recruiter(
        db: Session, admin: User, user_id: uuid.UUID, ip: str | None = None
    ) -> RecruiterProfile:
        recruiter = RecruiterRepository.get_by_user_id(db, user_id)
        if not recruiter:
            raise NotFoundError("Recruiter not found.")

        RecruiterRepository.update_status(
            db=db,
            user_id=user_id,
            status="approved",
            reviewed_by=admin.id,
        )

        AuditService.log(
            db=db,
            action="recruiter_approved",
            actor_id=admin.id,
            entity_type="recruiter",
            entity_id=str(user_id),
            detail={"organization": recruiter.organization},
            ip=ip,
        )

        db.refresh(recruiter)
        return recruiter

    @staticmethod
    def reject_recruiter(
        db: Session,
        admin: User,
        user_id: uuid.UUID,
        reason: str | None = None,
        ip: str | None = None,
    ) -> RecruiterProfile:
        recruiter = RecruiterRepository.get_by_user_id(db, user_id)
        if not recruiter:
            raise NotFoundError("Recruiter not found.")

        RecruiterRepository.update_status(
            db=db,
            user_id=user_id,
            status="rejected",
            reviewed_by=admin.id,
            rejection_reason=reason,
        )

        AuditService.log(
            db=db,
            action="recruiter_rejected",
            actor_id=admin.id,
            entity_type="recruiter",
            entity_id=str(user_id),
            detail={"reason": reason},
            ip=ip,
        )

        db.refresh(recruiter)
        return recruiter

    @staticmethod
    def suspend_user(
        db: Session,
        admin: User,
        target_user_id: uuid.UUID,
        reason: str | None = None,
        ip: str | None = None,
    ) -> User:
        """FR-ADM-6: Suspend any user; revokes all active tokens."""
        user = UserRepository.get_by_id(db, target_user_id)
        if not user:
            raise NotFoundError("User not found.")

        UserRepository.set_active_status(db, target_user_id, is_active=False)
        TokenRepository.revoke_all_user_tokens(db, target_user_id)

        # FR-ADM-5: Audit in the same transaction.
        AuditService.log(
            db=db,
            action="user_suspended",
            actor_id=admin.id,
            entity_type="user",
            entity_id=str(target_user_id),
            detail={"reason": reason, "target_email": user.email},
            ip=ip,
        )

        db.refresh(user)
        return user

    @staticmethod
    def reactivate_user(
        db: Session,
        admin: User,
        target_user_id: uuid.UUID,
        ip: str | None = None,
    ) -> User:
        """FR-ADM-6: Reactivate a previously suspended user."""
        user = UserRepository.get_by_id(db, target_user_id)
        if not user:
            raise NotFoundError("User not found.")

        UserRepository.set_active_status(db, target_user_id, is_active=True)

        # FR-ADM-5: Audit in the same transaction.
        AuditService.log(
            db=db,
            action="user_reactivated",
            actor_id=admin.id,
            entity_type="user",
            entity_id=str(target_user_id),
            detail={"target_email": user.email},
            ip=ip,
        )

        db.refresh(user)
        return user

    @staticmethod
    def get_audit_logs(
        db: Session,
        actor_id: uuid.UUID | None = None,
        action: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows, total = AuditRepository.list_logs(
            db=db,
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size,
        )

        items = [
            {
                "id": log.id,
                "actor_id": log.actor_id,
                "actor_email": email,
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "detail": log.detail,
                "created_at": log.created_at,
            }
            for log, email in rows
        ]

        return items, total

    @staticmethod
    def resolve_flag(
        db: Session,
        admin: User,
        flag_id: uuid.UUID,
        status: str,
        note: str | None,
        ip: str | None = None,
    ) -> dict[str, str]:
        """FR-ADM-2, FR-ADM-5: Resolve a flag and audit it in the same transaction."""
        allowed = {"dismissed", "confirmed"}
        if status not in allowed:
            raise BadRequestError(f"status must be one of {allowed}")
        res = FlagRepository.resolve_open(db, flag_id, admin.id, status)
        if res.rowcount == 0:
            existing_status = FlagRepository.get_status(db, flag_id)
            if existing_status is None:
                raise NotFoundError("Flag not found.")
            raise ConflictError("Flag is already resolved.")
        AuditService.log(
            db=db,
            action="flag_resolved",
            actor_id=admin.id,
            entity_type="flag",
            entity_id=str(flag_id),
            detail={"status": status, "note": note},
            ip=ip,
        )
        return {"message": "Flag resolved.", "status": status}
