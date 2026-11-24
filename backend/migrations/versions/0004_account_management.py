"""Account management: turn accounts off, temporary passwords, last sign-in.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-24

- disabled_at: set while an admin has turned the account off. Sign-in, sessions and access
  keys all stop working; turning it back on restores them.
- must_change_password: set when an admin creates the account or resets its password. The
  person can sign in with the temporary password but must choose their own before doing
  anything else.
- last_sign_in_at: shown on the admin People page.

afx_app keeps its column-limited grant (id, name, role), so it cannot read any of these.
"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN disabled_at timestamptz")
    op.execute("ALTER TABLE users ADD COLUMN must_change_password boolean NOT NULL DEFAULT false")
    op.execute("ALTER TABLE users ADD COLUMN last_sign_in_at timestamptz")
    op.execute("CREATE INDEX web_sessions_user_id_idx ON web_sessions (user_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS web_sessions_user_id_idx")
    op.execute("ALTER TABLE users DROP COLUMN last_sign_in_at")
    op.execute("ALTER TABLE users DROP COLUMN must_change_password")
    op.execute("ALTER TABLE users DROP COLUMN disabled_at")
