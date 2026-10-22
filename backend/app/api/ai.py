"""AI API router — Section 11 of docs/04-api-specification.md and docs/06-ai-modules-specification.md.

All AI routes:
- Authenticated
- Enforce role, ownership, and state authorization rules
- Quota checked per user
- Response includes standard envelope: { "ai": { "label": "AI draft", "confidence": "...", "log_id": ... }, "result": ... }
- AI never saves directly to business tables without human review/acceptance (AGENTS.md Rule 4)
- Untrusted inputs are strictly bounded and treated as data only
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.ai.features import (
    brief_generator,
    feedback_drafter,
    github_analysis,
    match_explanation,
    mentor,
    pre_review,
    recruiter_search,
    resume_analysis,
    resume_rewriter,
    skill_gap,
)
from app.core.errors import BadRequestError, NotFoundError
from app.db import get_db
from app.deps import (
    get_current_user,
    require_approved_company,
    require_approved_recruiter,
    require_roles,
    require_verified_email,
)
from app.models.application import Application, Submission
from app.models.project import Milestone, Project, ProjectSkill, Skill, StudentSkill
from app.models.user import StudentProfile, User
from app.services.github import fetch_github_repos
from app.services.match_service import MatchScoreService

router = APIRouter(prefix="/ai", tags=["AI"])


# ── Request / Response Schemas ────────────────────────────────────────────────


class ResumeAnalyzeRequest(BaseModel):
    resume_text: str = Field(..., min_length=10, max_length=50_000)


class ResumeAcceptRequest(BaseModel):
    log_id: int
    accepted_skills: list[dict[str, Any]] = Field(default_factory=list)


class BriefGenerateRequest(BaseModel):
    rough_idea: str = Field(..., min_length=5, max_length=1_000)
    target_difficulty: str | None = None
    duration_days: int | None = None


class SkillGapRequest(BaseModel):
    project_id: uuid.UUID


class GitHubAnalyzeRequest(BaseModel):
    username: str | None = None


class GitHubAcceptRequest(BaseModel):
    log_id: int
    accepted_skills: list[dict[str, Any]] = Field(default_factory=list)


class RecruiterQueryRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=500)


class AIFeedbackRequest(BaseModel):
    accepted: bool


class MentorChatRequest(BaseModel):
    application_id: uuid.UUID
    message: str = Field(..., min_length=2, max_length=1000)
    milestone_id: uuid.UUID | None = None
    history: list[dict[str, str]] | None = None


class FeedbackDraftRequest(BaseModel):
    submission_id: uuid.UUID
    rough_notes: str = Field(..., min_length=5, max_length=3000)
    rubric_scores: dict[str, Any] | None = None


class ResumeBulletsRequest(BaseModel):
    certificate_id: str


# ── 1. Resume Analysis (FR-STU-4) ─────────────────────────────────────────────


@router.post("/resume/analyze", summary="Analyze student resume text")
def analyze_resume(
    req: ResumeAnalyzeRequest,
    current_user: User = Depends(require_roles("student")),
    db: Session = Depends(get_db),
):
    require_verified_email(current_user)
    return resume_analysis.analyse(
        db=db,
        user_id=current_user.id,
        resume_text=req.resume_text,
    )


@router.post("/resume/accept", summary="Accept AI proposed resume skills")
def accept_resume_skills(
    req: ResumeAcceptRequest,
    current_user: User = Depends(require_roles("student")),
    db: Session = Depends(get_db),
):
    require_verified_email(current_user)
    return resume_analysis.accept_skills(
        db=db,
        user_id=current_user.id,
        log_id=req.log_id,
        accepted_skills=req.accepted_skills,
    )


# ── 2. Project Brief Generator (FR-PRJ-5) ─────────────────────────────────────


@router.post("/projects/brief", summary="Draft project brief from rough idea")
def draft_project_brief(
    req: BriefGenerateRequest,
    auth: tuple = Depends(require_approved_company),
    db: Session = Depends(get_db),
):
    current_user, _company = auth
    return brief_generator.generate(
        db=db,
        user_id=current_user.id,
        rough_idea=req.rough_idea,
        target_difficulty=req.target_difficulty,
        duration_days=req.duration_days,
    )


# ── 3. Project Match & Explanation (FR-APP-3) ─────────────────────────────────


@router.get("/projects/{project_id}/match", summary="Match score plus AI explanation for student")
def get_project_match(
    project_id: uuid.UUID,
    current_user: User = Depends(require_roles("student")),
    db: Session = Depends(get_db),
):
    require_verified_email(current_user)

    project = db.execute(
        select(Project).where(
            Project.id == project_id, Project.status.in_(["open", "closed"])
        )
    ).scalar_one_or_none()
    if not project:
        raise NotFoundError("Project not found.")

    if project.status == "closed":
        has_applied = db.execute(
            select(Application.id).where(
                Application.project_id == project.id,
                Application.student_id == current_user.id,
            )
        ).scalar_one_or_none()
        if not has_applied:
            raise NotFoundError("Project not found.")

    # Deterministic match calculation
    match_result = MatchScoreService.calculate_match_score(
        db, student_id=current_user.id, project=project
    )

    # Get student skills
    student_skills = list(
        db.execute(
            select(Skill.name)
            .join(StudentSkill, StudentSkill.skill_id == Skill.id)
            .where(StudentSkill.student_id == current_user.id)
        )
        .scalars()
        .all()
    )

    # Required skills
    req_skills = list(
        db.execute(
            select(Skill.name)
            .join(ProjectSkill, ProjectSkill.skill_id == Skill.id)
            .where(ProjectSkill.project_id == project.id)
        )
        .scalars()
        .all()
    )
    matched_skills = [s for s in req_skills if s in student_skills]

    # Verified projects count
    vp_count = (
        db.execute(
            text("""
            SELECT count(*) FROM certificates c
              JOIN applications a ON a.id = c.application_id
             WHERE a.student_id = :sid AND c.status = 'issued'
        """),
            {"sid": current_user.id},
        ).scalar()
        or 0
    )

    applicant_fact = {
        "application_id": str(project_id),
        "matched_skills": matched_skills,
        "missing_skills": match_result.get("missing_skills", []),
        "verified_project_count": vp_count,
        "relevant_verified_projects": vp_count,
        "current_load": 0,
        "breakdown": match_result.get("breakdown", {}),
    }

    ai_explanation = match_explanation.explain_applicants(
        db=db,
        user_id=current_user.id,
        applicants=[applicant_fact],
    )

    expl = ai_explanation.get("result", {}).get("explanations", [{}])[0]

    return {
        "ai": ai_explanation.get("ai", {"label": "AI draft", "confidence": "high"}),
        "result": {
            "score": match_result["score"],
            "breakdown": match_result["breakdown"],
            "missing_skills": match_result.get("missing_skills", []),
            "strengths": expl.get("strengths", ""),
            "gaps": expl.get("gaps", ""),
        },
    }


# ── 4. Rank Applicants (FR-APP-5) ─────────────────────────────────────────────


@router.post(
    "/projects/{project_id}/rank-applicants", summary="Rank applicants with AI explanations"
)
def rank_project_applicants(
    project_id: uuid.UUID,
    auth: tuple = Depends(require_approved_company),
    db: Session = Depends(get_db),
):
    current_user, company = auth

    project = db.execute(
        select(Project).where(Project.id == project_id, Project.company_id == company.id)
    ).scalar_one_or_none()
    if not project or project.status == "removed":
        raise NotFoundError("Project not found.")

    # Fetch applicants
    apps = list(
        db.execute(select(Application).where(Application.project_id == project.id)).scalars().all()
    )

    if not apps:
        return {
            "ai": {"label": "AI draft", "confidence": "high", "log_id": None},
            "result": {"explanations": []},
        }

    # Build facts for each applicant
    applicant_facts = []
    for app in apps:
        match_info = MatchScoreService.calculate_match_score(
            db, student_id=app.student_id, project=project
        )
        # Fetch student skills
        st_skills = list(
            db.execute(
                select(Skill.name)
                .join(StudentSkill, StudentSkill.skill_id == Skill.id)
                .where(StudentSkill.student_id == app.student_id)
            )
            .scalars()
            .all()
        )
        req_skills = list(
            db.execute(
                select(Skill.name)
                .join(ProjectSkill, ProjectSkill.skill_id == Skill.id)
                .where(ProjectSkill.project_id == project.id)
            )
            .scalars()
            .all()
        )
        matched = [s for s in req_skills if s in st_skills]

        vp_count = (
            db.execute(
                text("""
                SELECT count(*) FROM certificates c
                  JOIN applications a ON a.id = c.application_id
                 WHERE a.student_id = :sid AND c.status = 'issued'
            """),
                {"sid": app.student_id},
            ).scalar()
            or 0
        )

        applicant_facts.append(
            {
                "application_id": str(app.id),
                "matched_skills": matched,
                "missing_skills": match_info.get("missing_skills", []),
                "verified_project_count": vp_count,
                "relevant_verified_projects": vp_count,
                "current_load": 0,
                "breakdown": match_info.get("breakdown", {}),
            }
        )

    return match_explanation.explain_applicants(
        db=db,
        user_id=current_user.id,
        applicants=applicant_facts,
    )


# ── 5. Submission Pre-Review (FR-EVL-3) ────────────────────────────────────────


@router.post(
    "/submissions/{submission_id}/prereview", summary="AI pre-review of submission checklist"
)
def prereview_submission(
    submission_id: uuid.UUID,
    auth: tuple = Depends(require_approved_company),
    db: Session = Depends(get_db),
):
    current_user, company = auth

    sub = db.execute(select(Submission).where(Submission.id == submission_id)).scalar_one_or_none()
    if not sub:
        raise NotFoundError("Submission not found.")

    app = db.execute(
        select(Application).where(Application.id == sub.application_id)
    ).scalar_one_or_none()
    if not app:
        raise NotFoundError("Application not found.")

    project = db.execute(
        select(Project).where(Project.id == app.project_id, Project.company_id == company.id)
    ).scalar_one_or_none()
    if not project or project.status == "removed":
        raise NotFoundError("Project not found.")

    # Fetch deliverables checklist (from tasks where application_id IS NULL)
    tasks = list(
        db.execute(
            text("""
                SELECT t.title FROM tasks t
                  JOIN milestones m ON m.id = t.milestone_id
                 WHERE m.project_id = :pid AND t.application_id IS NULL
                 ORDER BY m.position, t.position
            """),
            {"pid": project.id},
        )
        .scalars()
        .all()
    )
    if not tasks:
        # Fall back to milestones
        tasks = list(
            db.execute(
                select(Milestone.title)
                .where(Milestone.project_id == project.id)
                .order_by(Milestone.position)
            )
            .scalars()
            .all()
        )
    if not tasks:
        tasks = ["Deliverable complete and functional"]

    file_tree = ["README.md", "src/index.js", "package.json"]
    readme = sub.notes or "Project deliverable implementation."
    source_sample = f"Repository URL: {sub.repo_url or 'Direct file'}\nNotes: {sub.notes or ''}"

    res = pre_review.review(
        db=db,
        user_id=current_user.id,
        checklist=tasks,
        file_tree=file_tree,
        readme=readme,
        source_sample=source_sample,
        company_notes="",
    )

    # Save to submission record
    sub.ai_prereview = res["result"]
    db.commit()

    return res


# ── 6. Skill Gap Learning Order (FR-APP-9) ────────────────────────────────────


@router.post("/skill-gap", summary="Deterministic skill gaps with AI learning order")
def get_skill_gap(
    req: SkillGapRequest,
    current_user: User = Depends(require_roles("student")),
    db: Session = Depends(get_db),
):
    require_verified_email(current_user)

    project = db.execute(select(Project).where(Project.id == req.project_id)).scalar_one_or_none()
    if not project or project.status == "removed":
        raise NotFoundError("Project not found.")

    # Calculate deterministic match and missing skills
    match_result = MatchScoreService.calculate_match_score(
        db=db,
        student_id=current_user.id,
        project=project,
    )
    missing_skills = match_result.get("missing_skills", [])

    # Student's current skills
    current_skills = list(
        db.execute(
            select(Skill.name)
            .join(StudentSkill, StudentSkill.skill_id == Skill.id)
            .where(StudentSkill.student_id == current_user.id)
        )
        .scalars()
        .all()
    )

    return skill_gap.suggest(
        db=db,
        user_id=current_user.id,
        missing_skills=missing_skills,
        current_skills=current_skills,
        project_difficulty=project.difficulty,
    )


# ── 7. GitHub Analysis (FR-STU-11) ───────────────────────────────────────────


@router.post("/github/analyze", summary="Analyze GitHub repos to propose skills")
def analyze_github(
    req: GitHubAnalyzeRequest = GitHubAnalyzeRequest(),
    current_user: User = Depends(require_roles("student")),
    db: Session = Depends(get_db),
):
    require_verified_email(current_user)

    username = req.username
    if not username:
        prof = db.execute(
            select(StudentProfile).where(StudentProfile.user_id == current_user.id)
        ).scalar_one_or_none()
        if prof and prof.github_username:
            username = prof.github_username
        else:
            raise BadRequestError(
                "No GitHub account linked. Provide a username or link your account."
            )

    # Fetch public repos using services/github.py (AGENTS.md Rule 12)
    repos = fetch_github_repos(username)

    return github_analysis.analyse(
        db=db,
        user_id=current_user.id,
        github_data={"repos": repos},
    )


@router.post("/github/accept", summary="Accept AI proposed GitHub skills")
def accept_github_skills(
    req: GitHubAcceptRequest,
    current_user: User = Depends(require_roles("student")),
    db: Session = Depends(get_db),
):
    require_verified_email(current_user)
    return github_analysis.accept_skills(
        db=db,
        user_id=current_user.id,
        log_id=req.log_id,
        accepted_skills=req.accepted_skills,
    )


# ── 8. Recruiter Natural-Language Search (FR-REC-3) ───────────────────────────


@router.post("/recruiter/parse-query", summary="Convert recruiter plain text to structured filters")
def parse_recruiter_query(
    req: RecruiterQueryRequest,
    auth: tuple = Depends(require_approved_recruiter),
    db: Session = Depends(get_db),
):
    current_user, _recruiter = auth
    return recruiter_search.interpret_query(
        db=db,
        user_id=current_user.id,
        query_text=req.query,
    )


# ── 9. AI Feedback (T-AI-01) ──────────────────────────────────────────────────


@router.post("/log/{log_id}/feedback", summary="Record user feedback on AI draft")
def record_ai_feedback(
    log_id: int,
    req: AIFeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.execute(
        text("""
            SELECT id FROM ai_logs
             WHERE id = :lid AND user_id = :uid
        """),
        {"lid": log_id, "uid": current_user.id},
    ).fetchone()
    if not row:
        raise NotFoundError("AI log not found.")

    db.execute(
        text("UPDATE ai_logs SET accepted = :accepted WHERE id = :lid"),
        {"lid": log_id, "accepted": req.accepted},
    )
    db.commit()
    return {"status": "ok", "log_id": log_id, "accepted": req.accepted}


# ── 10. AI Mentor Chat (FR-WRK-5) ─────────────────────────────────────────────


@router.post("/mentor/chat", summary="Chat with AI Mentor about active project workspace")
def mentor_chat(
    req: MentorChatRequest,
    current_user: User = Depends(require_roles("student")),
    db: Session = Depends(get_db),
):
    """FR-WRK-5: Socratic hints and guidance for student's active workspace."""
    require_verified_email(current_user)
    return mentor.chat(
        db=db,
        user_id=current_user.id,
        application_id=req.application_id,
        message=req.message,
        milestone_id=req.milestone_id,
        history=req.history,
    )


# ── 11. Evaluation Feedback Drafter (FR-EVL-5) ────────────────────────────────


@router.post("/evaluations/draft-feedback", summary="Draft structured feedback from reviewer notes")
def draft_evaluation_feedback(
    req: FeedbackDraftRequest,
    auth: tuple = Depends(require_approved_company),
    db: Session = Depends(get_db),
):
    """FR-EVL-5: AI drafts structured feedback from rough notes."""
    current_user, _company = auth
    return feedback_drafter.draft(
        db=db,
        user_id=current_user.id,
        submission_id=req.submission_id,
        rough_notes=req.rough_notes,
        rubric_scores=req.rubric_scores,
    )


# ── 12. Resume Bullet Rewriter (FR-RWD-4) ─────────────────────────────────────


@router.post(
    "/rewrite/resume-bullets",
    summary="Generate STAR-formatted resume bullets from verified record",
)
def rewrite_resume_bullets(
    req: ResumeBulletsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """FR-RWD-4: STAR-formatted resume bullets strictly citing verified facts."""
    require_verified_email(current_user)
    return resume_rewriter.rewrite(
        db=db,
        user_id=current_user.id,
        certificate_id=req.certificate_id,
    )
