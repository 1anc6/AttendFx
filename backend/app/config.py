"""Application settings, read from environment variables (and the repo-root .env in development)."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_prefix="AFX_",
        extra="ignore",
    )

    # One URL per database role. See docs/ARCHITECTURE.md section 4.2.
    owner_database_url: str  # migrations only (SQLAlchemy URL, postgresql+psycopg://)
    app_database_url: str  # RLS-bound reads for tools
    auth_database_url: str  # keys, sessions, audit
    sync_database_url: str  # worker writes

    # Passwords the migration assigns to the app roles.
    app_password: str = ""
    auth_password: str = ""
    sync_password: str = ""

    seed_password: str = "dev-password-change-me"


def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
