"""Attendance queries. Always called inside `rls_connection`, so RLS decides which rows exist."""

from datetime import date, datetime, timedelta
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


def term_enrolments(conn: psycopg.Connection, term: str) -> list[tuple]:
    """One row per enrolment in the term's courses: (student_id, student_name, course_code,
    course_title, teacher_name, present, absent, late, excused). Enrolments with no records yet
    come back with zero counts. RLS decides which enrolments and records the caller sees."""
    return conn.execute(
        """
        SELECT e.student_id, su.name, c.code, c.title, tu.name,
               count(a.id) FILTER (WHERE a.status = 'present'),
               count(a.id) FILTER (WHERE a.status = 'absent'),
               count(a.id) FILTER (WHERE a.status = 'late'),
               count(a.id) FILTER (WHERE a.status = 'excused')
        FROM enrolments e
        JOIN courses c ON c.id = e.course_id AND c.term = %s
        JOIN users su ON su.id = e.student_id
        LEFT JOIN users tu ON tu.id = c.teacher_id
        LEFT JOIN class_sessions s ON s.course_id = c.id
        LEFT JOIN attendance_records a
               ON a.class_session_id = s.id AND a.student_id = e.student_id
        GROUP BY e.student_id, su.name, c.code, c.title, tu.name
        """,
        (term,),
    ).fetchall()


def fortnight_counts(
    conn: psycopg.Connection, term: str, starts_on: date, student_id: UUID | None = None
) -> list[tuple[int, str, int]]:
    """(fortnight number from the term start, status, count) for every record in the term,
    or only one student's records when `student_id` is given."""
    student_filter = "AND a.student_id = %s" if student_id else ""
    params: list = [IST, starts_on, term] + ([student_id] if student_id else [])
    return conn.execute(
        f"""
        SELECT ((s.starts_at AT TIME ZONE %s)::date - %s::date) / 14, a.status, count(*)
        FROM attendance_records a
        JOIN class_sessions s ON s.id = a.class_session_id
        JOIN courses c ON c.id = s.course_id
        WHERE c.term = %s {student_filter}
        GROUP BY 1, 2
        ORDER BY 1
        """,
        params,
    ).fetchall()


def student_courses(
    conn: psycopg.Connection, *, term: str, student_id: UUID, now: datetime
) -> list[tuple]:
    """One row per course the student is enrolled in this term: (code, title, teacher_name,
    present, absent, late, excused, sessions_to_come). Courses with no records yet come back
    with zero counts. A session still to come is one after `now` with no mark for this student,
    so a session marked ahead of time is never counted twice."""
    return conn.execute(
        """
        SELECT c.code, c.title, tu.name,
               count(a.id) FILTER (WHERE a.status = 'present'),
               count(a.id) FILTER (WHERE a.status = 'absent'),
               count(a.id) FILTER (WHERE a.status = 'late'),
               count(a.id) FILTER (WHERE a.status = 'excused'),
               (SELECT count(*) FROM class_sessions f
                WHERE f.course_id = c.id AND f.starts_at > %(now)s
                  AND NOT EXISTS (
                      SELECT 1 FROM attendance_records r
                      WHERE r.class_session_id = f.id AND r.student_id = %(student)s
                  ))
        FROM enrolments e
        JOIN courses c ON c.id = e.course_id AND c.term = %(term)s
        LEFT JOIN users tu ON tu.id = c.teacher_id
        LEFT JOIN class_sessions s ON s.course_id = c.id
        LEFT JOIN attendance_records a
               ON a.class_session_id = s.id AND a.student_id = e.student_id
        WHERE e.student_id = %(student)s
        GROUP BY c.id, c.code, c.title, tu.name
        ORDER BY c.code
        """,
        {"term": term, "student": student_id, "now": now},
    ).fetchall()


def recent_records(
    conn: psycopg.Connection, *, term: str, student_id: UUID, limit: int
) -> list[tuple[datetime, str, str, str]]:
    """The student's latest marked sessions this term: (starts_at, code, title, status)."""
    return conn.execute(
        """
        SELECT s.starts_at, c.code, c.title, a.status
        FROM attendance_records a
        JOIN class_sessions s ON s.id = a.class_session_id
        JOIN courses c ON c.id = s.course_id AND c.term = %s
        WHERE a.student_id = %s
        ORDER BY s.starts_at DESC
        LIMIT %s
        """,
        (term, student_id, limit),
    ).fetchall()


def student_course_sessions(
    conn: psycopg.Connection, *, term: str, student_id: UUID, course_code: str
) -> list[tuple[datetime, datetime, str | None]] | None:
    """Every session of one course the student is enrolled in, with the student's mark or None.
    Returns None when there is no such enrolment (or RLS hides it)."""
    enrolled = conn.execute(
        """
        SELECT c.id FROM enrolments e JOIN courses c ON c.id = e.course_id
        WHERE e.student_id = %s AND c.code = %s AND c.term = %s
        """,
        (student_id, course_code, term),
    ).fetchone()
    if enrolled is None:
        return None
    return conn.execute(
        """
        SELECT s.starts_at, s.ends_at, a.status
        FROM class_sessions s
        LEFT JOIN attendance_records a ON a.class_session_id = s.id AND a.student_id = %s
        WHERE s.course_id = %s
        ORDER BY s.starts_at
        """,
        (student_id, enrolled[0]),
    ).fetchall()


def term_course_count(conn: psycopg.Connection, term: str) -> int:
    return conn.execute("SELECT count(*) FROM courses WHERE term = %s", (term,)).fetchone()[0]


def min_attendance_percent(conn: psycopg.Connection) -> float | None:
    row = conn.execute("SELECT value FROM settings WHERE key = 'attendance_min_percent'").fetchone()
    return float(row[0]) if row else None
