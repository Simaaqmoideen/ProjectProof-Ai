
from app.config import Settings


def test_settings_reads_uppercase_env_variables(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg://postgres:postgres@db:5432/projectproof"
    )
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:5173")

    settings = Settings()

    assert settings.database_url == "postgresql+psycopg://postgres:postgres@db:5432/projectproof"
    assert settings.jwt_secret == "test-secret"
    assert settings.frontend_url == "http://localhost:5173"


def test_settings_uses_localhost_default_when_unset(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.delenv("FRONTEND_URL", raising=False)
    monkeypatch.delenv("database_url", raising=False)
    monkeypatch.delenv("jwt_secret", raising=False)
    monkeypatch.delenv("frontend_url", raising=False)

    settings = Settings(_env_file=None)

    assert (
        settings.database_url
        == "postgresql+psycopg://postgres:postgres@localhost:5432/projectproof"
    )
    assert settings.jwt_secret == "change-me-to-a-long-random-string"
    assert settings.frontend_url == "http://localhost:5173"
