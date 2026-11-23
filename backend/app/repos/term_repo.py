"""Term calendar queries (public catalogue data)."""

from datetime import date

import psycopg


def all_terms(conn: psycopg.Connection) -> list[tuple[str, date, date]]:
    return conn.execute("SELECT name, starts_on, ends_on FROM terms ORDER BY starts_on").fetchall()


def current_term(conn: psycopg.Connection, today: date) -> tuple[str, date, date] | None:
    """The term containing `today`; else the latest one already started; else the next one."""
    return conn.execute(
        """
        SELECT name, starts_on, ends_on FROM terms
        ORDER BY (%(d)s BETWEEN starts_on AND ends_on) DESC,
                 (starts_on <= %(d)s) DESC,
                 CASE WHEN starts_on <= %(d)s THEN starts_on END DESC NULLS LAST,
                 starts_on
        LIMIT 1
        """,
        {"d": today},
    ).fetchone()


def holidays(conn: psycopg.Connection, term: str) -> list[tuple[date, str]]:
    return conn.execute(
        "SELECT day, name FROM term_holidays WHERE term = %s ORDER BY day", (term,)
    ).fetchall()


def catalogue(conn: psycopg.Connection, limit: int) -> list[tuple[str, str, str, str]]:
    """(department, code, title, term), grouped for display."""
    return conn.execute(
        """
        SELECT department, code, title, term FROM courses
        ORDER BY department, code, term DESC
        LIMIT %s
        """,
        (limit,),
    ).fetchall()


def course_count(conn: psycopg.Connection) -> int:
    return conn.execute("SELECT count(*) FROM courses").fetchone()[0]
