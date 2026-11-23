"""Term calendar: terms and their holidays.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-23

Read by the term-calendar and course-list-guide MCP resources. Public catalogue data, so no RLS:
any identified caller may read it, only the sync worker may write it.
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE terms (
            name      text PRIMARY KEY CHECK (name ~ '^[0-9]{4}-[A-Za-z]{3,10}$'),
            starts_on date NOT NULL,
            ends_on   date NOT NULL,
            CHECK (ends_on >= starts_on)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE term_holidays (
            term text NOT NULL REFERENCES terms (name) ON DELETE CASCADE,
            day  date NOT NULL,
            name text NOT NULL,
            PRIMARY KEY (term, day)
        )
        """
    )
    op.execute("GRANT SELECT ON terms, term_holidays TO afx_app")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON terms, term_holidays TO afx_sync")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS term_holidays")
    op.execute("DROP TABLE IF EXISTS terms")
