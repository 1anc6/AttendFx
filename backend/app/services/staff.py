"""Teacher and admin tools: course_attendance_summary and low_attendance_list.

Teachers only ever see their own courses: RLS hides other courses' attendance rows, so asking
about someone else's course gives the same "no records" answer as a course with no data.
"""

from datetime import date
from typing import Any
from uuid import UUID

from app.db.pools import Identity, rls_connection
from app.repos import attendance_repo
from app.services.common import (
    NO_RECORDS,
    PERCENT_RULE,
    STATUSES,
    UserError,
    attended_percent,
    period,
    require_staff,
    validate_dates,
    zero_counts,
)
from app.services.courses import course_summary, resolve_course

DEFAULT_MIN_PERCENT = 75.0  # used only if the settings row is missing


def _minimum(conn) -> float:
    configured = attendance_repo.min_attendance_percent(conn)
    return configured if configured is not None else DEFAULT_MIN_PERCENT


def _per_student(rows: list[tuple]) -> dict[UUID, dict[str, Any]]:
    students: dict[UUID, dict[str, Any]] = {}
    for student_id, name, status, n in rows:
        entry = students.setdefault(
            student_id, {"student_id": str(student_id), "name": name, **zero_counts()}
        )
        entry[status] = n
    for entry in students.values():
        entry["total_sessions"] = sum(entry[s] for s in STATUSES)
        entry["attended_percent"] = attended_percent(entry)
    return students


def course_attendance_summary(
    identity: Identity,
    *,
    course_code: str,
    term: str | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
) -> dict[str, Any]:
    require_staff(identity)
    validate_dates(from_date, to_date)

    with rls_connection(identity) as conn:
        course = resolve_course(conn, course_code, term)
        rows = attendance_repo.per_student_counts(
            conn, course_id=course[0], from_date=from_date, to_date=to_date
        )
        if not rows:
            return {"found": False, "message": NO_RECORDS}
        sessions = attendance_repo.sessions_with_records(
            conn, course_id=course[0], from_date=from_date, to_date=to_date
        )
        enrolled = attendance_repo.enrolled_count(conn, course[0])
        minimum = _minimum(conn)

    students = _per_student(rows)
    totals = zero_counts()
    for entry in students.values():
        for s in STATUSES:
            totals[s] += entry[s]
    percents = [
        e["attended_percent"] for e in students.values() if e["attended_percent"] is not None
    ]

    return {
        "found": True,
        "course": course_summary(course),
        "period": period(from_date, to_date),
        "enrolled_students": enrolled,
        "students_with_records": len(students),
        "sessions_recorded": sessions,
        "totals": {**totals, "attended_percent": attended_percent(totals)},
        "average_student_percent": round(sum(percents) / len(percents), 1) if percents else None,
        "minimum_percent": minimum,
        "students_below_minimum": sum(1 for p in percents if p < minimum),
        "how_percent_is_calculated": PERCENT_RULE,
    }


def low_attendance_list(
    identity: Identity,
    *,
    course_code: str,
    threshold_percent: float | None = None,
    term: str | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
) -> dict[str, Any]:
    require_staff(identity)
    validate_dates(from_date, to_date)
    if threshold_percent is not None and not 0 <= threshold_percent <= 100:
        raise UserError("threshold_percent must be between 0 and 100.")

    with rls_connection(identity) as conn:
        course = resolve_course(conn, course_code, term)
        rows = attendance_repo.per_student_counts(
            conn, course_id=course[0], from_date=from_date, to_date=to_date
        )
        if not rows:
            return {"found": False, "message": NO_RECORDS}
        if threshold_percent is None:
            threshold_percent = _minimum(conn)

    below = [
        e
        for e in _per_student(rows).values()
        if e["attended_percent"] is not None and e["attended_percent"] < threshold_percent
    ]
    below.sort(key=lambda e: (e["attended_percent"], e["name"]))
    return {
        "found": True,
        "course": course_summary(course),
        "period": period(from_date, to_date),
        "threshold_percent": threshold_percent,
        "count": len(below),
        "students": below,
        "how_percent_is_calculated": PERCENT_RULE,
    }
