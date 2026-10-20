import hashlib
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.repositories.audit_repo import AuditRepository


class AuditService:
    @staticmethod
    def hash_ip(ip: str | None) -> str | None:
        if not ip:
            return None
        return hashlib.sha256(ip.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def log(
        cls,
        db: Session,
        action: str,
        actor_id: uuid.UUID | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        detail: dict[str, Any] | None = None,
        ip: str | None = None,
    ) -> AuditLog:
        """Writes an audit log entry in the current database transaction (NFR-4)."""
        ip_hash = cls.hash_ip(ip)
        return AuditRepository.create_log(
            db=db,
            action=action,
            actor_id=actor_id,
            entity_type=entity_type,
            entity_id=entity_id,
            detail=detail,
            ip_hash=ip_hash,
        )
