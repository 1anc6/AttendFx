"""Phase 0 permission checks: the privacy rule holds at the database level.

These run as the real afx_app role, so they exercise grants and row-level security,
not application code. The full role x table x operation matrix comes in phase 2.
"""

import psycopg
import pytest

from app.worker.seed import uid

STUDENT = uid("user", "student1")
OTHER_STUDENT = uid("user", "student2")
TEACHER = uid("user", "teacher1")
ADMIN = uid("user", "admin")


def count(conn, sql, params=()):
    return conn.execute(sql, params).fetchone()[0]


def test_no_identity_sees_nothing(as_user):
    with as_user(None, None) as conn:
        assert count(conn, "SELECT count(*) FROM attendance_records") == 0
        assert count(conn, "SELECT count(*) FROM enrolments") == 0
        assert count(conn, "SELECT count(*) FROM users") == 0


def test_student_sees_only_own_attendance(as_user, truth):
    expected = count(
        truth, "SELECT count(*) FROM attendance_records WHERE student_id = %s", (STUDENT,)
    )
    assert expected > 0
    with as_user(STUDENT, "student") as conn:
        rows = conn.execute("SELECT DISTINCT student_id FROM attendance_records").fetchall()
        assert rows == [(STUDENT,)]
        assert count(conn, "SELECT count(*) FROM attendance_records") == expected


def test_student_cannot_target_another_student(as_user):
    with as_user(STUDENT, "student") as conn:
        n = count(
            conn, "SELECT count(*) FROM attendance_records WHERE student_id = %s", (OTHER_STUDENT,)
        )
        assert n == 0
        assert count(conn, "SELECT count(*) FROM users WHERE id = %s", (OTHER_STUDENT,)) == 0


def test_teacher_sees_only_own_courses(as_user, truth):
    expected = count(
        truth,
        """SELECT count(*) FROM attendance_records a
           JOIN class_sessions s ON s.id = a.class_session_id
           JOIN courses c ON c.id = s.course_id WHERE c.teacher_id = %s""",
        (TEACHER,),
    )
    total = count(truth, "SELECT count(*) FROM attendance_records")
    assert 0 < expected < total
    with as_user(TEACHER, "teacher") as conn:
        assert count(conn, "SELECT count(*) FROM attendance_records") == expected
        foreign = count(
            conn,
            """SELECT count(*) FROM attendance_records a
               JOIN class_sessions s ON s.id = a.class_session_id
               JOIN courses c ON c.id = s.course_id WHERE c.teacher_id <> %s""",
            (TEACHER,),
        )
        assert foreign == 0


def test_admin_reads_everything(as_user, truth):
    total = count(truth, "SELECT count(*) FROM attendance_records")
    with as_user(ADMIN, "admin") as conn:
        assert count(conn, "SELECT count(*) FROM attendance_records") == total


def test_claiming_a_role_without_matching_identity_gives_nothing(as_user):
    """A student id presented with the 'teacher' role matches no course, so no rows."""
    with as_user(STUDENT, "teacher") as conn:
        assert count(conn, "SELECT count(*) FROM attendance_records") == 0


def test_identity_does_not_leak_between_transactions(as_user):
    with as_user(ADMIN, "admin") as conn:
        assert count(conn, "SELECT count(*) FROM attendance_records") > 0
    with as_user(None, None) as conn:
        assert count(conn, "SELECT count(*) FROM attendance_records") == 0


def test_app_role_cannot_write_attendance(as_user):
    with as_user(ADMIN, "admin") as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("UPDATE attendance_records SET status = 'present'")


def test_app_role_cannot_touch_keys_or_secrets(as_user):
    with as_user(ADMIN, "admin") as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("SELECT * FROM api_keys")
    with as_user(ADMIN, "admin") as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("SELECT email FROM users")
    with as_user(ADMIN, "admin") as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("SELECT password_hash FROM users")


def test_auth_role_cannot_read_attendance_or_courses(settings, require_db):
    with psycopg.connect(settings.auth_database_url) as conn:
        for table in ("attendance_records", "courses", "enrolments"):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conn.execute(f"SELECT count(*) FROM {table}")
            conn.rollback()


def test_app_role_is_not_privileged(settings, require_db):
    with psycopg.connect(settings.app_database_url) as conn:
        row = conn.execute(
            "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"
        ).fetchone()
        assert row == (False, False)
