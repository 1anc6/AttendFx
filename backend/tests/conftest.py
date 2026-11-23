from contextlib import contextmanager

import psycopg
import pytest

from app.config import get_settings


def _db_available() -> bool:
    try:
        with psycopg.connect(get_settings().sync_database_url, connect_timeout=3):
            return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def settings():
    return get_settings()


@pytest.fixture(scope="session")
def require_db(settings):
    if not _db_available():
        pytest.skip("database not reachable: run `docker compose up -d`, migrate and seed first")


@pytest.fixture
def truth(settings, require_db):
    """Ground-truth connection (afx_sync policies allow all rows). Read-only use in tests."""
    with psycopg.connect(settings.sync_database_url) as conn:
        yield conn


@pytest.fixture
def as_user(settings, require_db):
    """Run queries as the app role with a given identity, the way the backend does per request."""

    @contextmanager
    def _as_user(user_id, role):
        with psycopg.connect(settings.app_database_url) as conn:
            with conn.transaction():
                conn.execute(
                    "SELECT set_config('app.user_id', %s, true), set_config('app.role', %s, true)",
                    (str(user_id) if user_id else "", role or ""),
                )
                yield conn

    return _as_user
