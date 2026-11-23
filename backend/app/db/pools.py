"""Connection pools, one per database role, and the per-request RLS identity helper.

Sync psycopg with a thread-offloaded call path is used on purpose: it behaves the same on
Windows, Linux and CI, and avoids the async/Proactor event loop incompatibility.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from uuid import UUID

import psycopg
from psycopg_pool import ConnectionPool

from app.config import get_settings


@dataclass(frozen=True)
class Identity:
    """Who is asking. Built only from a verified key or session, never from client input."""

    user_id: UUID
    role: str
    key_id: UUID | None = None


_pools: dict[str, ConnectionPool] = {}


def _pool(name: str, url: str) -> ConnectionPool:
    pool = _pools.get(name)
    if pool is None:
        pool = ConnectionPool(url, min_size=1, max_size=8, open=True, name=f"afx-{name}")
        _pools[name] = pool
    return pool


def app_pool() -> ConnectionPool:
    return _pool("app", get_settings().app_database_url)


def auth_pool() -> ConnectionPool:
    return _pool("auth", get_settings().auth_database_url)


def close_pools() -> None:
    for pool in _pools.values():
        pool.close()
    _pools.clear()


@contextmanager
def rls_connection(identity: Identity) -> Iterator[psycopg.Connection]:
    """A connection whose transaction runs as `identity` under row-level security.

    set_config(..., true) is transaction-local, so the identity cannot leak to the next
    request even through a pooled connection. The pool commits on a clean exit.
    """
    with app_pool().connection() as conn:
        conn.execute(
            "SELECT set_config('app.user_id', %s, true), set_config('app.role', %s, true)",
            (str(identity.user_id), identity.role),
        )
        yield conn
