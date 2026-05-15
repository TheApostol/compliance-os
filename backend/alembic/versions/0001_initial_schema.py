"""Initial schema — all tables from models.py and audit.py

Revision ID: 0001
Revises:
Create Date: 2026-05-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID  # noqa: F401

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The actual schema is managed by SQLAlchemy create_all in main.py lifespan.
    # This migration exists to establish the Alembic revision baseline so that
    # future `alembic revision --autogenerate` commands produce correct diffs.
    #
    # To stamp an existing database with this baseline without running DDL:
    #   alembic stamp 0001
    #
    # Future schema changes should use op.add_column(), op.create_table(), etc.
    pass


def downgrade() -> None:
    pass
