from datetime import UTC, datetime, timedelta

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.auth.keys import generate_key
from app.main import app
from app.repos import auth_repo


def owner_url(settings) -> str:
    return settings.owner_database_url.replace("postgresql+psycopg://", "postgresql://")


@pytest.fixture(scope="session")
def client(require_db):
    with TestClient(app) as c:
        yield c


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
