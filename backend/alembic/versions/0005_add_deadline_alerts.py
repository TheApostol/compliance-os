"""Add deadline_alerts table

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    return bind.dialect.has_table(bind, name)


def _enum_exists(name: str) -> bool:
    bind = op.get_bind()
    return bind.dialect.has_type(bind, name)


def upgrade() -> None:
    # Create the alertseverity enum type if it doesn't exist
    if not _enum_exists("alertseverity"):
        alertseverity = sa.Enum("low", "medium", "high", "critical", name="alertseverity")
        alertseverity.create(op.get_bind(), checkfirst=True)

    if not _table_exists("deadline_alerts"):
        op.create_table(
            "deadline_alerts",
            sa.Column("id", sa.String(), primary_key=True, nullable=False),
            sa.Column("tenant_id", sa.String(), nullable=False),
            sa.Column("obligation_id", sa.String(), nullable=False),
            sa.Column("regulation_code", sa.String(), nullable=False),
            sa.Column("regulator", sa.String(), nullable=False),
            sa.Column("country", sa.String(), nullable=False),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("deadline", sa.DateTime(timezone=True), nullable=False),
            sa.Column("days_remaining", sa.Integer(), nullable=False),
            sa.Column(
                "severity",
                sa.Enum("low", "medium", "high", "critical", name="alertseverity"),
                nullable=True,
                server_default="medium",
            ),
            sa.Column("is_acknowledged", sa.Boolean(), nullable=True, server_default="false"),
            sa.Column("acknowledged_by", sa.String(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=True,
                server_default=sa.func.now(),
            ),
            sa.UniqueConstraint("tenant_id", "obligation_id", name="uq_alert_tenant_obligation"),
        )
        op.create_index("ix_alerts_tenant_ack", "deadline_alerts", ["tenant_id", "is_acknowledged"])
        op.create_index("ix_deadline_alerts_tenant_id", "deadline_alerts", ["tenant_id"])


def downgrade() -> None:
    if _table_exists("deadline_alerts"):
        op.drop_index("ix_deadline_alerts_tenant_id", table_name="deadline_alerts")
        op.drop_index("ix_alerts_tenant_ack", table_name="deadline_alerts")
        op.drop_constraint("uq_alert_tenant_obligation", "deadline_alerts", type_="unique")
        op.drop_table("deadline_alerts")

    if _enum_exists("alertseverity"):
        sa.Enum(name="alertseverity").drop(op.get_bind(), checkfirst=True)
