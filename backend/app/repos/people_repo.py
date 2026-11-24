"""SQL for the admin People page. Runs as the narrow `afx_auth` role, which sees every account,
so callers (app.services.people) must check that the actor is an admin first."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import psycopg

from app.db.pools import auth_pool

PAGE_SIZE = 25


@dataclass(frozen=True)
class PersonRow:
    id: UUID
    name: str
    email: str
    role: str
    created_at: datetime
    last_sign_in_at: datetime | None
    locked_until: datetime | None
    disabled_at: datetime | None
    must_change_password: bool
    active_keys: int


@dataclass(frozen=True)
class NewPerson:
    name: str
    email: str
    role: str
    password_hash: str


class EmailTaken(Exception):
    pass


# status filter -> SQL condition. Fixed strings only; never built from input.
STATUS_SQL = {
    "all": "true",
    "active": "u.disabled_at IS NULL",
    "locked": "u.disabled_at IS NULL AND u.locked_until > now()",
    "must_change": "u.disabled_at IS NULL AND u.must_change_password",
    "disabled": "u.disabled_at IS NOT NULL",
}


def _like(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def list_people(
    *, search: str, role: str | None, status: str, page: int
) -> tuple[list[PersonRow], int]:
    """One page of people in name order, plus how many match in all."""
    where = [STATUS_SQL[status]]
    params: dict[str, object] = {"limit": PAGE_SIZE, "offset": (page - 1) * PAGE_SIZE}
    if search:
        where.append("(u.name ILIKE %(q)s OR u.email ILIKE %(q)s)")
        params["q"] = _like(search)
    if role:
        where.append("u.role = %(role)s")
        params["role"] = role
    condition = " AND ".join(where)
    with auth_pool().connection() as conn:
        total = conn.execute(f"SELECT count(*) FROM users u WHERE {condition}", params).fetchone()[
            0
        ]
        rows = conn.execute(
            f"""
            SELECT u.id, u.name, u.email, u.role, u.created_at, u.last_sign_in_at,
                   u.locked_until, u.disabled_at, u.must_change_password,
                   (SELECT count(*) FROM api_keys k
                    WHERE k.user_id = u.id AND k.revoked_at IS NULL
                      AND (k.expires_at IS NULL OR k.expires_at > now()))
            FROM users u WHERE {condition}
            ORDER BY lower(u.name), u.id
            LIMIT %(limit)s OFFSET %(offset)s
            """,
            params,
        ).fetchall()
    return [PersonRow(*r) for r in rows], total


def counts() -> dict[str, int]:
    with auth_pool().connection() as conn:
        row = conn.execute(
            """
            SELECT count(*),
                   count(*) FILTER (WHERE role = 'student'),
                   count(*) FILTER (WHERE role = 'teacher'),
                   count(*) FILTER (WHERE role = 'admin'),
                   count(*) FILTER (WHERE disabled_at IS NULL AND locked_until > now()),
                   count(*) FILTER (WHERE disabled_at IS NULL AND must_change_password),
                   count(*) FILTER (WHERE disabled_at IS NOT NULL)
            FROM users
            """
        ).fetchone()
    keys = ("total", "student", "teacher", "admin", "locked", "must_change", "disabled")
    return dict(zip(keys, row, strict=True))


def get_person(person_id: UUID) -> tuple[UUID, str, str, str] | None:
    """(id, name, email, role)."""
    with auth_pool().connection() as conn:
        row = conn.execute(
            "SELECT id, name, email, role FROM users WHERE id = %s", (person_id,)
        ).fetchone()
    return tuple(row) if row else None


def existing_emails(emails: list[str]) -> set[str]:
    """Which of these (lowercased) emails already belong to an account."""
    if not emails:
        return set()
    with auth_pool().connection() as conn:
        rows = conn.execute(
            "SELECT lower(email) FROM users WHERE lower(email) = ANY(%s)", (emails,)
        ).fetchall()
    return {r[0] for r in rows}


def create_people(people: list[NewPerson]) -> list[UUID]:
    """Insert all or none, in one transaction. Every account starts with a temporary password
    that must be changed. Raises EmailTaken if an email was taken meanwhile."""
    with auth_pool().connection() as conn:
        try:
            with conn.transaction():
                ids = []
                for p in people:
                    row = conn.execute(
                        """
                        INSERT INTO users (name, email, role, password_hash, must_change_password)
                        VALUES (%s, %s, %s, %s, true) RETURNING id
                        """,
                        (p.name, p.email, p.role, p.password_hash),
                    ).fetchone()
                    ids.append(row[0])
        except psycopg.errors.UniqueViolation:
            raise EmailTaken() from None
    return ids


def unlock(person_id: UUID) -> bool:
    """Clear a lockout. False if there was nothing to clear."""
    with auth_pool().connection() as conn:
        row = conn.execute(
            """
            UPDATE users SET failed_logins = 0, locked_until = NULL
            WHERE id = %s AND (locked_until IS NOT NULL OR failed_logins > 0) RETURNING id
            """,
            (person_id,),
        ).fetchone()
    return row is not None


def set_disabled(person_id: UUID, disabled: bool) -> bool:
    """Turn an account off (ending its web sessions) or back on. False if nothing changed."""
    with auth_pool().connection() as conn:
        if disabled:
            row = conn.execute(
                "UPDATE users SET disabled_at = now() WHERE id = %s AND disabled_at IS NULL "
                "RETURNING id",
                (person_id,),
            ).fetchone()
            conn.execute("DELETE FROM web_sessions WHERE user_id = %s", (person_id,))
        else:
            row = conn.execute(
                "UPDATE users SET disabled_at = NULL WHERE id = %s AND disabled_at IS NOT NULL "
                "RETURNING id",
                (person_id,),
            ).fetchone()
    return row is not None
