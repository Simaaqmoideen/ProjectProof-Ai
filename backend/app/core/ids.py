"""Identifier generation: verification ID, QR token, and content hash.
See docs/02-database-schema.md section 8.
"""

import hashlib
import json
import secrets
import uuid
from datetime import UTC, datetime

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no look-alikes (O, 0, I, 1)


def generate_verification_id(year: int | None = None) -> str:
    """Generate human-readable verification ID: EXP-YYYY-XXXX-NNNN.

    Format matches schema regex: ^EXP-[0-9]{4}-[A-Z0-9]{4}-[0-9]{4}$
    """
    if year is None:
        year = datetime.now().year
    part1 = "".join(secrets.choice(ALPHABET) for _ in range(4))
    part2 = "".join(str(secrets.randbelow(10)) for _ in range(4))
    return f"EXP-{year}-{part1}-{part2}"


def generate_qr_token() -> str:
    """Generate at least 128 bits of cryptographically secure randomness, URL-safe."""
    return secrets.token_urlsafe(24)


def compute_certificate_hash(
    student_id: uuid.UUID | str,
    project_id: uuid.UUID | str,
    company_id: uuid.UUID | str,
    completed_at: datetime | str,
    skills: list[str],
    overall_score: int,
) -> str:
    if isinstance(completed_at, str):
        try:
            dt = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
            if dt.tzinfo is not None:
                completed_at_utc = dt.astimezone(UTC)
            else:
                completed_at_utc = dt.replace(tzinfo=UTC)
            completed_at_str = completed_at_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            completed_at_str = str(completed_at)
    elif isinstance(completed_at, datetime):
        if completed_at.tzinfo is not None:
            completed_at_utc = completed_at.astimezone(UTC)
        else:
            completed_at_utc = completed_at.replace(tzinfo=UTC)
        completed_at_str = completed_at_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        completed_at_str = str(completed_at)

    canonical = {
        "student_id": str(student_id),
        "project_id": str(project_id),
        "company_id": str(company_id),
        "completed_at": completed_at_str,
        "skills": sorted(skills),
        "overall_score": overall_score,
    }
    raw = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
