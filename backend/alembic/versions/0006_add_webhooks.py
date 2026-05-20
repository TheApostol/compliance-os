"""Add webhook_configs table

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    return bind.dialect.has_table(bind, name)


def _enum_exists(name: str) -> bool:
    bind = op.get_bind()
    return bind.dialect.has_type(bind, name)


def upgrade() -> None:
    # Create the webhookevent enum type if it doesn't exist
    if not _enum_exists("webhookevent"):
        webhookevent = sa.Enum(
            "crawl.complete",
            "deadline.alert",
            "regulation.parsed",
            name="webhookevent",
        )
        webhookevent.create(op.get_bind(), checkfirst=True)

    if not _table_exists("webhook_configs"):
        op.create_table(
            "webhook_configs",
            sa.Column("id", sa.String(), primary_key=True, nullable=False),
            sa.Column("tenant_id", sa.String(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("url", sa.String(), nullable=False),
            sa.Column("secret", sa.String(), nullable=True),
            sa.Column(
                "events",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            ),
            sa.Column("is_active", sa.Boolean(), nullable=True, server_default="true"),
            sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_status_code", sa.Integer(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=True,
                server_default=sa.func.now(),
            ),
        )
        op.create_index("ix_webhooks_tenant", "webhook_configs", ["tenant_id"])


def downgrade() -> None:
    if _table_exists("webhook_configs"):
        op.drop_index("ix_webhooks_tenant", table_name="webhook_configs")
        op.drop_table("webhook_configs")

    if _enum_exists("webhookevent"):
        sa.Enum(name="webhookevent").drop(op.get_bind(), checkfirst=True)
