"""Settings and business-rule numbers. Change values here, never in code (see docs/01 section 7 and AGENTS.md)."""

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/projectproof",
        validation_alias=AliasChoices("DATABASE_URL", "database_url"),
    )
    jwt_secret: str = Field(
        default="change-me-to-a-long-random-string",
        validation_alias=AliasChoices("JWT_SECRET", "jwt_secret"),
    )
    jwt_algorithm: str = Field(
        default="HS256",
        validation_alias=AliasChoices("JWT_ALGORITHM", "jwt_algorithm"),
    )
    access_token_minutes: int = Field(
        default=15,
        validation_alias=AliasChoices("ACCESS_TOKEN_MINUTES", "access_token_minutes"),
    )
    refresh_token_days: int = Field(
        default=7,
        validation_alias=AliasChoices("REFRESH_TOKEN_DAYS", "refresh_token_days"),
    )
    email_verification_token_hours: int = Field(
        default=24,
        validation_alias=AliasChoices("EMAIL_VERIFICATION_TOKEN_HOURS", "email_verification_token_hours"),
    )
    password_reset_token_hours: int = Field(
        default=1,
        validation_alias=AliasChoices("PASSWORD_RESET_TOKEN_HOURS", "password_reset_token_hours"),
    )
    environment: str = Field(
        default="development",
        validation_alias=AliasChoices("ENVIRONMENT", "environment"),
    )
    frontend_url: str = Field(
        default="http://localhost:5173",
        validation_alias=AliasChoices("FRONTEND_URL", "frontend_url"),
    )

    # Rate limiting defaults
    login_rate_limit: str = Field(
        default="5/minute",
        validation_alias=AliasChoices("LOGIN_RATE_LIMIT", "login_rate_limit"),
    )
    public_verification_rate_limit: str = Field(
        default="30/minute",
        validation_alias=AliasChoices("PUBLIC_VERIFICATION_RATE_LIMIT", "public_verification_rate_limit"),
    )

    # BR-1 XP formula constants
    xp_base_per_day: int = Field(
        default=6,
        validation_alias=AliasChoices("XP_BASE_PER_DAY", "xp_base_per_day"),
    )
    xp_cap: int = Field(
        default=200,
        validation_alias=AliasChoices("XP_CAP", "xp_cap"),
    )
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
    trust_score_initial: int = Field(
        default=50,
        validation_alias=AliasChoices("TRUST_SCORE_INITIAL", "trust_score_initial"),
    )
    trust_score_fast_eval: int = Field(
        default=5,
        validation_alias=AliasChoices("TRUST_SCORE_FAST_EVAL", "trust_score_fast_eval"),
    )
    trust_score_fast_eval_cap: int = Field(
        default=30,
        validation_alias=AliasChoices("TRUST_SCORE_FAST_EVAL_CAP", "trust_score_fast_eval_cap"),
    )
    trust_score_overturned_penalty: int = Field(
        default=10,
        validation_alias=AliasChoices("TRUST_SCORE_OVERTURNED_PENALTY", "trust_score_overturned_penalty"),
    )
    trust_score_revocation_penalty: int = Field(
        default=20,
        validation_alias=AliasChoices("TRUST_SCORE_REVOCATION_PENALTY", "trust_score_revocation_penalty"),
    )
    trust_score_five_projects_bonus: int = Field(
        default=10,
        validation_alias=AliasChoices("TRUST_SCORE_FIVE_PROJECTS_BONUS", "trust_score_five_projects_bonus"),
    )
    trust_score_removed_project_penalty: int = Field(
        default=15,
        validation_alias=AliasChoices("TRUST_SCORE_REMOVED_PROJECT_PENALTY", "trust_score_removed_project_penalty"),
    )
    trust_score_publish_threshold: int = Field(
        default=30,
        validation_alias=AliasChoices("TRUST_SCORE_PUBLISH_THRESHOLD", "trust_score_publish_threshold"),
    )

    # BR-10 Recommendation bonuses
    recommend_category_bonus: int = Field(
        default=10,
        validation_alias=AliasChoices("RECOMMEND_CATEGORY_BONUS", "recommend_category_bonus"),
    )
    recommend_stretch_bonus: int = Field(
        default=5,
        validation_alias=AliasChoices("RECOMMEND_STRETCH_BONUS", "recommend_stretch_bonus"),
    )

    # Limits and rules
    max_active_applications: int = Field(
        default=3,
        validation_alias=AliasChoices("MAX_ACTIVE_APPLICATIONS", "max_active_applications"),
    )
    max_submission_versions: int = Field(
        default=3,
        validation_alias=AliasChoices("MAX_SUBMISSION_VERSIONS", "max_submission_versions"),
    )
    appeal_days: int = Field(
        default=7,
        validation_alias=AliasChoices("APPEAL_DAYS", "appeal_days"),
    )
    max_tasks_per_milestone: int = Field(
        default=10,
        validation_alias=AliasChoices("MAX_TASKS_PER_MILESTONE", "max_tasks_per_milestone"),
    )
    new_company_project_limit: int = Field(
        default=2,
        validation_alias=AliasChoices("NEW_COMPANY_PROJECT_LIMIT", "new_company_project_limit"),
    )
    new_company_evaluations_needed: int = Field(
        default=3,
        validation_alias=AliasChoices("NEW_COMPANY_EVALUATIONS_NEEDED", "new_company_evaluations_needed"),
    )

    # Upload limits
    max_resume_bytes: int = Field(
        default=5 * 1024 * 1024,  # 5 MB
        validation_alias=AliasChoices("MAX_RESUME_BYTES", "max_resume_bytes"),
    )
    max_submission_file_bytes: int = Field(
        default=50 * 1024 * 1024,  # 50 MB
        validation_alias=AliasChoices("MAX_SUBMISSION_FILE_BYTES", "max_submission_file_bytes"),
    )
    upload_dir: str = Field(
        default="uploads",
        validation_alias=AliasChoices("UPLOAD_DIR", "upload_dir"),
    )

    # AI settings
    llm_provider: str = Field(
        default="mock",
        validation_alias=AliasChoices("LLM_PROVIDER", "llm_provider"),
    )
    llm_api_key: str = Field(
        default="mock",
        validation_alias=AliasChoices("LLM_API_KEY", "llm_api_key"),
    )
    llm_model: str = Field(
        default="gpt-4o-mini",
        validation_alias=AliasChoices("LLM_MODEL", "llm_model"),
    )
    llm_daily_limit_per_user: int = Field(
        default=20,
        validation_alias=AliasChoices("LLM_DAILY_LIMIT_PER_USER", "llm_daily_limit_per_user"),
    )
    ai_timeout_seconds: int = Field(
        default=30,
        validation_alias=AliasChoices("AI_TIMEOUT_SECONDS", "ai_timeout_seconds"),
    )
    ai_max_resume_chars: int = Field(
        default=15_000,
        validation_alias=AliasChoices("AI_MAX_RESUME_CHARS", "ai_max_resume_chars"),
    )
    ai_max_idea_chars: int = Field(
        default=1_000,
        validation_alias=AliasChoices("AI_MAX_IDEA_CHARS", "ai_max_idea_chars"),
    )
    ai_max_source_chars: int = Field(
        default=30_000,
        validation_alias=AliasChoices("AI_MAX_SOURCE_CHARS", "ai_max_source_chars"),
    )

    # Mail / SMTP
    smtp_url: str = Field(
        default="",
        validation_alias=AliasChoices("SMTP_URL", "smtp_url"),
    )


settings = Settings()
