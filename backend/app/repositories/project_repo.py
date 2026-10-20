"""Project repository — parameterised queries only (AGENTS.md rule 5)."""
import uuid
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.project import Milestone, Project, ProjectSkill, Skill, Task


class ProjectRepository:
    @staticmethod
    def get_by_id(db: Session, project_id: uuid.UUID) -> Project | None:
        return db.execute(select(Project).where(Project.id == project_id)).scalar_one_or_none()

    @staticmethod
    def get_company_project(
        db: Session, project_id: uuid.UUID, company_id: uuid.UUID
    ) -> Project | None:
        return db.execute(
            select(Project).where(
                Project.id == project_id,
                Project.company_id == company_id,
            )
        ).scalar_one_or_none()

    @staticmethod
    def list_open(
        db: Session,
        category: str | None = None,
        difficulty: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Project], int]:
        stmt = select(Project).where(Project.status == "open")
        if category:
            stmt = stmt.where(Project.category == category)
        if difficulty:
            stmt = stmt.where(Project.difficulty == difficulty)
        if search:
            # Parameterised ILIKE — no concatenation
            stmt = stmt.where(Project.title.ilike(f"%{search}%"))
        total_stmt = select(func.count()).select_from(stmt.subquery())
        total = db.execute(total_stmt).scalar_one()
        stmt = stmt.order_by(Project.published_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        return list(db.execute(stmt).scalars().all()), total

    @staticmethod
    def count_open_for_company(db: Session, company_id: uuid.UUID) -> int:
        return db.execute(
            select(func.count(Project.id)).where(
                Project.company_id == company_id,
                Project.status == "open",
            )
        ).scalar_one()

    @staticmethod
    def list_for_company(
        db: Session,
        company_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Project], int]:
        stmt = select(Project).where(Project.company_id == company_id)
        total_stmt = select(func.count()).select_from(stmt.subquery())
        total = db.execute(total_stmt).scalar_one()
        stmt = stmt.order_by(Project.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        return list(db.execute(stmt).scalars().all()), total

    @staticmethod
    def update_project(
        db: Session,
        project_id: uuid.UUID,
        **fields,
    ) -> None:
        """Parameterised update. Only set provided fields."""
        if not fields:
            return
        stmt = (
            update(Project)
            .where(Project.id == project_id)
            .values(**fields)
        )
        db.execute(stmt)

    @staticmethod
    def set_status(
        db: Session,
        project_id: uuid.UUID,
        status: str,
        published_at: datetime | None = None,
    ) -> None:
        values = {"status": status}
        if published_at is not None:
            values["published_at"] = published_at
        db.execute(update(Project).where(Project.id == project_id).values(**values))

    # ── Skill helpers ────────────────────────────────────────────────────────

    @staticmethod
    def get_or_create_skill(db: Session, name: str) -> "Skill":
        """Case-insensitive lookup via CITEXT column; create if absent."""
        skill = db.execute(
            select(Skill).where(Skill.name == name.strip())
        ).scalar_one_or_none()
        if not skill:
            skill = Skill(name=name.strip())
            db.add(skill)
            db.flush()
        return skill

    @staticmethod
    def replace_skills(db: Session, project_id: uuid.UUID, skill_names: list[str]) -> None:
        # Remove existing
        db.execute(
            ProjectSkill.__table__.delete().where(
                ProjectSkill.project_id == project_id
            )
        )
        for name in skill_names:
            skill = ProjectRepository.get_or_create_skill(db, name)
            db.add(ProjectSkill(project_id=project_id, skill_id=skill.id))

    @staticmethod
    def get_skill_names(db: Session, project_id: uuid.UUID) -> list[str]:
        rows = db.execute(
            select(Skill.name)
            .join(ProjectSkill, ProjectSkill.skill_id == Skill.id)
            .where(ProjectSkill.project_id == project_id)
        ).scalars().all()
        return list(rows)

    # ── Milestone helpers ─────────────────────────────────────────────────────

    @staticmethod
    def replace_milestones(
        db: Session,
        project_id: uuid.UUID,
        milestone_data: list[dict],
    ) -> list[Milestone]:
        """Delete-and-replace milestones (draft only). milestone_data is a
        list of dicts matching MilestoneCreate fields plus a 'tasks' list."""
        # Delete existing
        db.execute(
            Milestone.__table__.delete().where(Milestone.project_id == project_id)
        )
        db.flush()
        created = []
        for m in milestone_data:
            ms = Milestone(
                project_id=project_id,
                position=m["position"],
                title=m["title"],
                description=m.get("description"),
                due_day_offset=m["due_day_offset"],
            )
            db.add(ms)
            db.flush()
            for pos, t in enumerate(m.get("tasks", []), start=1):
                db.add(Task(
                    milestone_id=ms.id,
                    position=pos,
                    title=t["title"],
                    description=t.get("description"),
                ))
            created.append(ms)
        return created
