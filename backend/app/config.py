"""Settings and business-rule numbers. Change values here, never in code (see docs/01 section 7)."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@db:5432/projectproof"
    jwt_secret: str = "change-me"
    access_token_minutes: int = 15

    # BR-1 XP
    xp_base_per_day: int = 6
    xp_cap: int = 200
    difficulty_multiplier: dict[str, float] = {"beginner": 1.0, "intermediate": 1.5, "advanced": 2.0}
    # BR-3 match weights
    match_weights: dict[str, float] = {"skills": 0.5, "difficulty": 0.2, "experience": 0.2, "availability": 0.1}
    # BR-10 recommendation bonuses
    recommend_category_bonus: int = 10
    recommend_stretch_bonus: int = 5
    # limits
    max_active_applications: int = 3
    max_submission_versions: int = 3
    appeal_days: int = 7
    max_tasks_per_milestone: int = 10
    trust_penalty_project_removed: int = 15

    class Config:
        env_file = ".env"


settings = Settings()
