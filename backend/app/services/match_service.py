"""BR-3 Match score and BR-10 Recommendation score calculations.
Deterministic algorithms implemented strictly from docs/06-ai-modules-specification.md section 5.
"""
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.application import Application, Certificate
from app.models.project import Project, ProjectSkill, Skill, StudentSkill

DIFFICULTY_LEVEL_MAP = {
    "beginner": 1,
    "intermediate": 2,
    "advanced": 3,
}

DIFFICULTY_FIT_TABLE = {
    0: 100,   # Same level
    -1: 80,   # One step easier (project beginner vs student intermediate)
    1: 60,    # One step harder (project intermediate vs student beginner)
    -2: 50,   # Two steps easier (project beginner vs student advanced)
    2: 25,    # Two steps harder (project advanced vs student beginner)
}


class MatchScoreService:
    @staticmethod
    def calculate_match_score(
        db: Session,
        student_id: uuid.UUID,
        project: Project,
    ) -> dict[str, Any]:
        """BR-3: match = 0.5 * skills + 0.2 * difficulty_fit + 0.2 * experience + 0.1 * availability.
        Returns score (0-100), breakdown dict, and list of missing skills.
        """
        # 1. Fetch project required skills
        proj_skill_ids = [
            ps.skill_id
            for ps in db.execute(
                select(ProjectSkill).where(ProjectSkill.project_id == project.id)
            ).scalars().all()
        ]

        # 2. Fetch student skills
        student_skills = list(
            db.execute(
                select(StudentSkill).where(StudentSkill.student_id == student_id)
            ).scalars().all()
        )
        student_skill_map = {ss.skill_id: ss for ss in student_skills}

        # Fetch skill details for missing skills output
        all_skills_map = {
            s.id: s.name
            for s in db.execute(select(Skill)).scalars().all()
        }

        # Calculate Skills Part (0 to 100)
        # Credit 1.0 if proficiency >= 3 or source == 'verified_project'; 0.5 if proficiency 1 or 2; otherwise 0.
        missing_skills: list[str] = []
        if not proj_skill_ids:
            skills_score = 100.0
        else:
            total_credit = 0.0
            for sid in proj_skill_ids:
                ss = student_skill_map.get(sid)
                if not ss:
                    missing_skills.append(all_skills_map.get(sid, f"Skill-{sid}"))
                elif ss.proficiency >= 3 or ss.source == "verified_project":
                    total_credit += 1.0
                else:
                    total_credit += 0.5
            skills_score = (100.0 * total_credit) / len(proj_skill_ids)

        # 3. Verified certificates & completions
        issued_certs = list(
            db.execute(
                select(Certificate, Project)
                .join(Application, Certificate.application_id == Application.id)
                .join(Project, Application.project_id == Project.id)
                .where(
                    Application.student_id == student_id,
                    Certificate.status == "issued",
                )
            ).all()
        )
        verified_completions_count = len(issued_certs)

        # Calculate Difficulty Fit Part (0 to 100)
        # 0 or 1 -> beginner, 2 to 4 -> intermediate, 5+ -> advanced
        if verified_completions_count <= 1:
            target_level = "beginner"
        elif verified_completions_count <= 4:
            target_level = "intermediate"
        else:
            target_level = "advanced"

        proj_level_num = DIFFICULTY_LEVEL_MAP.get(project.difficulty, 1)
        target_level_num = DIFFICULTY_LEVEL_MAP.get(target_level, 1)
        diff_step = proj_level_num - target_level_num
        difficulty_fit_score = float(DIFFICULTY_FIT_TABLE.get(diff_step, 50))

        # Calculate Experience Part (0 to 100)
        # Count issued certificates whose projects share at least one required skill (relevant)
        if not proj_skill_ids:
            relevant_certs_count = verified_completions_count
        else:
            relevant_certs_count = 0
            for cert, completed_proj in issued_certs:
                comp_skills = set(
                    db.execute(
                        select(ProjectSkill.skill_id).where(ProjectSkill.project_id == completed_proj.id)
                    ).scalars().all()
                )
                if comp_skills.intersection(proj_skill_ids):
                    relevant_certs_count += 1

        if relevant_certs_count >= 1:
            experience_score = float(min(100, 30 + 35 * relevant_certs_count))
        elif verified_completions_count > 0:
            experience_score = 30.0
        else:
            experience_score = 10.0

        # Calculate Availability Part (0 to 100)
        # By student's current in_progress applications: 0 gives 100, 1 gives 80, 2 gives 50, 3+ gives 20
        active_apps_count = db.execute(
            select(Application).where(
                Application.student_id == student_id,
                Application.status.in_(["in_progress", "submitted", "changes_requested"]),
            )
        ).scalars().all()
        active_count = len(list(active_apps_count))

        if active_count == 0:
            availability_score = 100.0
        elif active_count == 1:
            availability_score = 80.0
        elif active_count == 2:
            availability_score = 50.0
        else:
            availability_score = 20.0

        # Weighted calculation from config
        weights = settings.match_weights
        w_skills = weights.get("skills", 0.5)
        w_diff = weights.get("difficulty", 0.2)
        w_exp = weights.get("experience", 0.2)
        w_avail = weights.get("availability", 0.1)

        raw_match = (
            w_skills * skills_score
            + w_diff * difficulty_fit_score
            + w_exp * experience_score
            + w_avail * availability_score
        )
        final_score = round(min(100.0, max(0.0, raw_match)), 2)

        return {
            "score": round(final_score),
            "raw_score": final_score,
            "breakdown": {
                "skills": round(skills_score),
                "difficulty": round(difficulty_fit_score),
                "experience": round(experience_score),
                "availability": round(availability_score),
            },
            "missing_skills": missing_skills,
            "target_level": target_level,
            "relevant_completions": relevant_certs_count,
            "verified_completions": verified_completions_count,
            "active_applications": active_count,
        }

    @staticmethod
    def calculate_recommendation(
        db: Session,
        student_id: uuid.UUID,
        project: Project,
    ) -> dict[str, Any] | None:
        """BR-10 & FR-APP-10: Recommendation score calculation.
        recommend = min(100, match + 10 if category matches completed project + 5 if lacks 1 or 2 skills).
        Returns None if student already applied or has >= 3 active applications.
        """
        # Check active applications limit (>= 3 active projects are not recommended)
        active_apps = list(db.execute(
            select(Application).where(
                Application.student_id == student_id,
                Application.status.in_(["in_progress", "submitted", "changes_requested"]),
            )
        ).scalars().all())
        if len(active_apps) >= 3:
            return None

        # Check if already applied to this project
        already_applied = db.execute(
            select(Application).where(
                Application.student_id == student_id,
                Application.project_id == project.id,
            )
        ).scalars().first()
        if already_applied:
            return None

        match_info = MatchScoreService.calculate_match_score(db, student_id, project)
        base_match = match_info["score"]
        missing_skills = match_info["missing_skills"]

        # Bonus 1: Category match with completed verified projects (+10)
        completed_categories = set(
            db.execute(
                select(Project.category)
                .join(Application, Application.project_id == Project.id)
                .join(Certificate, Certificate.application_id == Application.id)
                .where(
                    Application.student_id == student_id,
                    Certificate.status == "issued",
                )
            ).scalars().all()
        )
        category_match = project.category in completed_categories
        category_bonus = settings.recommend_category_bonus if category_match else 0

        # Bonus 2: Stretch bonus (+5 if student lacks 1 or 2 required skills)
        stretch_bonus = 0
        if 1 <= len(missing_skills) <= 2:
            stretch_bonus = settings.recommend_stretch_bonus

        total_recommend = min(100, base_match + category_bonus + stretch_bonus)

        # Assemble one-line human-readable reason
        # Total skills required
        proj_skill_count = len(db.execute(
            select(ProjectSkill).where(ProjectSkill.project_id == project.id)
        ).scalars().all())
        matched_count = max(0, proj_skill_count - len(missing_skills))

        reasons: list[str] = []
        if stretch_bonus > 0 and missing_skills:
            reasons.append(f"Stretch: learn {', '.join(missing_skills)}")
        elif proj_skill_count > 0:
            reasons.append(f"Matches {matched_count} of {proj_skill_count} skills")

        if category_match:
            reasons.append(f"in {project.category} which you have completed")

        if not reasons:
            reasons.append(f"Good fit for your {match_info['target_level']} level")

        reason_text = "; ".join(reasons)

        return {
            "project_id": project.id,
            "project": project,
            "recommendation_score": total_recommend,
            "match_score": base_match,
            "match_breakdown": match_info["breakdown"],
            "reason": reason_text,
            "missing_skills": missing_skills,
        }
