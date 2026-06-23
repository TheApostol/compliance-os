"""Add transactions + transaction_rules tables (M10 — Transaction Monitoring)

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    return bind.dialect.has_table(bind, name)


def _enum_exists(name: str) -> bool:
    bind = op.get_bind()
    return bind.execute(
        sa.text("SELECT 1 FROM pg_type WHERE typname = :name"), {"name": name}
    ).first() is not None


def upgrade() -> None:
    if not _table_exists("transactions"):
        op.create_table(
            "transactions",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("tenant_id", sa.String(64), nullable=False),
            sa.Column("external_ref", sa.String(255), nullable=True),
            sa.Column("subject_identifier", sa.String(255), nullable=False),
            sa.Column("counterparty_identifier", sa.String(255), nullable=True),
            sa.Column("counterparty_country", sa.String(2), nullable=True),
            sa.Column("amount", sa.Numeric(18, 2), nullable=False),
            sa.Column("currency", sa.String(8), nullable=False),
            sa.Column("channel", sa.String(32), nullable=False),
            sa.Column("country", sa.String(2), nullable=False),
            sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column(
                "status",
                sa.Enum("pending", "cleared", "flagged", "blocked", "reported", name="transactionstatus"),
                nullable=True,
            ),
            sa.Column("risk_score", sa.Integer(), nullable=True),
            sa.Column(
                "risk_level",
                sa.Enum(
                    "LOW", "MEDIUM", "HIGH", "CRITICAL", name="risklevel",
                    create_type=not _enum_exists("risklevel"),
                ),
                nullable=True,
            ),
            sa.Column("rule_flags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("ai_analysis", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("case_id", sa.String(64), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("scored_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_transactions_tenant_id", "transactions", ["tenant_id"])
        op.create_index("ix_transactions_status", "transactions", ["status"])
        op.create_index("ix_transactions_risk_level", "transactions", ["risk_level"])
        op.create_index("ix_txn_tenant_subject", "transactions", ["tenant_id", "subject_identifier"])
        op.create_index("ix_txn_tenant_status", "transactions", ["tenant_id", "status"])
        op.create_index("ix_txn_tenant_occurred", "transactions", ["tenant_id", "occurred_at"])

    if not _table_exists("transaction_rules"):
        op.create_table(
            "transaction_rules",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("tenant_id", sa.String(64), nullable=False),
            sa.Column("rule_code", sa.String(64), nullable=False),
            sa.Column("rule_type", sa.String(32), nullable=False),
            sa.Column("description", sa.String(500), nullable=False),
            sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("tenant_id", "rule_code", name="uq_rule_tenant_code"),
        )
        op.create_index("ix_transaction_rules_tenant_id", "transaction_rules", ["tenant_id"])


def downgrade() -> None:
    if _table_exists("transaction_rules"):
        op.drop_index("ix_transaction_rules_tenant_id", table_name="transaction_rules")
        op.drop_table("transaction_rules")

    if _table_exists("transactions"):
        op.drop_index("ix_txn_tenant_occurred", table_name="transactions")
        op.drop_index("ix_txn_tenant_status", table_name="transactions")
        op.drop_index("ix_txn_tenant_subject", table_name="transactions")
        op.drop_index("ix_transactions_risk_level", table_name="transactions")
        op.drop_index("ix_transactions_status", table_name="transactions")
        op.drop_index("ix_transactions_tenant_id", table_name="transactions")
        op.drop_table("transactions")
        sa.Enum(name="transactionstatus").drop(op.get_bind(), checkfirst=True)
