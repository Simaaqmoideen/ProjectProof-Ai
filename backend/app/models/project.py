import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    Text,
)
from sqlalchemy.dialects.postgresql import CITEXT, ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db import Base

DifficultyLevelEnum = ENUM(
    "beginner", "intermediate", "advanced", name="difficulty_level", create_type=False
)
ProjectCategoryEnum = ENUM(
    "development", "data", "design", "other", name="project_category", create_type=False
)
ProjectStatusEnum = ENUM(
    "draft", "open", "closed", "cancelled", "removed", name="project_status", create_type=False
)


SkillSourceEnum = ENUM("self", "resume", "verified_project", name="skill_source", create_type=False)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(
        ProjectCategoryEnum, default="development", nullable=False
    )
    difficulty: Mapped[str] = mapped_column(DifficultyLevelEnum, nullable=False)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    xp_max: Mapped[int] = mapped_column(Integer, nullable=False)
    max_selected: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    application_deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(
        ProjectStatusEnum, default="draft", nullable=False, index=True
    )
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    removed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    removal_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    company = relationship("Company")
    milestones: Mapped[list["Milestone"]] = relationship(
        "Milestone",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="Milestone.position",
    )
    skills: Mapped[list["Skill"]] = relationship("Skill", secondary="project_skills")


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(CITEXT, unique=True, nullable=False)
    category: Mapped[str | None] = mapped_column(Text, nullable=True)


class ProjectSkill(Base):
    __tablename__ = "project_skills"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[int] = mapped_column(Integer, ForeignKey("skills.id"), primary_key=True)


class StudentSkill(Base):
    __tablename__ = "student_skills"

    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_profiles.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    skill_id: Mapped[int] = mapped_column(Integer, ForeignKey("skills.id"), primary_key=True)
    proficiency: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    source: Mapped[str] = mapped_column(SkillSourceEnum, default="self", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    skill = relationship("Skill")


class Milestone(Base):
    __tablename__ = "milestones"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_day_offset: Mapped[int] = mapped_column(Integer, nullable=False)

    project = relationship("Project", back_populates="milestones")
    tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="milestone", cascade="all, delete-orphan", order_by="Task.position"
    )


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    milestone_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("milestones.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    application_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=True
    )
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    milestone = relationship("Milestone", back_populates="tasks")
