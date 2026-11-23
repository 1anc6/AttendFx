"""Course catalogue queries. Courses and sessions are public to any identified caller."""

import psycopg

IST = "Asia/Kolkata"

_COURSE_COLUMNS = """
    c.id, c.code, c.title, c.department, c.credits, c.term, c.description, u.name AS teacher_name
"""


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def search(
    conn: psycopg.Connection,
    *,
    query: str | None,
    department: str | None,
    term: str | None,
    limit: int,
) -> list[tuple]:
    conditions, params = ["true"], []
    if query:
        pattern = f"%{_escape_like(query)}%"
        conditions.append("(c.code ILIKE %s OR c.title ILIKE %s OR c.department ILIKE %s)")
        params += [pattern, pattern, pattern]
    if department:
        conditions.append("lower(c.department) = lower(%s)")
        params.append(department)
    if term:
        conditions.append("c.term = %s")
        params.append(term)
    params.append(limit)
    sql = f"""
        SELECT c.code, c.title, c.department, c.credits, c.term, u.name
        FROM courses c LEFT JOIN users u ON u.id = c.teacher_id
        WHERE {" AND ".join(conditions)}
        ORDER BY c.term DESC, c.code
        LIMIT %s
    """
    return conn.execute(sql, params).fetchall()


def find(conn: psycopg.Connection, code: str, term: str | None) -> list[tuple]:
    """All terms of a course code (or one term). Columns as in _COURSE_COLUMNS."""
    sql = f"SELECT {_COURSE_COLUMNS} FROM courses c LEFT JOIN users u ON u.id = c.teacher_id "
    if term:
        return conn.execute(sql + "WHERE c.code = %s AND c.term = %s", (code, term)).fetchall()
    return conn.execute(sql + "WHERE c.code = %s ORDER BY c.term DESC", (code,)).fetchall()


def weekly_slots(conn: psycopg.Connection, course_id) -> list[tuple[str, str, str, int]]:
    """(weekday, start HH:MM, end HH:MM, sessions) in India time, most common slot first."""
    return conn.execute(
        """
        SELECT to_char(starts_at AT TIME ZONE %(tz)s, 'FMDay'),
               to_char(starts_at AT TIME ZONE %(tz)s, 'HH24:MI'),
               to_char(ends_at   AT TIME ZONE %(tz)s, 'HH24:MI'),
               count(*)
        FROM class_sessions WHERE course_id = %(id)s
        GROUP BY 1, 2, 3 ORDER BY 4 DESC, 1
        """,
        {"tz": IST, "id": course_id},
    ).fetchall()


def session_span(conn: psycopg.Connection, course_id) -> tuple:
    """(first date, last date, number of sessions) in India time."""
    return conn.execute(
        """
        SELECT min((starts_at AT TIME ZONE %(tz)s)::date),
               max((starts_at AT TIME ZONE %(tz)s)::date),
               count(*)
        FROM class_sessions WHERE course_id = %(id)s
        """,
        {"tz": IST, "id": course_id},
    ).fetchone()
