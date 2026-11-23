"""Attendance queries. Always called inside `rls_connection`, so RLS decides which rows exist."""

from datetime import date, timedelta
from uuid import UUID

import psycopg

IST = "Asia/Kolkata"


def _date_conditions(from_date: date | None, to_date: date | None) -> tuple[list[str], list]:
    """Filters on s.starts_at for whole Asia/Kolkata calendar days."""
    conditions: list[str] = []
    params: list = []
    if from_date:
        conditions.append("s.starts_at >= (%s::date)::timestamp AT TIME ZONE %s")
        params += [from_date, IST]
    if to_date:
        conditions.append("s.starts_at < ((%s::date)::timestamp AT TIME ZONE %s)")
        params += [to_date + timedelta(days=1), IST]
    return conditions, params


def status_counts(
    conn: psycopg.Connection,
    *,
    student_id: UUID,
    course_code: str | None,
    from_date: date | None,
    to_date: date | None,
) -> list[tuple[str, str, str, int]]:
    """Rows of (course_code, course_title, status, count) for one student."""
    conditions = ["a.student_id = %s"]
    params: list = [student_id]
    if course_code:
        conditions.append("c.code = %s")
        params.append(course_code)
    date_conditions, date_params = _date_conditions(from_date, to_date)
    conditions += date_conditions
    params += date_params

    sql = f"""
        SELECT c.code, c.title, a.status, count(*)
        FROM attendance_records a
        JOIN class_sessions s ON s.id = a.class_session_id
        JOIN courses c ON c.id = s.course_id
        WHERE {" AND ".join(conditions)}
        GROUP BY c.code, c.title, a.status
        ORDER BY c.code
    """
    return conn.execute(sql, params).fetchall()


def per_student_counts(
    conn: psycopg.Connection,
    *,
    course_id: UUID,
    from_date: date | None,
    to_date: date | None,
) -> list[tuple[UUID, str, str, int]]:
    """Rows of (student_id, student_name, status, count) for one course."""
    date_conditions, date_params = _date_conditions(from_date, to_date)
    conditions = ["s.course_id = %s", *date_conditions]
    sql = f"""
        SELECT a.student_id, u.name, a.status, count(*)
        FROM attendance_records a
        JOIN class_sessions s ON s.id = a.class_session_id
        JOIN users u ON u.id = a.student_id
        WHERE {" AND ".join(conditions)}
        GROUP BY a.student_id, u.name, a.status
    """
    return conn.execute(sql, [course_id, *date_params]).fetchall()


def sessions_with_records(
    conn: psycopg.Connection,
    *,
    course_id: UUID,
    from_date: date | None,
    to_date: date | None,
) -> int:
    date_conditions, date_params = _date_conditions(from_date, to_date)
    conditions = ["s.course_id = %s", *date_conditions]
    sql = f"""
        SELECT count(DISTINCT a.class_session_id)
        FROM attendance_records a JOIN class_sessions s ON s.id = a.class_session_id
        WHERE {" AND ".join(conditions)}
    """
    return conn.execute(sql, [course_id, *date_params]).fetchone()[0]


def enrolled_count(conn: psycopg.Connection, course_id: UUID) -> int:
    return conn.execute(
        "SELECT count(*) FROM enrolments WHERE course_id = %s", (course_id,)
    ).fetchone()[0]


def min_attendance_percent(conn: psycopg.Connection) -> float | None:
    row = conn.execute("SELECT value FROM settings WHERE key = 'attendance_min_percent'").fetchone()
    return float(row[0]) if row else None
