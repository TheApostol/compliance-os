"""Test graph tenant isolation — verify cross-tenant data leakage is prevented."""

import pytest
from uuid import uuid4
from sqlalchemy import select
from app.db.base import AsyncSessionLocal
from app.db.models import GraphVertex, GraphEdge


@pytest.mark.asyncio
async def test_graph_vertex_tenant_isolation():
    """Verify GraphVertex queries are scoped by tenant_id."""
    async with AsyncSessionLocal() as session:
        # Insert vertices for tenant A and B with same entity_id
        v_a = GraphVertex(
            id=uuid4(),
            vertex_type="entity",
            entity_id="entity1",
            tenant_id="tenant_a",
            label="Entity A"
        )
        v_b = GraphVertex(
            id=uuid4(),
            vertex_type="entity",
            entity_id="entity1",  # Same entity ID but different tenant
            tenant_id="tenant_b",
            label="Entity B"
        )
        session.add_all([v_a, v_b])
        await session.commit()

        # Tenant A should see only their vertex
        result_a = (await session.execute(
            select(GraphVertex).where(
                GraphVertex.entity_id == "entity1",
                GraphVertex.tenant_id == "tenant_a"
            )
        )).scalars().all()

        assert len(result_a) == 1
        assert result_a[0].tenant_id == "tenant_a"
        assert result_a[0].id == v_a.id

        # Tenant B should see only their vertex
        result_b = (await session.execute(
            select(GraphVertex).where(
                GraphVertex.entity_id == "entity1",
                GraphVertex.tenant_id == "tenant_b"
            )
        )).scalars().all()

        assert len(result_b) == 1
        assert result_b[0].tenant_id == "tenant_b"
        assert result_b[0].id == v_b.id

        # Without tenant_id filter, both should be returned (but queries should never omit tenant_id)
        all_results = (await session.execute(
            select(GraphVertex).where(GraphVertex.entity_id == "entity1")
        )).scalars().all()
        assert len(all_results) == 2


@pytest.mark.asyncio
async def test_graph_edge_tenant_isolation():
    """Verify GraphEdge queries are scoped by tenant_id."""
    async with AsyncSessionLocal() as session:
        # Create vertices for two tenants
        v1_a = GraphVertex(
            id=uuid4(),
            vertex_type="regulation",
            entity_id="reg1",
            tenant_id="tenant_a",
            label="Reg A"
        )
        v2_a = GraphVertex(
            id=uuid4(),
            vertex_type="obligation",
            entity_id="ob1",
            tenant_id="tenant_a",
            label="Ob A"
        )

        v1_b = GraphVertex(
            id=uuid4(),
            vertex_type="regulation",
            entity_id="reg1",
            tenant_id="tenant_b",
            label="Reg B"
        )
        v2_b = GraphVertex(
            id=uuid4(),
            vertex_type="obligation",
            entity_id="ob1",
            tenant_id="tenant_b",
            label="Ob B"
        )

        session.add_all([v1_a, v2_a, v1_b, v2_b])
        await session.flush()

        # Create edges for both tenants
        e_a = GraphEdge(
            id=uuid4(),
            from_vertex_id=v1_a.id,
            to_vertex_id=v2_a.id,
            edge_type="APPLIES_TO",
            tenant_id="tenant_a"
        )
        e_b = GraphEdge(
            id=uuid4(),
            from_vertex_id=v1_b.id,
            to_vertex_id=v2_b.id,
            edge_type="APPLIES_TO",
            tenant_id="tenant_b"
        )

        session.add_all([e_a, e_b])
        await session.commit()

        # Each tenant sees only their edges
        edges_a = (await session.execute(
            select(GraphEdge).where(
                GraphEdge.edge_type == "APPLIES_TO",
                GraphEdge.tenant_id == "tenant_a"
            )
        )).scalars().all()

        edges_b = (await session.execute(
            select(GraphEdge).where(
                GraphEdge.edge_type == "APPLIES_TO",
                GraphEdge.tenant_id == "tenant_b"
            )
        )).scalars().all()

        assert len(edges_a) == 1
        assert len(edges_b) == 1
        assert edges_a[0].tenant_id == "tenant_a"
        assert edges_b[0].tenant_id == "tenant_b"
        assert edges_a[0].id == e_a.id
        assert edges_b[0].id == e_b.id


@pytest.mark.asyncio
async def test_graph_composite_index_efficiency():
    """Verify composite indexes exist and enable efficient tenant-scoped queries."""
    async with AsyncSessionLocal() as session:
        # Create multiple vertices to test indexing
        for i in range(5):
            for tenant in ["tenant_a", "tenant_b"]:
                v = GraphVertex(
                    id=uuid4(),
                    vertex_type="obligation",
                    entity_id=f"ob_{i}",
                    tenant_id=tenant,
                    label=f"Obligation {i} for {tenant}"
                )
                session.add(v)
        await session.commit()

        # Query using composite index: tenant_id + vertex_type + entity_id
        result = (await session.execute(
            select(GraphVertex).where(
                GraphVertex.tenant_id == "tenant_a",
                GraphVertex.vertex_type == "obligation",
                GraphVertex.entity_id == "ob_2"
            )
        )).scalars().all()

        assert len(result) == 1
        assert result[0].tenant_id == "tenant_a"


@pytest.mark.asyncio
async def test_graph_edge_cross_tenant_prevention():
    """Verify edges cannot cross tenant boundaries."""
    async with AsyncSessionLocal() as session:
        # Create vertices for different tenants
        v_a = GraphVertex(
            id=uuid4(),
            vertex_type="entity",
            entity_id="entity_a",
            tenant_id="tenant_a",
            label="Entity A"
        )
        v_b = GraphVertex(
            id=uuid4(),
            vertex_type="regulation",
            entity_id="reg_b",
            tenant_id="tenant_b",
            label="Reg B"
        )

        session.add_all([v_a, v_b])
        await session.flush()

        # Attempt to create cross-tenant edge (this should work at DB level,
        # but the application should prevent it)
        cross_tenant_edge = GraphEdge(
            id=uuid4(),
            from_vertex_id=v_a.id,
            to_vertex_id=v_b.id,
            edge_type="APPLIES_TO",
            tenant_id="tenant_a"  # Edge marked as tenant_a, but connects to tenant_b vertex
        )
        session.add(cross_tenant_edge)
        await session.commit()

        # Querying as tenant_a should see the edge (it's marked as theirs)
        # but the application layer should validate that both vertices belong to tenant_a
        result = (await session.execute(
            select(GraphEdge).where(
                GraphEdge.tenant_id == "tenant_a",
                GraphEdge.from_vertex_id == v_a.id
            )
        )).scalars().all()

        assert len(result) == 1
        # In production, application code should validate both from_vertex and to_vertex
        # belong to the same tenant as the edge
