"""Initial schema: tables, database roles, grants and row-level security.

Revision ID: 0001
Revises:
Create Date: 2026-11-23

See docs/ARCHITECTURE.md sections 4.1 to 4.4.
"""

import re

from alembic import op

from app.config import get_settings

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

APP_ROLES = ("afx_app", "afx_auth", "afx_sync")
SAFE_PASSWORD = re.compile(r"^[A-Za-z0-9._~-]+$")

TABLES = [
    """
    CREATE TABLE users (
        id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        name          text NOT NULL,
        email         text NOT NULL,
        role          text NOT NULL CHECK (role IN ('student', 'teacher', 'admin')),
        password_hash text NOT NULL,
        failed_logins integer NOT NULL DEFAULT 0,
        locked_until  timestamptz,
        created_at    timestamptz NOT NULL DEFAULT now()
    )
    """,
    "CREATE UNIQUE INDEX users_email_lower_key ON users (lower(email))",
    """
    CREATE TABLE api_keys (
        id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id      uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
        name         text NOT NULL,
        prefix       text NOT NULL UNIQUE,
        secret_hash  text NOT NULL,
        expires_at   timestamptz,
        revoked_at   timestamptz,
        last_used_at timestamptz,
        created_at   timestamptz NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX api_keys_user_id_idx ON api_keys (user_id)",
    """
    CREATE TABLE web_sessions (
        id         text PRIMARY KEY,
        user_id    uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
        csrf_token text NOT NULL,
        expires_at timestamptz NOT NULL,
        created_at timestamptz NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE courses (
        id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        code        text NOT NULL,
        title       text NOT NULL,
        department  text NOT NULL,
        credits     integer NOT NULL CHECK (credits > 0),
        term        text NOT NULL,
        description text NOT NULL DEFAULT '',
        teacher_id  uuid NOT NULL REFERENCES users (id),
        UNIQUE (code, term)
    )
    """,
    "CREATE INDEX courses_teacher_id_idx ON courses (teacher_id)",
    """
    CREATE TABLE enrolments (
        id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        student_id uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
        course_id  uuid NOT NULL REFERENCES courses (id) ON DELETE CASCADE,
        UNIQUE (student_id, course_id)
    )
    """,
    "CREATE INDEX enrolments_course_id_idx ON enrolments (course_id)",
    """
    CREATE TABLE class_sessions (
        id        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        course_id uuid NOT NULL REFERENCES courses (id) ON DELETE CASCADE,
        starts_at timestamptz NOT NULL,
        ends_at   timestamptz NOT NULL,
        CHECK (ends_at > starts_at)
    )
    """,
    "CREATE INDEX class_sessions_course_id_idx ON class_sessions (course_id, starts_at)",
    """
    CREATE TABLE attendance_records (
        id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        class_session_id uuid NOT NULL REFERENCES class_sessions (id) ON DELETE CASCADE,
        student_id       uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
        status           text NOT NULL CHECK (status IN ('present', 'absent', 'late', 'excused')),
        UNIQUE (class_session_id, student_id)
    )
    """,
    "CREATE INDEX attendance_student_id_idx ON attendance_records (student_id)",
    """
    CREATE TABLE audit_log (
        id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        ts         timestamptz NOT NULL DEFAULT now(),
        user_id    uuid,
        key_id     uuid,
        surface    text NOT NULL CHECK (surface IN ('mcp', 'api')),
        action     text NOT NULL,
        args_hash  text,
        status     text NOT NULL,
        latency_ms integer,
        request_id text
    )
    """,
    "CREATE INDEX audit_log_ts_idx ON audit_log (ts)",
    """
    CREATE TABLE settings (
        key   text PRIMARY KEY,
        value text NOT NULL
    )
    """,
]

# Fail closed: if the per-request settings are missing, these return NULL and no policy matches.
HELPER_FUNCTIONS = [
    """
    CREATE FUNCTION app_uid() RETURNS uuid
    LANGUAGE sql STABLE
    AS $$ SELECT NULLIF(current_setting('app.user_id', true), '')::uuid $$
    """,
    """
    CREATE FUNCTION app_role() RETURNS text
    LANGUAGE sql STABLE
    AS $$ SELECT NULLIF(current_setting('app.role', true), '') $$
    """,
]

RLS_TABLES = ("users", "enrolments", "attendance_records")

POLICIES = [
    # users: own row, teachers' names, a teacher's own students, everything for admin.
    "CREATE POLICY users_app_self ON users FOR SELECT TO afx_app USING (id = app_uid())",
    # Teachers' names are visible to any identified caller (course details), never to anonymous.
    "CREATE POLICY users_app_teachers ON users FOR SELECT TO afx_app "
    "USING (app_uid() IS NOT NULL AND role = 'teacher')",
    """
    CREATE POLICY users_app_teacher_students ON users FOR SELECT TO afx_app
    USING (
        app_role() = 'teacher'
        AND EXISTS (
            SELECT 1 FROM enrolments e JOIN courses c ON c.id = e.course_id
            WHERE e.student_id = users.id AND c.teacher_id = app_uid()
        )
    )
    """,
    "CREATE POLICY users_app_admin ON users FOR SELECT TO afx_app USING (app_role() = 'admin')",
    "CREATE POLICY users_auth_all ON users FOR ALL TO afx_auth USING (true) WITH CHECK (true)",
    "CREATE POLICY users_sync_all ON users FOR ALL TO afx_sync USING (true) WITH CHECK (true)",
    # enrolments
    "CREATE POLICY enr_app_student ON enrolments FOR SELECT TO afx_app USING (student_id = app_uid())",
    """
    CREATE POLICY enr_app_teacher ON enrolments FOR SELECT TO afx_app
    USING (
        app_role() = 'teacher'
        AND EXISTS (SELECT 1 FROM courses c WHERE c.id = course_id AND c.teacher_id = app_uid())
    )
    """,
    "CREATE POLICY enr_app_admin ON enrolments FOR SELECT TO afx_app USING (app_role() = 'admin')",
    "CREATE POLICY enr_sync_all ON enrolments FOR ALL TO afx_sync USING (true) WITH CHECK (true)",
    # attendance_records (ARCHITECTURE.md 4.4)
    """
    CREATE POLICY att_app_student ON attendance_records FOR SELECT TO afx_app
    USING (app_role() = 'student' AND student_id = app_uid())
    """,
    """
    CREATE POLICY att_app_teacher ON attendance_records FOR SELECT TO afx_app
    USING (
        app_role() = 'teacher'
        AND EXISTS (
            SELECT 1 FROM class_sessions s JOIN courses c ON c.id = s.course_id
            WHERE s.id = class_session_id AND c.teacher_id = app_uid()
        )
    )
    """,
    "CREATE POLICY att_app_admin ON attendance_records FOR SELECT TO afx_app USING (app_role() = 'admin')",
    "CREATE POLICY att_sync_all ON attendance_records FOR ALL TO afx_sync USING (true) WITH CHECK (true)",
]

GRANTS = [
    # afx_app: read-only. Column-limited on users so emails and hashes are never readable.
    "GRANT SELECT (id, name, role) ON users TO afx_app",
    "GRANT SELECT ON courses, class_sessions, settings, enrolments, attendance_records TO afx_app",
    # afx_auth: keys, sessions, audit, and account management. No access to attendance or courses.
    "GRANT SELECT, INSERT, UPDATE ON users TO afx_auth",
    "GRANT SELECT, INSERT, UPDATE ON api_keys TO afx_auth",
    "GRANT SELECT, INSERT, UPDATE, DELETE ON web_sessions TO afx_auth",
    "GRANT SELECT, INSERT ON audit_log TO afx_auth",
    # afx_sync: writes data tables; may prune the audit log. No access to keys or sessions.
    "GRANT SELECT, INSERT, UPDATE, DELETE ON users, courses, enrolments, class_sessions, "
    "attendance_records, settings TO afx_sync",
    "GRANT SELECT, DELETE ON audit_log TO afx_sync",
]


def _create_roles() -> None:
    settings = get_settings()
    passwords = {
        "afx_app": settings.app_password,
        "afx_auth": settings.auth_password,
        "afx_sync": settings.sync_password,
    }
    for role in APP_ROLES:
        op.execute(
            f"""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{role}') THEN
                    CREATE ROLE {role} LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
                END IF;
            END
            $$
            """
        )
        password = passwords[role]
        if password:
            if not SAFE_PASSWORD.match(password):
                raise RuntimeError(f"Password for {role} may only contain letters, digits . _ ~ -")
            op.execute(f"ALTER ROLE {role} PASSWORD '{password}'")


def upgrade() -> None:
    _create_roles()
    for statement in TABLES + HELPER_FUNCTIONS:
        op.execute(statement)
    for table in RLS_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    for statement in POLICIES + GRANTS:
        op.execute(statement)


def downgrade() -> None:
    for table in (
        "settings",
        "audit_log",
        "attendance_records",
        "class_sessions",
        "enrolments",
        "courses",
        "web_sessions",
        "api_keys",
        "users",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
    op.execute("DROP FUNCTION IF EXISTS app_uid()")
    op.execute("DROP FUNCTION IF EXISTS app_role()")
    # Roles are cluster-level objects and are intentionally left in place.
