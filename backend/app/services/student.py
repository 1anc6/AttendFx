"""The student's own attendance page: /api/me/attendance and one course's sessions.

Students only. There is no student id anywhere in the request: the page always shows the
signed-in student, read through row-level security as that student, so the database is the
final check, exactly as for the `my_attendance` tool.

Reading the page is not audited, like the admin dashboards.
"""

import math
from datetime import UTC, date, datetime
from fractions import Fraction
from typing import Any

from app.db.pools import Identity, rls_connection
from app.repos import attendance_repo, term_repo
from app.services.admin import AT_RISK_MARGIN, IST, fortnight_series
from app.services.common import (
    PERCENT_RULE,
    STATUSES,
    Denied,
    UserError,
    attended_percent,
    validate_course_code,
)
from app.services.staff import DEFAULT_MIN_PERCENT

RECENT = 10


class CourseNotFound(UserError):
    """No such course in the student's current enrolments. Same answer for "not yours"."""


def _require_student(actor: Identity) -> None:
    if actor.role != "student":
        raise Denied("Only students have an attendance page.")


def room_left(attended: int, counted: int, remaining: int, minimum_percent: float) -> dict:
    """How much room the student has against the rule for the rest of the term.

    `attended` is present + late, `counted` is marked sessions minus excused, `remaining` is
    sessions still to come. Future sessions are assumed not to be excused. Exact arithmetic,
    so a student exactly on the rule is on it, not a rounding error below it.

    Returns one of:
      {"kind": "spare", "sessions": k}   at or above the rule; k more absences keep it there
      {"kind": "need", "sessions": n}    below the rule; attending the next n gets back to it
      {"kind": "cannot_reach"}           even attending every remaining session falls short
      {"kind": "final"}                  at or above the rule with no sessions left to come
      {"kind": "no_sessions"}            nothing marked and nothing left to come
    """
    m = Fraction(str(minimum_percent)) / 100
    end_total = counted + remaining
    if end_total == 0:
        return {"kind": "no_sessions"}
    if Fraction(attended + remaining, end_total) < m:
        return {"kind": "cannot_reach"}
    if remaining == 0:
        return {"kind": "final"}  # reachable with nothing left means at or above it now
    if counted == 0 or Fraction(attended, counted) >= m:
        spare = math.floor(attended + remaining - m * end_total)
        return {"kind": "spare", "sessions": max(0, min(remaining, spare))}
    # Below now, but reachable: the smallest n with (attended + n) / (counted + n) >= m.
    # m < 1 here, because m == 1 with attended < counted is caught as cannot_reach above.
    need = math.ceil((m * counted - attended) / (1 - m))
    return {"kind": "need", "sessions": need}


def _status(percent: float | None, minimum: float) -> str:
    if percent is None:
        return "no_records"
    if percent >= minimum:
        return "ok"
    return "at_risk" if percent < minimum - AT_RISK_MARGIN else "watch"


def _minimum(conn) -> tuple[float, bool]:
    configured = attendance_repo.min_attendance_percent(conn)
    return (configured, True) if configured is not None else (DEFAULT_MIN_PERCENT, False)


def my_page(actor: Identity, *, now: datetime | None = None) -> dict[str, Any]:
    _require_student(actor)
    now = now or datetime.now(UTC)
    today: date = now.astimezone(IST).date()

    with rls_connection(actor) as conn:
        minimum, rule_set = _minimum(conn)
        term = term_repo.current_term(conn, today)
        if term is None:
            return {
                "term": None,
                "minimum_percent": minimum,
                "rule_set": rule_set,
                "courses": [],
                "recent": [],
                "fortnights": [],
                "overall": None,
                "how_percent_is_calculated": PERCENT_RULE,
            }
        name, starts_on, ends_on = term
        rows = attendance_repo.student_courses(conn, term=name, student_id=actor.user_id, now=now)
        recent = attendance_repo.recent_records(
            conn, term=name, student_id=actor.user_id, limit=RECENT
        )
        fortnight_rows = attendance_repo.fortnight_counts(
            conn, name, starts_on, student_id=actor.user_id
        )

    totals = dict.fromkeys(STATUSES, 0)
    courses = []
    for code, title, teacher, present, absent, late, excused, remaining in rows:
        counts = {"present": present, "absent": absent, "late": late, "excused": excused}
        for s in STATUSES:
            totals[s] += counts[s]
        attended = present + late
        counted = present + absent + late
        percent = attended_percent(counts)
        courses.append(
            {
                "course_code": code,
                "course_title": title,
                "teacher_name": teacher,
                **counts,
                "attended": attended,
                "counted_sessions": counted,
                "attended_percent": percent,
                "remaining_sessions": remaining,
                "status": _status(percent, minimum),
                "room": room_left(attended, counted, remaining, minimum),
            }
        )

    return {
        "term": {"name": name, "starts_on": starts_on.isoformat(), "ends_on": ends_on.isoformat()},
        "minimum_percent": minimum,
        "rule_set": rule_set,
        "overall": {
            **totals,
            "attended": totals["present"] + totals["late"],
            "counted_sessions": totals["present"] + totals["absent"] + totals["late"],
            "attended_percent": attended_percent(totals),
        },
        "courses": courses,
        "recent": [
            {
                "starts_at": starts_at.isoformat(),
                "course_code": code,
                "course_title": title,
                "status": status,
            }
            for starts_at, code, title, status in recent
        ],
        "fortnights": fortnight_series(fortnight_rows, starts_on, ends_on, today),
        "how_percent_is_calculated": PERCENT_RULE,
    }


def my_course(actor: Identity, course_code: str, *, now: datetime | None = None) -> dict[str, Any]:
    """Every session of one of the student's courses this term, with their mark."""
    _require_student(actor)
    validate_course_code(course_code)
    now = now or datetime.now(UTC)

    with rls_connection(actor) as conn:
        term = term_repo.current_term(conn, now.astimezone(IST).date())
        rows = (
            attendance_repo.student_course_sessions(
                conn, term=term[0], student_id=actor.user_id, course_code=course_code
            )
            if term
            else None
        )
    if rows is None:
        raise CourseNotFound("You are not enrolled in that course this term.")

    return {
        "course_code": course_code,
        "sessions": [
            {
                "starts_at": starts_at.isoformat(),
                "ends_at": ends_at.isoformat(),
                # upcoming: not started yet; unmarked: started but no mark recorded
                "status": status or ("upcoming" if starts_at > now else "unmarked"),
            }
            for starts_at, ends_at, status in rows
        ],
    }
