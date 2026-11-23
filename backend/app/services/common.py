"""Rules shared by every tool: validation, role checks, the attendance percent formula."""

import re
from datetime import date

from app.db.pools import Identity

COURSE_CODE = re.compile(r"^[A-Z]{2,4}[0-9]{3}$")
TERM = re.compile(r"^[0-9]{4}-[A-Za-z]{3,10}$")
MAX_SPAN_DAYS = 366
STATUSES = ("present", "absent", "late", "excused")

# One message for "not allowed" and "does not exist", so callers cannot probe for records.
NO_RECORDS = "No attendance records were found for that request."

PERCENT_RULE = "attended_percent = (present + late) / (all sessions - excused) * 100"


class UserError(Exception):
    """A problem with the request itself. The message is safe to show to the caller."""


class Denied(UserError):
    """The caller's role may not use this tool. Says nothing about any record."""


def require_staff(identity: Identity) -> None:
    if identity.role not in ("teacher", "admin"):
        raise Denied("This tool is only available to teachers and admins.")


def validate_course_code(code: str | None) -> None:
    if code is not None and not COURSE_CODE.match(code):
        raise UserError("course_code must look like CSE301: 2-4 capital letters then 3 digits.")


def validate_term(term: str | None) -> None:
    if term is not None and not TERM.match(term):
        raise UserError("term must look like 2026-Autumn.")


def validate_dates(from_date: date | None, to_date: date | None) -> None:
    if from_date and to_date:
        if from_date > to_date:
            raise UserError("from_date must be on or before to_date.")
        if (to_date - from_date).days > MAX_SPAN_DAYS:
            raise UserError(f"The date range can be at most {MAX_SPAN_DAYS} days.")


def zero_counts() -> dict[str, int]:
    return dict.fromkeys(STATUSES, 0)


def attended_percent(counts: dict[str, int]) -> float | None:
    """The single place the attendance formula lives. None when nothing countable exists."""
    total = sum(counts[s] for s in STATUSES)
    counted = total - counts["excused"]
    return round(100 * (counts["present"] + counts["late"]) / counted, 1) if counted else None


def period(from_date: date | None, to_date: date | None) -> dict[str, str | None]:
    return {
        "from_date": from_date.isoformat() if from_date else None,
        "to_date": to_date.isoformat() if to_date else None,
        "timezone": "Asia/Kolkata",
    }
