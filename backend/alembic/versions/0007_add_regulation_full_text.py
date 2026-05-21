"""Add full_text, source_url, source_hash, tenant_id to regulations

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-21

Idempotent: uses inspector to check existing columns before adding.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_columns(table: str) -> set[str]:
    """Return the set of column names currently present in *table*."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {col["name"] for col in inspector.get_columns(table)}


def upgrade() -> None:
    existing = _existing_columns("regulations")

    if "full_text" not in existing:
        op.add_column(
            "regulations",
            sa.Column("full_text", sa.Text(), nullable=True),
        )

    if "source_url" not in existing:
        op.add_column(
            "regulations",
            sa.Column("source_url", sa.String(length=1024), nullable=True),
        )

    if "source_hash" not in existing:
        op.add_column(
            "regulations",
            sa.Column("source_hash", sa.String(length=64), nullable=True),
        )

    if "tenant_id" not in existing:
        op.add_column(
            "regulations",
            sa.Column("tenant_id", sa.String(length=64), nullable=True),
        )
        op.create_index("ix_regulation_tenant_id", "regulations", ["tenant_id"])


def downgrade() -> None:
    existing = _existing_columns("regulations")

    if "tenant_id" in existing:
        op.drop_index("ix_regulation_tenant_id", table_name="regulations")
        op.drop_column("regulations", "tenant_id")

    if "source_hash" in existing:
        op.drop_column("regulations", "source_hash")

    if "source_url" in existing:
        op.drop_column("regulations", "source_url")

    if "full_text" in existing:
        op.drop_column("regulations", "full_text")
