from sqlalchemy.orm import Session

from app.core.errors import ConflictError, ForbiddenError, NotFoundError
from app.models.user import RecruiterProfile, User
from app.repositories.recruiter_repo import RecruiterRepository
from app.services.audit_service import AuditService
from app.services.company_service import extract_email_domain


class RecruiterService:
    @staticmethod
    def register_recruiter(
        db: Session,
        user: User,
        full_name: str,
        organization: str,
        ip: str | None = None,
    ) -> RecruiterProfile:
        if user.role != "recruiter":
            raise ForbiddenError("Only users with recruiter role can complete recruiter registration.")

        existing = RecruiterRepository.get_by_user_id(db, user.id)
        if existing:
            raise ConflictError("Recruiter profile already registered.")

        work_domain = extract_email_domain(user.email)

        profile = RecruiterRepository.create_profile(
            db=db,
            user_id=user.id,
            full_name=full_name.strip(),
            organization=organization.strip(),
            work_email_domain=work_domain,
            status="pending",
        )

        AuditService.log(
            db,
            action="recruiter_registered",
            actor_id=user.id,
            entity_type="recruiter",
            entity_id=str(user.id),
            detail={"organization": organization, "domain": work_domain},
            ip=ip,
        )

        return profile

    @staticmethod
    def get_profile(db: Session, user: User) -> RecruiterProfile:
        profile = RecruiterRepository.get_by_user_id(db, user.id)
        if not profile:
            raise NotFoundError("Recruiter profile not found.")
        return profile
