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
