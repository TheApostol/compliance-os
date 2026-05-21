"""Add ai_model_registry and compliance_cases tables (missing from previous migrations)

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-21

Idempotent: uses inspector.get_table_names() check before creating, same pattern as 0007/0008.
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing = {t for t in inspector.get_table_names()}

    # ── ai_model_registry ────────────────────────────────────────────
    if "ai_model_registry" not in existing:
        op.create_table(
            "ai_model_registry",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
            ),
            sa.Column("model_id", sa.String(255), nullable=False, index=True),
            sa.Column("provider", sa.String(64), nullable=False),
            sa.Column("version_hash", sa.String(64), nullable=True),
            sa.Column("use_cases", postgresql.JSONB, server_default="[]"),
            sa.Column("benchmark_scores", postgresql.JSONB, server_default="{}"),
            sa.Column("approved_for_production", sa.Boolean, server_default="false"),
            sa.Column("approved_by_user_id", sa.String(64), nullable=True),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("deprecated", sa.Boolean, server_default="false"),
            sa.Column("notes", sa.String, nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
            ),
        )

    # ── compliance_cases ─────────────────────────────────────────────
    # Ensure required enum types exist before creating the table.
    enums = {e["name"] for e in inspector.get_enums()}

    if "risklevel" not in enums:
        sa.Enum(
            "LOW", "MEDIUM", "HIGH", "CRITICAL",
            name="risklevel",
        ).create(conn)

    if "casestatus" not in enums:
        sa.Enum(
            "OPEN",
            "UNDER_REVIEW",
            "ESCALATED",
            "CLOSED_NO_ACTION",
            "REPORTED",
            "REJECTED",
            name="casestatus",
        ).create(conn)

    if "compliance_cases" not in existing:
        op.create_table(
            "compliance_cases",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
            ),
            sa.Column(
                "tenant_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("tenants.id"),
                nullable=False,
                index=True,
            ),
            sa.Column("case_code", sa.String(64), unique=True, nullable=False),
            sa.Column("subject_type", sa.String(32), nullable=True),
            sa.Column("subject_identifier", sa.String(255), nullable=True),
            sa.Column(
                "risk_level",
                sa.Enum(
                    "LOW", "MEDIUM", "HIGH", "CRITICAL",
                    name="risklevel",
                    create_type=False,
                ),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "status",
                sa.Enum(
                    "OPEN",
                    "UNDER_REVIEW",
                    "ESCALATED",
                    "CLOSED_NO_ACTION",
                    "REPORTED",
                    "REJECTED",
                    name="casestatus",
                    create_type=False,
                ),
                server_default="OPEN",
                index=True,
            ),
            sa.Column("ai_risk_score", sa.Integer, nullable=True),
            sa.Column("ai_analysis", postgresql.JSONB, server_default="{}"),
            sa.Column("red_flags", postgresql.JSONB, server_default="[]"),
            sa.Column("obligations_triggered", postgresql.JSONB, server_default="[]"),
            sa.Column("assigned_to_user_id", sa.String(64), nullable=True),
            sa.Column("requires_human_review", sa.Boolean, server_default="true"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
            ),
            sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing = {t for t in inspector.get_table_names()}

    if "compliance_cases" in existing:
        op.drop_table("compliance_cases")

    enums = {e["name"] for e in inspector.get_enums()}
    if "casestatus" in enums:
        sa.Enum(name="casestatus").drop(conn)
    if "risklevel" in enums:
        sa.Enum(name="risklevel").drop(conn)

    if "ai_model_registry" in existing:
        op.drop_table("ai_model_registry")
