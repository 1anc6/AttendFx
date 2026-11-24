"""SQL for web sign-in and web sessions. Runs as the narrow `afx_auth` role."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.db.pools import auth_pool


@dataclass(frozen=True)
class LoginRecord:
    id: UUID
    name: str
    email: str
    role: str
    password_hash: str
    locked_until: datetime | None


@dataclass(frozen=True)
class SessionRecord:
    user_id: UUID
    role: str
    name: str
    email: str
    csrf_token: str
    expires_at: datetime


def find_login(email: str) -> LoginRecord | None:
    with auth_pool().connection() as conn:
        row = conn.execute(
            """
            SELECT id, name, email, role, password_hash, locked_until
            FROM users WHERE lower(email) = lower(%s)
            """,
            (email,),
        ).fetchone()
    return LoginRecord(*row) if row else None


def record_failure(user_id: UUID, max_failures: int, lock_minutes: int) -> datetime | None:
    """Count one wrong password. On reaching `max_failures`, lock the account and reset the
    counter. One atomic UPDATE, so concurrent guesses cannot skip the lock. Returns
    locked_until (None while not locked)."""
    with auth_pool().connection() as conn:
        row = conn.execute(
            """
            UPDATE users SET
                failed_logins = CASE WHEN failed_logins + 1 >= %(max)s
                                     THEN 0 ELSE failed_logins + 1 END,
                locked_until  = CASE WHEN failed_logins + 1 >= %(max)s
                                     THEN now() + make_interval(mins => %(mins)s)
                                     ELSE locked_until END
            WHERE id = %(id)s
            RETURNING locked_until
            """,
            {"max": max_failures, "mins": lock_minutes, "id": user_id},
        ).fetchone()
    return row[0] if row else None


def record_success(user_id: UUID, new_password_hash: str | None = None) -> None:
    """Clear the failure count and any expired lock; optionally store an upgraded hash."""
    with auth_pool().connection() as conn:
        if new_password_hash:
            conn.execute(
                "UPDATE users SET failed_logins = 0, locked_until = NULL, password_hash = %s "
                "WHERE id = %s",
                (new_password_hash, user_id),
            )
        else:
            conn.execute(
                "UPDATE users SET failed_logins = 0, locked_until = NULL WHERE id = %s",
                (user_id,),
            )


def create_session(session_hash: str, user_id: UUID, csrf_token: str, expires_at: datetime) -> None:
    """Store a session under the hash of its cookie value. Also drops this person's expired
    sessions, so the table does not grow without bound."""
    with auth_pool().connection() as conn:
        conn.execute(
            "DELETE FROM web_sessions WHERE user_id = %s AND expires_at <= now()", (user_id,)
        )
        conn.execute(
            """
            INSERT INTO web_sessions (id, user_id, csrf_token, expires_at)
            VALUES (%s, %s, %s, %s)
            """,
            (session_hash, user_id, csrf_token, expires_at),
        )


def find_session(session_hash: str) -> SessionRecord | None:
    with auth_pool().connection() as conn:
        row = conn.execute(
            """
            SELECT s.user_id, u.role, u.name, u.email, s.csrf_token, s.expires_at
            FROM web_sessions s JOIN users u ON u.id = s.user_id
            WHERE s.id = %s AND s.expires_at > now()
            """,
            (session_hash,),
        ).fetchone()
    return SessionRecord(*row) if row else None


def delete_session(session_hash: str) -> None:
    with auth_pool().connection() as conn:
        conn.execute("DELETE FROM web_sessions WHERE id = %s", (session_hash,))
