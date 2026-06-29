"""Add timezone_iana column to tenants table (T1.4 — Deadline/Timezone Handling)

Revision ID: 0011
Revises: 0010
Create Date: 2026-06-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    """Check if a column already exists in a table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = inspector.get_columns(table)
    return any(c['name'] == column for c in columns)


def upgrade() -> None:
    """Add timezone_iana column to tenants table for deadline calculation."""

    # Add timezone_iana column if not exists
    if not _column_exists("tenants", "timezone_iana"):
        op.add_column(
            "tenants",
            sa.Column("timezone_iana", sa.String(64), nullable=False, server_default="UTC"),
        )


def downgrade() -> None:
    """Remove timezone_iana column."""

    if _column_exists("tenants", "timezone_iana"):
        op.drop_column("tenants", "timezone_iana")
