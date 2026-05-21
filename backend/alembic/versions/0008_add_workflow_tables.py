"""Add M7 workflow and workflow_steps tables

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-21
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing = {t for t in inspector.get_table_names()}

    if "workflowstatus" not in {e["name"] for e in inspector.get_enums()}:
        sa.Enum(
            "pending", "running", "approval_required", "completed", "failed", "escalated",
            name="workflowstatus",
        ).create(conn)

    if "workflows" not in existing:
        op.create_table(
            "workflows",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.String(64), nullable=False, index=True),
            sa.Column("workflow_type", sa.String(64), nullable=False),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("trigger_source", sa.String(128), nullable=True),
            sa.Column("severity", sa.String(32), server_default="medium"),
            sa.Column(
                "status",
                sa.Enum(
                    "pending", "running", "approval_required", "completed", "failed", "escalated",
                    name="workflowstatus",
                    create_type=False,
                ),
                server_default="pending",
            ),
            sa.Column("assigned_to", sa.String(128), nullable=True),
            sa.Column("metadata", postgresql.JSONB, server_default="{}"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    if "workflow_steps" not in existing:
        op.create_table(
            "workflow_steps",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "workflow_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("workflows.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("step_type", sa.String(64), nullable=False),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("status", sa.String(32), server_default="pending"),
            sa.Column("requires_approval", sa.Boolean, server_default="false"),
            sa.Column("completed", sa.Boolean, server_default="false"),
            sa.Column("order_index", sa.Integer, server_default="0"),
            sa.Column("payload", postgresql.JSONB, server_default="{}"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )


def downgrade() -> None:
    op.drop_table("workflow_steps")
    op.drop_table("workflows")
    sa.Enum(name="workflowstatus").drop(op.get_bind())
