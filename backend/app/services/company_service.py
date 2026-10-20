from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.core.errors import ConflictError, ForbiddenError, NotFoundError
from app.models.user import Company, User
from app.repositories.company_repo import CompanyRepository
from app.schemas.admin import AutomatedCompanyChecks
from app.services.audit_service import AuditService

FREE_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com",
    "mail.com", "protonmail.com", "zoho.com", "aol.com",
}


def normalize_domain(domain_or_url: str | None) -> str | None:
    if not domain_or_url:
        return None
    val = domain_or_url.strip().lower()
    if "://" not in val:
        val = "http://" + val
    try:
        parsed = urlparse(val)
        host = parsed.netloc or parsed.path
        host = host.split(":")[0]  # remove port if any
        host = host.removeprefix("www.")
        return host if host else None
    except Exception:
        return None


def extract_email_domain(email: str) -> str:
    parts = email.strip().lower().split("@")
    return parts[1] if len(parts) > 1 else ""


class CompanyService:
    @staticmethod
    def compute_automated_checks(db: Session, company: Company, owner_email: str | None = None) -> AutomatedCompanyChecks:
        email_domain = (company.email_domain or "").lower()
        if not email_domain and owner_email:
            email_domain = extract_email_domain(owner_email)

        website_domain = normalize_domain(company.website)
        domain_matches_website = False
        if website_domain and email_domain:
            domain_matches_website = (website_domain == email_domain) or (email_domain.endswith("." + website_domain))

        doc_uploaded = bool(company.registration_doc_key and company.registration_doc_key.strip())

        # Check domain conflicts
        other_companies = []
        if email_domain:
            other_companies = CompanyRepository.get_by_domain(db, email_domain, exclude_company_id=company.id)
        domain_conflict = len(other_companies) > 0

        is_free = email_domain in FREE_EMAIL_DOMAINS

        return AutomatedCompanyChecks(
            domain_matches_website=domain_matches_website,
            document_uploaded=doc_uploaded,
            domain_conflict=domain_conflict,
            is_free_email=is_free,
        )

    @classmethod
    def register_company(
        cls,
        db: Session,
        user: User,
        name: str,
        website: str | None = None,
        description: str | None = None,
        registration_doc_key: str | None = None,
        ip: str | None = None,
    ) -> Company:
        if user.role != "company":
            raise ForbiddenError("Only users with company role can register a company profile.")

        # Check if this user already belongs to a company
        existing_membership = CompanyRepository.get_membership(db, user.id)
        if existing_membership:
            raise ConflictError("You are already associated with a company profile.")

        email_domain = extract_email_domain(user.email)

        # T-ORG-03: Second company registers with an active company's domain -> rejected
        if email_domain:
            active_companies_on_domain = CompanyRepository.get_by_domain(db, email_domain)
            if active_companies_on_domain:
                raise ConflictError("Another active company is already registered with this domain.")

        # BR-6: Trust score starts at 50 *when approved*. It is 0 here so the
        # automated-checks display is informational only and does not set the score.
        # The score is set to settings.trust_score_initial (50) inside approve_company().
        company = CompanyRepository.create_company(
            db=db,
            name=name.strip(),
            website=website.strip() if website else None,
            email_domain=email_domain,
            description=description.strip() if description else None,
            registration_doc_key=registration_doc_key,
            trust_score=0,
            status="pending",
        )

        CompanyRepository.add_member(
            db=db,
            company_id=company.id,
            user_id=user.id,
            member_role="owner",
        )

        # FR-ADM-5: Every company state change writes an audit_log row in the same transaction.
        AuditService.log(
            db,
            action="company_registered",
            actor_id=user.id,
            entity_type="company",
            entity_id=str(company.id),
            detail={"name": company.name, "domain": email_domain},
            ip=ip,
        )

        return company

    @staticmethod
    def get_company_by_user(db: Session, user: User) -> Company:
        company = CompanyRepository.get_by_user_id(db, user.id)
        if not company:
            raise NotFoundError("Company profile not found.")
        return company

    @staticmethod
    def update_company(
        db: Session,
        user: User,
        description: str | None = None,
        website: str | None = None,
        ip: str | None = None,
    ) -> Company:
        company = CompanyRepository.get_by_user_id(db, user.id)
        if not company:
            raise NotFoundError("Company profile not found.")

        CompanyRepository.update_profile(
            db=db,
            company_id=company.id,
            description=description,
            website=website,
        )

        AuditService.log(
            db,
            action="company_updated",
            actor_id=user.id,
            entity_type="company",
            entity_id=str(company.id),
            detail={"website": website, "description_updated": description is not None},
            ip=ip,
        )

        db.refresh(company)
        return company
