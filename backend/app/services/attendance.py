"""Student-facing attendance tools: my_attendance and attendance_rule."""

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
    validate_course_code,
    validate_dates,
    zero_counts,
)


def _parse_student_id(student_id: str | None) -> UUID | None:
    if student_id is None:
        return None
    try:
        return UUID(student_id)
    except ValueError:
        raise UserError("student_id must be a valid id.") from None


def my_attendance(
    identity: Identity,
    *,
    course_code: str | None = None,
    student_id: str | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
) -> dict[str, Any]:
    validate_course_code(course_code)
    validate_dates(from_date, to_date)
    requested = _parse_student_id(student_id)

    if identity.role == "student":
        if requested is not None and requested != identity.user_id:
            return {"found": False, "message": NO_RECORDS}  # same answer as "no data"
        target = identity.user_id
    else:  # teacher or admin
        if requested is None:
            raise UserError("student_id is required for teachers and admins.")
        target = requested

    with rls_connection(identity) as conn:
        rows = attendance_repo.status_counts(
            conn,
            student_id=target,
            course_code=course_code,
            from_date=from_date,
            to_date=to_date,
        )

    if not rows:
        return {"found": False, "message": NO_RECORDS}

    courses: dict[str, dict[str, Any]] = {}
    for code, title, status, n in rows:
        entry = courses.setdefault(code, {"course_code": code, "title": title, **zero_counts()})
        entry[status] = n

    totals = zero_counts()
    for entry in courses.values():
        entry["total_sessions"] = sum(entry[s] for s in STATUSES)
        entry["attended_percent"] = attended_percent(entry)
        for s in STATUSES:
            totals[s] += entry[s]

    return {
        "found": True,
        "student_id": str(target),
        "period": period(from_date, to_date),
        "courses": list(courses.values()),
        "overall": {
            **totals,
            "total_sessions": sum(totals.values()),
            "attended_percent": attended_percent(totals),
        },
        "how_percent_is_calculated": PERCENT_RULE,
    }


def attendance_rule(identity: Identity) -> dict[str, Any]:
    with rls_connection(identity) as conn:
        minimum = attendance_repo.min_attendance_percent(conn)
    if minimum is None:
        return {
            "configured": False,
            "message": "The minimum attendance rule has not been set yet.",
            "how_percent_is_calculated": PERCENT_RULE,
        }
    return {
        "configured": True,
        "minimum_percent": minimum,
        "rule": f"Students must attend at least {minimum:g}% of classes in each course.",
        "how_percent_is_calculated": PERCENT_RULE,
        "note": "Late counts as attended. Excused sessions are left out of the calculation.",
    }
