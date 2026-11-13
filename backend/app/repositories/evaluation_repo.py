"""Evaluation repository: submissions, evaluations, and appeals.
See AGENTS.md rule 5 and docs/02-database-schema.md.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.orm import Session


class EvaluationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_submission_count(self, application_id: uuid.UUID) -> int:
        """Get number of existing submission versions for application."""
        count = self.db.execute(
            text("SELECT count(id) FROM submissions WHERE application_id = :app_id"),
            {"app_id": application_id},
        ).scalar()
        return count or 0

    def get_latest_submission_version(self, application_id: uuid.UUID) -> int:
        version = self.db.execute(
            text(
                "SELECT COALESCE(MAX(version), 0) FROM submissions WHERE application_id = :app_id"
            ),
            {"app_id": application_id},
        ).scalar()
        return version or 0

    def create_submission(
        self,
        application_id: uuid.UUID,
        version: int,
        repo_url: str | None,
        file_key: str | None,
        notes: str | None,
    ) -> uuid.UUID:
        sub_id = uuid.uuid4()
        now = datetime.now(UTC)
        self.db.execute(
            text("""
                INSERT INTO submissions (id, application_id, version, repo_url, file_key, notes, submitted_at)
                VALUES (:id, :app_id, :version, :repo_url, :file_key, :notes, :now)
            """),
            {
                "id": sub_id,
                "app_id": application_id,
                "version": version,
                "repo_url": repo_url,
                "file_key": file_key,
                "notes": notes,
                "now": now,
            },
        )
        # Update application status to 'submitted'
        self.db.execute(
            text("""
                UPDATE applications
                SET status = 'submitted', updated_at = :now
                WHERE id = :app_id
            """),
            {"app_id": application_id, "now": now},
        )
        return sub_id

    def get_submission(self, submission_id: uuid.UUID) -> dict | None:
        row = (
            self.db.execute(
                text("""
                SELECT s.id, s.application_id, s.version, s.repo_url, s.file_key, s.notes,
                       s.similarity_score, s.similarity_report, s.ai_prereview, s.submitted_at,
                       a.student_id, a.project_id, p.company_id
                FROM submissions s
                JOIN applications a ON a.id = s.application_id
                JOIN projects p ON p.id = a.project_id
                WHERE s.id = :sub_id
            """),
                {"sub_id": submission_id},
            )
            .mappings()
            .fetchone()
        )
        return dict(row) if row else None

    def get_evaluation_by_submission(self, submission_id: uuid.UUID) -> dict | None:
        row = (
            self.db.execute(
                text("""
                SELECT id, submission_id, reviewer_id, rubric_scores, overall_score,
                       feedback, public_summary, used_ai_draft, decision, evaluated_at
                FROM evaluations
                WHERE submission_id = :sub_id
            """),
                {"sub_id": submission_id},
            )
            .mappings()
            .fetchone()
        )
        return dict(row) if row else None

    def get_evaluation(self, evaluation_id: uuid.UUID) -> dict | None:
        row = (
            self.db.execute(
                text("""
                SELECT e.id, e.submission_id, e.reviewer_id, e.rubric_scores, e.overall_score,
                       e.feedback, e.public_summary, e.used_ai_draft, e.decision, e.evaluated_at,
                       s.application_id, a.student_id, p.company_id
                FROM evaluations e
                JOIN submissions s ON s.id = e.submission_id
                JOIN applications a ON a.id = s.application_id
                JOIN projects p ON p.id = a.project_id
                WHERE e.id = :eval_id
            """),
                {"eval_id": evaluation_id},
            )
            .mappings()
            .fetchone()
        )
        return dict(row) if row else None

    def create_evaluation(
        self,
        submission_id: uuid.UUID,
        reviewer_id: uuid.UUID,
        rubric_scores: dict | None,
        overall_score: int,
        feedback: str,
        public_summary: str | None,
        used_ai_draft: bool,
        decision: str,
    ) -> uuid.UUID:
        eval_id = uuid.uuid4()
        import json

        rubric_json = json.dumps(rubric_scores) if rubric_scores else None
        self.db.execute(
            text("""
                INSERT INTO evaluations (
                    id, submission_id, reviewer_id, rubric_scores, overall_score,
                    feedback, public_summary, used_ai_draft, decision, evaluated_at
                ) VALUES (
                    :id, :sub_id, :reviewer_id, :rubric_scores, :overall_score,
                    :feedback, :public_summary, :used_ai_draft, :decision, now()
                )
            """),
            {
                "id": eval_id,
                "sub_id": submission_id,
                "reviewer_id": reviewer_id,
                "rubric_scores": rubric_json,
                "overall_score": overall_score,
                "feedback": feedback,
                "public_summary": public_summary,
                "used_ai_draft": used_ai_draft,
                "decision": decision,
            },
        )
        return eval_id

    def update_application_status(self, application_id: uuid.UUID, status: str) -> None:
        self.db.execute(
            text("UPDATE applications SET status = :status, updated_at = now() WHERE id = :app_id"),
            {"app_id": application_id, "status": status},
        )

    def get_open_appeal_for_evaluation(self, evaluation_id: uuid.UUID) -> dict | None:
        row = (
            self.db.execute(
                text(
                    "SELECT id, evaluation_id, status FROM appeals WHERE evaluation_id = :eval_id AND status = 'open'"
                ),
                {"eval_id": evaluation_id},
            )
            .mappings()
            .fetchone()
        )
        return dict(row) if row else None

    def create_appeal(
        self, evaluation_id: uuid.UUID, student_id: uuid.UUID, reason: str
    ) -> uuid.UUID:
        appeal_id = uuid.uuid4()
        self.db.execute(
            text("""
                INSERT INTO appeals (id, evaluation_id, student_id, reason, status, created_at)
                VALUES (:id, :eval_id, :student_id, :reason, 'open', now())
            """),
            {
                "id": appeal_id,
                "eval_id": evaluation_id,
                "student_id": student_id,
                "reason": reason,
            },
        )
        return appeal_id
