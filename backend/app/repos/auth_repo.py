"""SQL for keys, accounts and audit rows. Runs as the narrow `afx_auth` role."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.db.pools import auth_pool


@dataclass(frozen=True)
class KeyRecord:
    id: UUID
    user_id: UUID
    role: str
    secret_hash: str
    expires_at: datetime | None
    revoked_at: datetime | None


def find_key(prefix: str) -> KeyRecord | None:
    with auth_pool().connection() as conn:
        row = conn.execute(
            """
            SELECT k.id, k.user_id, u.role, k.secret_hash, k.expires_at, k.revoked_at
            FROM api_keys k JOIN users u ON u.id = k.user_id
            WHERE k.prefix = %s
            """,
            (prefix,),
        ).fetchone()
    return KeyRecord(*row) if row else None


def touch_key(key_id: UUID) -> None:
    """Record last use, at most once a minute per key, to avoid a write on every request."""
    with auth_pool().connection() as conn:
        conn.execute(
            """
            UPDATE api_keys SET last_used_at = now()
            WHERE id = %s AND (last_used_at IS NULL OR last_used_at < now() - interval '1 minute')
            """,
            (key_id,),
        )


def create_key(
    user_id: UUID, name: str, prefix: str, secret_hash: str, expires_at: datetime | None
) -> UUID:
    with auth_pool().connection() as conn:
        row = conn.execute(
            """
            INSERT INTO api_keys (user_id, name, prefix, secret_hash, expires_at)
            VALUES (%s, %s, %s, %s, %s) RETURNING id
            """,
            (user_id, name, prefix, secret_hash, expires_at),
        ).fetchone()
    return row[0]


def create_key_limited(
    owner_id: UUID,
    name: str,
    prefix: str,
    secret_hash: str,
    expires_at: datetime,
    max_active: int,
) -> tuple[str, UUID | None]:
    """Insert a key unless the owner already has `max_active` usable keys.

    Locks the owner's user row so two concurrent requests cannot both pass the count.
    Returns ("ok", id), ("no_user", None) or ("limit", None).
    """
    with auth_pool().connection() as conn:
        if (
            conn.execute("SELECT 1 FROM users WHERE id = %s FOR UPDATE", (owner_id,)).fetchone()
            is None
        ):
            return "no_user", None
        active = conn.execute(
            """
            SELECT count(*) FROM api_keys
            WHERE user_id = %s AND revoked_at IS NULL AND (expires_at IS NULL OR expires_at > now())
            """,
            (owner_id,),
        ).fetchone()[0]
        if active >= max_active:
            return "limit", None
        row = conn.execute(
            """
            INSERT INTO api_keys (user_id, name, prefix, secret_hash, expires_at)
            VALUES (%s, %s, %s, %s, %s) RETURNING id
            """,
            (owner_id, name, prefix, secret_hash, expires_at),
        ).fetchone()
    return "ok", row[0]


def list_keys(owner_id: UUID) -> list[tuple]:
    """(id, name, prefix, created_at, last_used_at, expires_at, revoked_at). Never the hash."""
    with auth_pool().connection() as conn:
        return conn.execute(
            """
            SELECT id, name, prefix, created_at, last_used_at, expires_at, revoked_at
            FROM api_keys WHERE user_id = %s ORDER BY created_at DESC
            """,
            (owner_id,),
        ).fetchall()


def get_key_owner(key_id: UUID) -> tuple[UUID, datetime | None] | None:
    """(owner user id, revoked_at) for a key id."""
    with auth_pool().connection() as conn:
        row = conn.execute(
            "SELECT user_id, revoked_at FROM api_keys WHERE id = %s", (key_id,)
        ).fetchone()
    return (row[0], row[1]) if row else None


def find_key_id_by_prefix(prefix: str) -> UUID | None:
    with auth_pool().connection() as conn:
        row = conn.execute("SELECT id FROM api_keys WHERE prefix = %s", (prefix,)).fetchone()
    return row[0] if row else None


def revoke_key(key_id: UUID) -> bool:
    """Revoke now. False if it was already revoked (revocation time is never moved)."""
    with auth_pool().connection() as conn:
        row = conn.execute(
            "UPDATE api_keys SET revoked_at = now() WHERE id = %s AND revoked_at IS NULL "
            "RETURNING id",
            (key_id,),
        ).fetchone()
    return row is not None


def find_user_by_email(email: str) -> tuple[UUID, str] | None:
    with auth_pool().connection() as conn:
        row = conn.execute(
            "SELECT id, role FROM users WHERE lower(email) = lower(%s)", (email,)
        ).fetchone()
    return (row[0], row[1]) if row else None


def insert_audit(
    *,
    user_id: UUID | None,
    key_id: UUID | None,
    surface: str,
    action: str,
    args_hash: str | None,
    status: str,
    latency_ms: int,
    request_id: str | None,
) -> None:
    with auth_pool().connection() as conn:
        conn.execute(
            """
            INSERT INTO audit_log
                (user_id, key_id, surface, action, args_hash, status, latency_ms, request_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (user_id, key_id, surface, action, args_hash, status, latency_ms, request_id),
        )
