"""Add compliance_entities, graph_vertices, graph_edges, users tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    return bind.dialect.has_table(bind, name)


def upgrade() -> None:
    # ── compliance_entities ─────────────────────────────────────────
    if not _table_exists("compliance_entities"):
        op.create_table(
            "compliance_entities",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                nullable=False,
            ),
            sa.Column("tenant_id", sa.String(64), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column(
                "entity_type",
                sa.Enum("company", "individual", "sector", name="entitytype"),
                nullable=False,
            ),
            sa.Column("sectors", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("properties", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
        )
        op.create_index(
            "ix_compliance_entities_tenant_id",
            "compliance_entities",
            ["tenant_id"],
        )
        op.create_index(
            "ix_entity_tenant_type",
            "compliance_entities",
            ["tenant_id", "entity_type"],
        )

    # ── graph_vertices ──────────────────────────────────────────────
    if not _table_exists("graph_vertices"):
        op.create_table(
            "graph_vertices",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                nullable=False,
            ),
            sa.Column("vertex_type", sa.String(32), nullable=False),
            sa.Column("entity_id", sa.String(64), nullable=False),
            sa.Column("label", sa.String(255), nullable=False),
            sa.Column("properties", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
        )
        op.create_index(
            "ix_graph_vertices_vertex_type",
            "graph_vertices",
            ["vertex_type"],
        )
        op.create_index(
            "ix_graph_vertices_entity_id",
            "graph_vertices",
            ["entity_id"],
        )
        op.create_index(
            "ix_vertex_type_entity",
            "graph_vertices",
            ["vertex_type", "entity_id"],
        )

    # ── graph_edges ─────────────────────────────────────────────────
    if not _table_exists("graph_edges"):
        op.create_table(
            "graph_edges",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                nullable=False,
            ),
            sa.Column(
                "from_vertex_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("graph_vertices.id"),
                nullable=False,
            ),
            sa.Column(
                "to_vertex_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("graph_vertices.id"),
                nullable=False,
            ),
            sa.Column("edge_type", sa.String(64), nullable=False),
            sa.Column("properties", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
        )
        op.create_index(
            "ix_graph_edges_edge_type",
            "graph_edges",
            ["edge_type"],
        )
        op.create_index(
            "ix_edge_from",
            "graph_edges",
            ["from_vertex_id"],
        )
        op.create_index(
            "ix_edge_to",
            "graph_edges",
            ["to_vertex_id"],
        )
        op.create_index(
            "ix_edge_type_from",
            "graph_edges",
            ["edge_type", "from_vertex_id"],
        )

    # ── users ───────────────────────────────────────────────────────
    if not _table_exists("users"):
        op.create_table(
            "users",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                nullable=False,
            ),
            sa.Column("tenant_id", sa.String(64), nullable=False),
            sa.Column("email", sa.String(255), nullable=False, unique=True),
            sa.Column("hashed_password", sa.String(255), nullable=False),
            sa.Column(
                "role",
                sa.Enum("admin", "analyst", "viewer", name="userrole"),
                nullable=False,
            ),
            sa.Column("is_active", sa.Boolean(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
        )
        op.create_index(
            "ix_users_tenant_id",
            "users",
            ["tenant_id"],
        )
        op.create_index(
            "ix_users_email",
            "users",
            ["email"],
            unique=True,
        )


def downgrade() -> None:
    # Drop in reverse order to respect foreign-key dependencies
    if _table_exists("graph_edges"):
        op.drop_index("ix_edge_type_from", table_name="graph_edges")
        op.drop_index("ix_edge_to", table_name="graph_edges")
        op.drop_index("ix_edge_from", table_name="graph_edges")
        op.drop_index("ix_graph_edges_edge_type", table_name="graph_edges")
        op.drop_table("graph_edges")

    if _table_exists("graph_vertices"):
        op.drop_index("ix_vertex_type_entity", table_name="graph_vertices")
        op.drop_index("ix_graph_vertices_entity_id", table_name="graph_vertices")
        op.drop_index("ix_graph_vertices_vertex_type", table_name="graph_vertices")
        op.drop_table("graph_vertices")

    if _table_exists("compliance_entities"):
        op.drop_index("ix_entity_tenant_type", table_name="compliance_entities")
        op.drop_index("ix_compliance_entities_tenant_id", table_name="compliance_entities")
        op.drop_table("compliance_entities")

    if _table_exists("users"):
        op.drop_index("ix_users_email", table_name="users")
        op.drop_index("ix_users_tenant_id", table_name="users")
        op.drop_table("users")

    # Drop enums
    sa.Enum(name="entitytype").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="userrole").drop(op.get_bind(), checkfirst=True)
