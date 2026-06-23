"""Add DAG/state-machine fields to workflow_steps + updated_at to workflows (M7 fix)

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-23

Idempotent: uses inspector to check existing columns before adding.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_columns(table: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {col["name"] for col in inspector.get_columns(table)}


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    return bind.dialect.has_table(bind, name)


def upgrade() -> None:
    if _table_exists("workflows"):
        existing = _existing_columns("workflows")
        if "updated_at" not in existing:
            op.add_column("workflows", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))

    if _table_exists("workflow_steps"):
        existing = _existing_columns("workflow_steps")
        if "depends_on" not in existing:
            op.add_column(
                "workflow_steps",
                sa.Column("depends_on", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            )
        if "started_at" not in existing:
            op.add_column("workflow_steps", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
        if "completed_at" not in existing:
            op.add_column("workflow_steps", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
        if "due_at" not in existing:
            op.add_column("workflow_steps", sa.Column("due_at", sa.DateTime(timezone=True), nullable=True))
        if "approved_by" not in existing:
            op.add_column("workflow_steps", sa.Column("approved_by", sa.String(length=128), nullable=True))
        if "escalated" not in existing:
            op.add_column("workflow_steps", sa.Column("escalated", sa.Boolean(), nullable=True))


def downgrade() -> None:
    if _table_exists("workflow_steps"):
        existing = _existing_columns("workflow_steps")
        for col in ("escalated", "approved_by", "due_at", "completed_at", "started_at", "depends_on"):
            if col in existing:
                op.drop_column("workflow_steps", col)

    if _table_exists("workflows"):
        existing = _existing_columns("workflows")
        if "updated_at" in existing:
            op.drop_column("workflows", "updated_at")
