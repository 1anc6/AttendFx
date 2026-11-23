"""Attendance queries. Always called inside `rls_connection`, so RLS decides which rows exist."""

from datetime import date, timedelta
from uuid import UUID

import psycopg

IST = "Asia/Kolkata"


def status_counts(
    conn: psycopg.Connection,
    *,
    student_id: UUID,
    course_code: str | None,
    from_date: date | None,
    to_date: date | None,
) -> list[tuple[str, str, str, int]]:
    """Rows of (course_code, course_title, status, count). Dates are Asia/Kolkata calendar days."""
    conditions = ["a.student_id = %s"]
    params: list = [student_id]
    if course_code:
        conditions.append("c.code = %s")
        params.append(course_code)
    if from_date:
        conditions.append("s.starts_at >= (%s::date)::timestamp AT TIME ZONE %s")
        params += [from_date, IST]
    if to_date:
        conditions.append("s.starts_at < ((%s::date)::timestamp AT TIME ZONE %s)")
        params += [to_date + timedelta(days=1), IST]

    sql = f"""
        SELECT c.code, c.title, a.status, count(*)
        FROM attendance_records a
        JOIN class_sessions s ON s.id = a.class_session_id
        JOIN courses c ON c.id = s.course_id
        WHERE {" AND ".join(conditions)}
        GROUP BY c.code, c.title, a.status
        ORDER BY c.code
    """  # noqa: S608 - only fixed fragments are interpolated; values are bound parameters
    return conn.execute(sql, params).fetchall()
