"""SQL for the admin Activity and Usage pages: reads of the audit log, joined to people and keys
for display. Runs as `afx_auth`, which may read the audit log and every account, so callers
(app.services.admin) must check that the actor is an admin first.

Days are Asia/Kolkata calendar days. The audit log keeps 90 days, so nothing older exists.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.db.pools import auth_pool

IST = "Asia/Kolkata"
PAGE_SIZE = 50

# Outcomes that mean "the request did what was asked". Everything else is a problem worth a look
# (denied, invalid, error, locked, rejected, limit, not_found, ...). Fixed strings only.
FINE_STATUSES = ("ok", "no_records", "unchanged", "already_revoked", "not_locked")

SURFACES = ("mcp", "api", "cli")


@dataclass(frozen=True)
class ActivityRow:
    id: int
    ts: datetime
    surface: str
    action: str
    status: str
    latency_ms: int | None
    user_id: UUID | None
    name: str | None
    email: str | None
    role: str | None
    key_prefix: str | None


def _like(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def activity(
    *, surface: str | None, problems_only: bool, search: str, page: int
) -> tuple[list[ActivityRow], int]:
    """One page of audit rows, newest first, plus how many match in all."""
    where = ["true"]
    params: dict[str, object] = {
        "fine": list(FINE_STATUSES),
        "limit": PAGE_SIZE,
        "offset": (page - 1) * PAGE_SIZE,
    }
    if surface:
        where.append("a.surface = %(surface)s")
        params["surface"] = surface
    if problems_only:
        where.append("NOT (a.status = ANY(%(fine)s))")
    if search:
        where.append("(u.name ILIKE %(q)s OR u.email ILIKE %(q)s OR a.action ILIKE %(q)s)")
        params["q"] = _like(search)
    condition = " AND ".join(where)
    joins = """
        FROM audit_log a
        LEFT JOIN users u ON u.id = a.user_id
        LEFT JOIN api_keys k ON k.id = a.key_id
    """
    with auth_pool().connection() as conn:
        total = conn.execute(f"SELECT count(*) {joins} WHERE {condition}", params).fetchone()[0]
        rows = conn.execute(
            f"""
            SELECT a.id, a.ts, a.surface, a.action, a.status, a.latency_ms,
                   a.user_id, u.name, u.email, u.role, k.prefix
            {joins}
            WHERE {condition}
            ORDER BY a.ts DESC, a.id DESC
            LIMIT %(limit)s OFFSET %(offset)s
            """,
            params,
        ).fetchall()
    return [ActivityRow(*r) for r in rows], total


def daily(days: int) -> list[tuple[str, int, int, int]]:
    """(day, assistant calls, web and CLI events, problems) for each of the last `days` days,
    oldest first, with empty days included."""
    with auth_pool().connection() as conn:
        rows = conn.execute(
            """
            WITH span AS (
                SELECT generate_series(
                    (now() AT TIME ZONE %(tz)s)::date - (%(days)s - 1),
                    (now() AT TIME ZONE %(tz)s)::date,
                    interval '1 day'
                )::date AS day
            ),
            counted AS (
                SELECT (ts AT TIME ZONE %(tz)s)::date AS day,
                       count(*) FILTER (WHERE surface = 'mcp') AS mcp,
                       count(*) FILTER (WHERE surface <> 'mcp') AS other,
                       count(*) FILTER (WHERE NOT (status = ANY(%(fine)s))) AS problems
                FROM audit_log
                WHERE ts >= ((now() AT TIME ZONE %(tz)s)::date - (%(days)s - 1))
                             ::timestamp AT TIME ZONE %(tz)s
                GROUP BY 1
            )
            SELECT span.day, coalesce(c.mcp, 0), coalesce(c.other, 0), coalesce(c.problems, 0)
            FROM span LEFT JOIN counted c ON c.day = span.day
            ORDER BY span.day
            """,
            {"tz": IST, "days": days, "fine": list(FINE_STATUSES)},
        ).fetchall()
    return [(d.isoformat(), mcp, other, problems) for d, mcp, other, problems in rows]


# Rows from the start of the first of the last %(days)s India-time days. Needs tz and days.
SINCE = "ts >= ((now() AT TIME ZONE %(tz)s)::date - (%(days)s - 1))::timestamp AT TIME ZONE %(tz)s"


def by_tool(days: int) -> list[tuple[str, int, int, int | None, int | None]]:
    """(action, calls, problems, median ms, 95th percentile ms) for assistant calls."""
    with auth_pool().connection() as conn:
        rows = conn.execute(
            f"""
            SELECT action, count(*),
                   count(*) FILTER (WHERE NOT (status = ANY(%(fine)s))),
                   percentile_disc(0.5) WITHIN GROUP (ORDER BY latency_ms),
                   percentile_disc(0.95) WITHIN GROUP (ORDER BY latency_ms)
            FROM audit_log
            WHERE surface = 'mcp' AND {SINCE}
            GROUP BY action
            ORDER BY count(*) DESC, action
            """,
            {"tz": IST, "days": days, "fine": list(FINE_STATUSES)},
        ).fetchall()
    return [tuple(r) for r in rows]


def top_people(days: int, limit: int = 10) -> list[tuple[UUID, str, str, str, int, datetime]]:
    """(user id, name, email, role, assistant calls, last call) for the busiest people."""
    with auth_pool().connection() as conn:
        rows = conn.execute(
            f"""
            SELECT u.id, u.name, u.email, u.role, count(*), max(a.ts)
            FROM audit_log a JOIN users u ON u.id = a.user_id
            WHERE a.surface = 'mcp' AND a.{SINCE}
            GROUP BY u.id, u.name, u.email, u.role
            ORDER BY count(*) DESC, u.name
            LIMIT %(limit)s
            """,
            {"tz": IST, "days": days, "limit": limit},
        ).fetchall()
    return [tuple(r) for r in rows]


def assistant_totals(days: int) -> tuple[int, int, int]:
    """(assistant calls, distinct people, problems) over the last `days` days."""
    with auth_pool().connection() as conn:
        row = conn.execute(
            f"""
            SELECT count(*), count(DISTINCT user_id),
                   count(*) FILTER (WHERE NOT (status = ANY(%(fine)s)))
            FROM audit_log
            WHERE surface = 'mcp' AND {SINCE}
            """,
            {"tz": IST, "days": days, "fine": list(FINE_STATUSES)},
        ).fetchone()
    return tuple(row)


def active_keys() -> int:
    """Usable access keys right now, across everyone whose account is on."""
    with auth_pool().connection() as conn:
        return conn.execute(
            """
            SELECT count(*) FROM api_keys k JOIN users u ON u.id = k.user_id
            WHERE k.revoked_at IS NULL AND (k.expires_at IS NULL OR k.expires_at > now())
              AND u.disabled_at IS NULL
            """
        ).fetchone()[0]
