from datetime import UTC, datetime, timedelta

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.api import routes as api_routes
from app.auth.keys import generate_key
from app.main import app, mcp_asgi
from app.ratelimit.limiter import TokenBucketLimiter
from app.repos import auth_repo


def owner_url(settings) -> str:
    return settings.owner_database_url.replace("postgresql+psycopg://", "postgresql://")


@pytest.fixture(scope="session")
def client(require_db):
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def generous_limits():
    """The suite makes hundreds of fast calls as the same few users. Give every test fresh,
    effectively unlimited buckets; rate-limit tests install tight ones themselves."""
    mcp_asgi.user_limiter = TokenBucketLimiter(1_000_000, 1_000_000)
    mcp_asgi.failure_limiter = TokenBucketLimiter(1_000_000, 1_000_000)
    api_routes.limits.per_user = TokenBucketLimiter(1_000_000, 1_000_000)
    api_routes.limits.login_failures = TokenBucketLimiter(1_000_000, 1_000_000)
    yield


@pytest.fixture(scope="session")
def make_key(require_db, settings):
    """Mint keys directly (like an admin would) and delete them, and their audit rows, after."""
    created = []

    def _make(user_id, *, expires_in=timedelta(days=1)):
        full, prefix, secret_hash = generate_key()
        key_id = auth_repo.create_key(
            user_id, "pytest-key", prefix, secret_hash, datetime.now(UTC) + expires_in
        )
        created.append(key_id)
        return full

    yield _make

    with psycopg.connect(owner_url(settings)) as conn:
        conn.execute("DELETE FROM audit_log WHERE key_id = ANY(%s)", (created,))
        conn.execute("DELETE FROM api_keys WHERE id = ANY(%s)", (created,))


@pytest.fixture
def owner(settings, require_db):
    """Superuser-ish connection for test setup and inspection only (never used by the app)."""
    with psycopg.connect(owner_url(settings)) as conn:
        yield conn
