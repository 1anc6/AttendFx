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

    # Host header values the MCP endpoint accepts (DNS-rebinding protection). In production set
    # this to the public hostname, for example "attendfx.onrender.com".
    allowed_hosts: str = "localhost:*,127.0.0.1:*,testserver"

    # Requests per person (all of one user's keys share a bucket): burst, then N a minute.
    rate_limit_per_minute: float = 60
    rate_limit_burst: int = 20
    # Failed key checks per client IP before that IP gets 429s. Generous on purpose: a whole
    # campus can share one IP behind NAT. Behind a proxy, run uvicorn with --proxy-headers.
    auth_failures_per_minute: float = 30
    auth_failures_burst: int = 60


def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
