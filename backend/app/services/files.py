"""Private local file storage and resume processing."""

import io
import uuid
from pathlib import Path

from pypdf import PdfReader
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.core.errors import BadRequestError, NotFoundError


def upload_resume(db: Session, user_id: uuid.UUID, filename: str, content: bytes) -> dict[str, str]:
    """Validate, privately store, and associate a resume PDF with its owner."""
    if not filename.lower().endswith(".pdf") or not content.startswith(b"%PDF-"):
        raise BadRequestError("Only valid PDF files are accepted.")
    if len(content) > settings.max_resume_bytes:
        raise BadRequestError(f"Resume must be <= {settings.max_resume_bytes // (1024 * 1024)} MB.")

    key = f"resumes/{uuid.uuid4().hex}.pdf"
    root = Path(settings.upload_dir).resolve()
    destination = (root / key).resolve()
    if not destination.is_relative_to(root):
        raise BadRequestError("Invalid resume storage key.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)
    try:
        updated = db.execute(
            text("UPDATE student_profiles SET resume_file_key = :key WHERE user_id = :uid"),
            {"key": key, "uid": user_id},
        )
        if updated.rowcount == 0:
            raise NotFoundError("Student profile not found.")
        db.commit()
    except Exception:
        destination.unlink(missing_ok=True)
        db.rollback()
        raise
    return {"message": "Resume uploaded successfully.", "resume_url": key, "resume_file_key": key}


def extract_my_resume_text(db: Session, user_id: uuid.UUID) -> dict[str, str]:
    """Extract bounded text from the current student's stored resume PDF."""
    key = db.execute(
        text("SELECT resume_file_key FROM student_profiles WHERE user_id = :uid"),
        {"uid": user_id},
    ).scalar_one_or_none()
    if not key:
        raise NotFoundError("Resume not found.")
    root = Path(settings.upload_dir).resolve()
    path = (root / key).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise NotFoundError("Resume not found.")
    try:
        reader = PdfReader(io.BytesIO(path.read_bytes()))
        text_content = " ".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        raise BadRequestError("The uploaded PDF could not be read.") from exc
    return {"text": text_content[: settings.ai_max_resume_chars]}
