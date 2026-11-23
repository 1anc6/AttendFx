"""Attendance business rules: who may ask about whom, validation, and summarising."""

import re
from datetime import date
from typing import Any
from uuid import UUID

from app.db.pools import Identity, rls_connection
from app.repos import attendance_repo

COURSE_CODE = re.compile(r"^[A-Z]{2,4}[0-9]{3}$")
MAX_SPAN_DAYS = 366

# One message for "not allowed" and "does not exist", so callers cannot probe for records.
NO_RECORDS = "No attendance records were found for that request."


class UserError(Exception):
    """A problem with the request itself. The message is safe to show to the caller."""


def _validate(course_code: str | None, from_date: date | None, to_date: date | None) -> None:
    if course_code is not None and not COURSE_CODE.match(course_code):
        raise UserError("course_code must look like CSE301: 2-4 capital letters then 3 digits.")
    if from_date and to_date:
        if from_date > to_date:
            raise UserError("from_date must be on or before to_date.")
        if (to_date - from_date).days > MAX_SPAN_DAYS:
            raise UserError(f"The date range can be at most {MAX_SPAN_DAYS} days.")


def _parse_student_id(student_id: str | None) -> UUID | None:
    if student_id is None:
        return None
    try:
        return UUID(student_id)
    except ValueError:
        raise UserError("student_id must be a valid id.") from None


def _percent(attended: int, counted: int) -> float | None:
    return round(100 * attended / counted, 1) if counted else None


def my_attendance(
    identity: Identity,
    *,
    course_code: str | None = None,
    student_id: str | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
) -> dict[str, Any]:
    _validate(course_code, from_date, to_date)
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
        entry = courses.setdefault(
            code,
            {
                "course_code": code,
                "title": title,
                "present": 0,
                "absent": 0,
                "late": 0,
                "excused": 0,
            },
        )
        entry[status] = n

    totals = {"present": 0, "absent": 0, "late": 0, "excused": 0}
    for entry in courses.values():
        entry["total_sessions"] = sum(entry[s] for s in totals)
        entry["attended_percent"] = _percent(
            entry["present"] + entry["late"], entry["total_sessions"] - entry["excused"]
        )
        for s in totals:
            totals[s] += entry[s]
    total_sessions = sum(totals.values())

    return {
        "found": True,
        "student_id": str(target),
        "period": {
            "from_date": from_date.isoformat() if from_date else None,
            "to_date": to_date.isoformat() if to_date else None,
            "timezone": "Asia/Kolkata",
        },
        "courses": list(courses.values()),
        "overall": {
            **totals,
            "total_sessions": total_sessions,
            "attended_percent": _percent(
                totals["present"] + totals["late"], total_sessions - totals["excused"]
            ),
        },
        "how_percent_is_calculated": (
            "attended_percent = (present + late) / (all sessions - excused) * 100"
        ),
    }
