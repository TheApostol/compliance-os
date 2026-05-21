"""Add tenants table

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    return bind.dialect.has_table(bind, name)


def upgrade() -> None:
    if not _table_exists("tenants"):
        op.create_table(
            "tenants",
            sa.Column("id", sa.String(), primary_key=True, nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("slug", sa.String(), nullable=False, unique=True),
            sa.Column("data_residency_policy", sa.String(), nullable=True, server_default="global"),
            sa.Column("is_active", sa.Boolean(), nullable=True, server_default="true"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=True,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "settings",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            ),
        )
        op.create_index(
            "ix_tenants_slug",
            "tenants",
            ["slug"],
            unique=True,
        )


def downgrade() -> None:
    if _table_exists("tenants"):
        op.drop_index("ix_tenants_slug", table_name="tenants")
        op.drop_table("tenants")
