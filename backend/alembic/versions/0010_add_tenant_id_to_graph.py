"""Add tenant_id to graph_vertices and graph_edges (Tier 1.1 — Graph Tenant Isolation)

Revision ID: 0010
Revises: 0009
Create Date: 2026-06-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    """Check if a column already exists in a table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = inspector.get_columns(table)
    return any(c['name'] == column for c in columns)


def upgrade() -> None:
    """Add tenant_id columns to graph tables and create indexes."""

    # Add tenant_id to graph_vertices if not exists
    if not _column_exists("graph_vertices", "tenant_id"):
        op.add_column(
            "graph_vertices",
            sa.Column("tenant_id", sa.String(64), nullable=False, server_default="system"),
        )

    # Add tenant_id to graph_edges if not exists
    if not _column_exists("graph_edges", "tenant_id"):
        op.add_column(
            "graph_edges",
            sa.Column("tenant_id", sa.String(64), nullable=False, server_default="system"),
        )

    # Create indexes for tenant_id queries
    try:
        op.create_index(
            "ix_graph_vertex_tenant",
            "graph_vertices",
            ["tenant_id"],
            if_not_exists=True,
        )
    except Exception:
        # Index may already exist
        pass

    try:
        op.create_index(
            "ix_graph_edge_tenant",
            "graph_edges",
            ["tenant_id"],
            if_not_exists=True,
        )
    except Exception:
        # Index may already exist
        pass

    # Composite indexes for common query patterns
    try:
        op.create_index(
            "ix_graph_vertex_tenant_type_entity",
            "graph_vertices",
            ["tenant_id", "vertex_type", "entity_id"],
            if_not_exists=True,
        )
    except Exception:
        pass

    try:
        op.create_index(
            "ix_graph_edge_tenant_type",
            "graph_edges",
            ["tenant_id", "edge_type"],
            if_not_exists=True,
        )
    except Exception:
        pass


def downgrade() -> None:
    """Remove tenant_id columns and indexes."""

    # Drop indexes
    try:
        op.drop_index("ix_graph_vertex_tenant_type_entity", table_name="graph_vertices")
    except Exception:
        pass

    try:
        op.drop_index("ix_graph_edge_tenant_type", table_name="graph_edges")
    except Exception:
        pass

    try:
        op.drop_index("ix_graph_vertex_tenant", table_name="graph_vertices")
    except Exception:
        pass

    try:
        op.drop_index("ix_graph_edge_tenant", table_name="graph_edges")
    except Exception:
        pass

    # Drop columns
    if _column_exists("graph_vertices", "tenant_id"):
        op.drop_column("graph_vertices", "tenant_id")

    if _column_exists("graph_edges", "tenant_id"):
        op.drop_column("graph_edges", "tenant_id")
