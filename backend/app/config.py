"""Settings and business-rule numbers. Change values here, never in code (see docs/01 section 7 and AGENTS.md)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres@127.0.0.1:5433/projectproof"
    jwt_secret: str = "change-me-to-a-long-random-string"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    email_verification_token_hours: int = 24
    password_reset_token_hours: int = 1
    environment: str = "development"
    frontend_url: str = "http://localhost:5173"

    # Rate limiting defaults
    login_rate_limit: str = "5/minute"
    public_verification_rate_limit: str = "30/minute"

    # BR-1 XP formula constants
    xp_base_per_day: int = 6
    xp_cap: int = 200
    difficulty_multiplier: dict[str, float] = {
        "beginner": 1.0,
        "intermediate": 1.5,
        "advanced": 2.0,
    }
    evaluation_multipliers: dict[str, float] = {
        "tier1": 1.0,  # 60-74
        "tier2": 1.1,  # 75-89
        "tier3": 1.2,  # 90-100
    }

    # BR-3 Match weights
    match_weights: dict[str, float] = {
        "skills": 0.5,
        "difficulty": 0.2,
        "experience": 0.2,
        "availability": 0.1,
    }

    # BR-6 Company trust score constants
    trust_score_initial: int = 50
    trust_score_fast_eval: int = 5
    trust_score_fast_eval_cap: int = 30
    trust_score_overturned_penalty: int = 10
    trust_score_revocation_penalty: int = 20
    trust_score_five_projects_bonus: int = 10
    trust_score_removed_project_penalty: int = 15
    trust_score_publish_threshold: int = 30

    # BR-10 Recommendation bonuses
    recommend_category_bonus: int = 10
    recommend_stretch_bonus: int = 5

    # Limits and rules
    max_active_applications: int = 3
    max_submission_versions: int = 3
    appeal_days: int = 7
    max_tasks_per_milestone: int = 10
    new_company_project_limit: int = 2
    new_company_evaluations_needed: int = 3

    # Upload limits
    max_resume_bytes: int = 5 * 1024 * 1024  # 5 MB
    max_submission_file_bytes: int = 50 * 1024 * 1024  # 50 MB
    upload_dir: str = "uploads"

    # AI settings
    llm_provider: str = "mock"
    llm_api_key: str = "mock"
    llm_model: str = "gpt-4o-mini"
    llm_daily_limit_per_user: int = 20
    ai_timeout_seconds: int = 30
    ai_max_resume_chars: int = 15_000
    ai_max_idea_chars: int = 1_000
    ai_max_source_chars: int = 30_000

    # Mail / SMTP
    smtp_url: str = ""


settings = Settings()
