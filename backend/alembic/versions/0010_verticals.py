"""Add multi-vertical support: vertical column on tenants, vertical_regulators, vertical_obligation_types

Revision ID: 0010
Revises: 0009
Create Date: 2026-05-21

Idempotent: uses inspector checks before each DDL operation.
"""
from __future__ import annotations

import uuid
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = {t for t in inspector.get_table_names()}

    # ── Add vertical column to tenants ────────────────────────────────
    existing_cols = {c["name"] for c in inspector.get_columns("tenants")}
    if "vertical" not in existing_cols:
        op.add_column("tenants", sa.Column("vertical", sa.String(50), server_default="FINTECH"))

    # ── vertical_regulators ───────────────────────────────────────────
    if "vertical_regulators" not in existing_tables:
        op.create_table(
            "vertical_regulators",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            sa.Column("vertical", sa.String(50), nullable=False),
            sa.Column("country", sa.String(10), nullable=False),
            sa.Column("regulator_code", sa.String(20), nullable=False),
            sa.Column("regulator_name", sa.Text, nullable=False),
            sa.Column("regulator_url", sa.Text, nullable=True),
            sa.Column("schedule_hours", sa.Integer, server_default="24"),
            sa.Column("is_active", sa.Boolean, server_default="true"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_vr_vertical", "vertical_regulators", ["vertical"])
        op.create_unique_constraint(
            "uq_vr_vertical_country_code", "vertical_regulators",
            ["vertical", "country", "regulator_code"]
        )

    # ── vertical_obligation_types ──────────────────────────────────────
    if "vertical_obligation_types" not in existing_tables:
        op.create_table(
            "vertical_obligation_types",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            sa.Column("vertical", sa.String(50), nullable=False),
            sa.Column("obligation_type", sa.String(100), nullable=False),
            sa.Column("description", sa.Text, nullable=True),
            sa.Column("default_deadline_days", sa.Integer, nullable=True),
            sa.Column("severity", sa.String(20), server_default="medium"),
        )
        op.create_index("ix_vot_vertical", "vertical_obligation_types", ["vertical"])
        op.create_unique_constraint(
            "uq_vot_vertical_type", "vertical_obligation_types",
            ["vertical", "obligation_type"]
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = {t for t in inspector.get_table_names()}

    if "vertical_obligation_types" in existing_tables:
        op.drop_table("vertical_obligation_types")
    if "vertical_regulators" in existing_tables:
        op.drop_table("vertical_regulators")

    existing_cols = {c["name"] for c in inspector.get_columns("tenants")}
    if "vertical" in existing_cols:
        op.drop_column("tenants", "vertical")
