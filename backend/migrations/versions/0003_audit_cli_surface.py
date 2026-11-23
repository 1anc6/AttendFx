"""Allow 'cli' as an audit surface, for operator actions such as issuing or revoking keys.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-23
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE audit_log DROP CONSTRAINT audit_log_surface_check")
    op.execute(
        "ALTER TABLE audit_log ADD CONSTRAINT audit_log_surface_check "
        "CHECK (surface IN ('mcp', 'api', 'cli'))"
    )


def downgrade() -> None:
    op.execute("DELETE FROM audit_log WHERE surface = 'cli'")
    op.execute("ALTER TABLE audit_log DROP CONSTRAINT audit_log_surface_check")
    op.execute(
        "ALTER TABLE audit_log ADD CONSTRAINT audit_log_surface_check "
        "CHECK (surface IN ('mcp', 'api'))"
    )
