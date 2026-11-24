"""Admin dashboards: Overview (attendance this term and assistant use), Activity (the audit log)
and Usage (assistant calls over time, by tool and by person).

Only admins. Attendance figures are read through row-level security as the admin, exactly as
the admin's own MCP tools would see them. The audit log is read as `afx_auth`, which sees every
row, so the role check here matters as much as the one on the route.

Nothing here writes, and reading a dashboard is not itself audited.
"""

from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from app.db.pools import Identity, rls_connection
from app.repos import admin_repo, attendance_repo, people_repo, term_repo
from app.services.common import PERCENT_RULE, STATUSES, Denied, UserError, attended_percent
from app.services.staff import DEFAULT_MIN_PERCENT

IST = ZoneInfo("Asia/Kolkata")
USAGE_WINDOWS = (7, 30, 90)
HIGH_PERCENT = 90.0
AT_RISK_MARGIN = 10.0  # this far under the minimum is "at risk"; closer is "watch"


def _require_admin(actor: Identity) -> None:
    if actor.role != "admin":
        raise Denied("Only admins can see this.")


def _today() -> date:
    return datetime.now(IST).date()


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


# ----------------------------------------------------------------------------- Overview


def fortnight_series(rows: list[tuple[int, str, int]], starts_on: date, ends_on: date, today: date):
    """Attendance percent per fortnight of the term, up to the one containing today."""
    last = (min(today, ends_on) - starts_on).days // 14
    buckets: dict[int, dict[str, int]] = {}
    for n, status, count in rows:
        if 0 <= n <= last:
            buckets.setdefault(n, dict.fromkeys(STATUSES, 0))[status] = count
    series = []
    for n in range(last + 1):
        counts = buckets.get(n, dict.fromkeys(STATUSES, 0))
        start = starts_on + timedelta(days=14 * n)
        series.append(
            {
                "starts_on": start.isoformat(),
                "records": sum(counts.values()),
                "attended_percent": attended_percent(counts),
            }
        )
    return series


def _enrolment(row: tuple) -> dict[str, Any]:
    student_id, student, code, title, teacher, present, absent, late, excused = row
    counts = {"present": present, "absent": absent, "late": late, "excused": excused}
    total = sum(counts.values())
    return {
        "student_id": str(student_id),
        "student_name": student,
        "course_code": code,
        "course_title": title,
        "teacher_name": teacher,
        "attended": present + late,
        "counted_sessions": total - excused,
        "attended_percent": attended_percent(counts),
        "_counts": counts,
    }


def overview(actor: Identity, *, today: date | None = None) -> dict[str, Any]:
    _require_admin(actor)
    today = today or _today()
    calls, callers, problems = admin_repo.assistant_totals(7)
    assistant = {
        "days": 7,
        "calls": calls,
        "people": callers,
        "problems": problems,
        "active_keys": admin_repo.active_keys(),
    }
    people = people_repo.counts()

    with rls_connection(actor) as conn:
        term = term_repo.current_term(conn, today)
        if term is None:
            return {"term": None, "people": people, "assistant": assistant, "attendance": None}
        name, starts_on, ends_on = term
        minimum = attendance_repo.min_attendance_percent(conn)
        minimum = minimum if minimum is not None else DEFAULT_MIN_PERCENT
        courses = attendance_repo.term_course_count(conn, name)
        enrolments = [_enrolment(r) for r in attendance_repo.term_enrolments(conn, name)]
        fortnight_rows = attendance_repo.fortnight_counts(conn, name, starts_on)

    totals = dict.fromkeys(STATUSES, 0)
    for e in enrolments:
        for s in STATUSES:
            totals[s] += e["_counts"][s]
        del e["_counts"]

    measured = [e for e in enrolments if e["attended_percent"] is not None]
    below = sorted(
        (e for e in measured if e["attended_percent"] < minimum),
        key=lambda e: (e["attended_percent"], e["student_name"], e["course_code"]),
    )
    for e in below:
        e["risk"] = "at_risk" if e["attended_percent"] < minimum - AT_RISK_MARGIN else "watch"

    return {
        "term": {
            "name": name,
            "starts_on": starts_on.isoformat(),
            "ends_on": ends_on.isoformat(),
        },
        "people": people,
        "assistant": assistant,
        "attendance": {
            "courses": courses,
            "minimum_percent": minimum,
            "high_percent": HIGH_PERCENT,
            "overall_percent": attended_percent(totals),
            "funnel": {
                "enrolled": len(enrolments),
                "attended_any": sum(1 for e in enrolments if e["attended"] > 0),
                "at_or_above_minimum": sum(1 for e in measured if e["attended_percent"] >= minimum),
                "at_or_above_high": sum(
                    1 for e in measured if e["attended_percent"] >= HIGH_PERCENT
                ),
            },
            "fortnights": fortnight_series(fortnight_rows, starts_on, ends_on, today),
            "below_minimum": below,
            "students_below_minimum": len({e["student_id"] for e in below}),
            "how_percent_is_calculated": PERCENT_RULE,
        },
    }


# ----------------------------------------------------------------------------- Activity


def activity(
    actor: Identity,
    *,
    surface: str | None = None,
    outcome: str = "all",
    search: str = "",
    page: int = 1,
) -> dict[str, Any]:
    _require_admin(actor)
    if surface is not None and surface not in admin_repo.SURFACES:
        raise UserError("Surface must be mcp, api or cli.")
    if outcome not in ("all", "problems"):
        raise UserError("Outcome must be all or problems.")
    if page < 1:
        raise UserError("Page must be 1 or more.")
    rows, total = admin_repo.activity(
        surface=surface,
        problems_only=outcome == "problems",
        search=search.strip()[:100],
        page=page,
    )
    return {
        "events": [
            {
                "id": r.id,
                "ts": r.ts.isoformat(),
                "surface": r.surface,
                "action": r.action,
                "status": r.status,
                "ok": r.status in admin_repo.FINE_STATUSES,
                "latency_ms": r.latency_ms,
                "person": (
                    {
                        "id": str(r.user_id),
                        "name": r.name,
                        "email": r.email,
                        "role": r.role,
                    }
                    if r.user_id and r.name
                    else None
                ),
                "key_prefix": r.key_prefix,
            }
            for r in rows
        ],
        "total": total,
        "page": page,
        "page_size": admin_repo.PAGE_SIZE,
        "retention_days": 90,
    }


# ----------------------------------------------------------------------------- Usage


def usage(actor: Identity, *, days: int = 30) -> dict[str, Any]:
    _require_admin(actor)
    if days not in USAGE_WINDOWS:
        raise UserError("Days must be 7, 30 or 90.")
    daily = [
        {"day": day, "assistant": mcp, "web": other, "problems": problems}
        for day, mcp, other, problems in admin_repo.daily(days)
    ]
    calls, callers, problems = admin_repo.assistant_totals(days)
    return {
        "days": days,
        "generated_at": datetime.now(UTC).isoformat(),
        "totals": {
            "assistant_calls": calls,
            "people": callers,
            "problems": problems,
            "web_events": sum(d["web"] for d in daily),
        },
        "daily": daily,
        "tools": [
            {
                "action": action,
                "calls": n,
                "problems": bad,
                "median_ms": p50,
                "p95_ms": p95,
            }
            for action, n, bad, p50, p95 in admin_repo.by_tool(days)
        ],
        "people": [
            {
                "id": str(uid),
                "name": name,
                "email": email,
                "role": role,
                "calls": n,
                "last_call_at": _iso(last),
            }
            for uid, name, email, role, n, last in admin_repo.top_people(days)
        ],
    }
