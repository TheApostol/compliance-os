"""
ComplianceOS — Compliance Graph Service
=========================================
Models Regulation → Obligation → Entity → Control as a queryable graph
using standard PostgreSQL with recursive CTEs. No external extension required.

Vertex types:  regulation | obligation | entity | control | regulator
Edge types:    REQUIRES | APPLIES_TO | SATISFIES | ISSUED_BY | CROSS_REFERENCES
"""

from __future__ import annotations

import uuid
import logging
from typing import Any

from sqlalchemy import select, text
from app.db.base import AsyncSessionLocal
from app.db.models import GraphVertex, GraphEdge, ComplianceEntity, EntityType, Obligation

logger = logging.getLogger(__name__)


class GraphService:

    async def upsert_vertex(
        self,
        vertex_type: str,
        entity_id: str,
        label: str,
        properties: dict | None = None,
    ) -> str:
        """Create or update a vertex. Returns vertex ID."""
        async with AsyncSessionLocal() as session:
            stmt = select(GraphVertex).where(
                GraphVertex.vertex_type == vertex_type,
                GraphVertex.entity_id == entity_id,
            )
            vertex = (await session.execute(stmt)).scalar_one_or_none()

            if vertex is None:
                vertex = GraphVertex(
                    id=uuid.uuid4(),
                    vertex_type=vertex_type,
                    entity_id=entity_id,
                    label=label,
                    properties=properties or {},
                )
                session.add(vertex)
            else:
                vertex.label = label
                if properties:
                    vertex.properties = {**(vertex.properties or {}), **properties}

            await session.commit()
            return str(vertex.id)

    async def upsert_edge(
        self,
        from_vertex_id: str,
        to_vertex_id: str,
        edge_type: str,
        properties: dict | None = None,
    ) -> str:
        """Create or return existing edge between two vertices."""
        async with AsyncSessionLocal() as session:
            stmt = select(GraphEdge).where(
                GraphEdge.from_vertex_id == from_vertex_id,
                GraphEdge.to_vertex_id == to_vertex_id,
                GraphEdge.edge_type == edge_type,
            )
            edge = (await session.execute(stmt)).scalar_one_or_none()

            if edge is None:
                edge = GraphEdge(
                    id=uuid.uuid4(),
                    from_vertex_id=from_vertex_id,
                    to_vertex_id=to_vertex_id,
                    edge_type=edge_type,
                    properties=properties or {},
                )
                session.add(edge)
                await session.commit()

            return str(edge.id)

    async def add_regulation(
        self,
        regulation_id: str,
        country: str,
        regulator: str,
        code: str,
        title: str,
        obligations: list[dict],
    ) -> dict[str, Any]:
        """
        Upsert a regulation vertex + all its obligation vertices + ISSUED_BY + REQUIRES edges.
        Returns counts.
        """
        # Regulation vertex
        reg_vid = await self.upsert_vertex(
            vertex_type="regulation",
            entity_id=regulation_id,
            label=f"{regulator} {code}",
            properties={"country": country, "regulator": regulator, "title": title},
        )

        # Regulator vertex + ISSUED_BY edge
        reg_authority_vid = await self.upsert_vertex(
            vertex_type="regulator",
            entity_id=f"{country}:{regulator}",
            label=regulator,
            properties={"country": country},
        )
        await self.upsert_edge(reg_vid, reg_authority_vid, "ISSUED_BY")

        # Obligation vertices + REQUIRES edges
        obl_count = 0
        for obl in obligations:
            obl_id = obl.get("obligation_code", str(uuid.uuid4()))
            obl_vid = await self.upsert_vertex(
                vertex_type="obligation",
                entity_id=obl_id,
                label=obl.get("description", obl_id)[:120],
                properties={
                    "obligation_type": obl.get("obligation_type", ""),
                    "severity": obl.get("severity", ""),
                    "frequency": obl.get("frequency", ""),
                    "deadline_rule": obl.get("deadline_rule", ""),
                },
            )
            await self.upsert_edge(reg_vid, obl_vid, "REQUIRES")
            obl_count += 1

        return {"regulation_vertex": reg_vid, "obligations_added": obl_count}

    async def link_control(
        self,
        obligation_entity_id: str,
        control_label: str,
        control_properties: dict | None = None,
    ) -> str:
        """Link a control to an obligation with a SATISFIES edge."""
        ctrl_id = f"ctrl:{uuid.uuid4().hex[:12]}"
        ctrl_vid = await self.upsert_vertex(
            vertex_type="control",
            entity_id=ctrl_id,
            label=control_label,
            properties=control_properties or {},
        )
        # Find obligation vertex
        async with AsyncSessionLocal() as session:
            stmt = select(GraphVertex).where(
                GraphVertex.vertex_type == "obligation",
                GraphVertex.entity_id == obligation_entity_id,
            )
            obl_vertex = (await session.execute(stmt)).scalar_one_or_none()

        if obl_vertex:
            await self.upsert_edge(ctrl_vid, str(obl_vertex.id), "SATISFIES")

        return ctrl_vid

    async def get_regulation_subgraph(
        self,
        regulation_id: str,
    ) -> dict[str, Any]:
        """
        Return all vertices and edges reachable from a regulation vertex
        using a recursive CTE (BFS up to depth 3).
        """
        async with AsyncSessionLocal() as session:
            # Find regulation vertex
            stmt = select(GraphVertex).where(
                GraphVertex.vertex_type == "regulation",
                GraphVertex.entity_id == regulation_id,
            )
            root = (await session.execute(stmt)).scalar_one_or_none()
            if not root:
                return {"error": "Regulation not found in graph"}

            root_id = str(root.id)

            # Recursive CTE: walk edges outward up to depth 3
            cte_sql = text("""
                WITH RECURSIVE subgraph AS (
                    SELECT id::text, vertex_type, entity_id, label, properties, 0 AS depth
                    FROM graph_vertices
                    WHERE id = :root_id::uuid

                    UNION ALL

                    SELECT v.id::text, v.vertex_type, v.entity_id, v.label, v.properties, sg.depth + 1
                    FROM graph_vertices v
                    JOIN graph_edges e ON e.to_vertex_id = v.id
                    JOIN subgraph sg ON sg.id = e.from_vertex_id::text
                    WHERE sg.depth < 3
                )
                SELECT DISTINCT id, vertex_type, entity_id, label, properties, depth
                FROM subgraph
            """)
            vertices_result = await session.execute(cte_sql, {"root_id": root_id})
            vertices = [
                {
                    "id": str(row.id),
                    "vertex_type": row.vertex_type,
                    "entity_id": row.entity_id,
                    "label": row.label,
                    "properties": row.properties,
                    "depth": row.depth,
                }
                for row in vertices_result
            ]

            vertex_ids = [v["id"] for v in vertices]
            edges_stmt = select(GraphEdge).where(
                GraphEdge.from_vertex_id.in_(vertex_ids),
                GraphEdge.to_vertex_id.in_(vertex_ids),
            )
            edges_result = await session.execute(edges_stmt)
            edges = [
                {
                    "id": str(e.id),
                    "from_vertex_id": str(e.from_vertex_id),
                    "to_vertex_id": str(e.to_vertex_id),
                    "edge_type": e.edge_type,
                    "properties": e.properties,
                }
                for e in edges_result.scalars().all()
            ]

        return {
            "regulation_id": regulation_id,
            "vertices": vertices,
            "edges": edges,
            "vertex_count": len(vertices),
            "edge_count": len(edges),
        }

    async def get_obligations_for_entity(
        self,
        entity_id: str,
        entity_type: str = "entity",
    ) -> dict[str, Any]:
        """Return all obligations that apply to a given entity."""
        async with AsyncSessionLocal() as session:
            stmt = select(GraphVertex).where(
                GraphVertex.vertex_type == entity_type,
                GraphVertex.entity_id == entity_id,
            )
            entity_vertex = (await session.execute(stmt)).scalar_one_or_none()
            if not entity_vertex:
                return {"error": "Entity not found in graph", "obligations": []}

            # Walk APPLIES_TO edges inbound to this entity
            edges_stmt = select(GraphEdge).where(
                GraphEdge.to_vertex_id == entity_vertex.id,
                GraphEdge.edge_type == "APPLIES_TO",
            )
            edges = (await session.execute(edges_stmt)).scalars().all()
            obligation_ids = [str(e.from_vertex_id) for e in edges]

            obligations = []
            if obligation_ids:
                obl_stmt = select(GraphVertex).where(
                    GraphVertex.id.in_(obligation_ids),
                    GraphVertex.vertex_type == "obligation",
                )
                obl_rows = (await session.execute(obl_stmt)).scalars().all()
                obligations = [
                    {
                        "obligation_id": str(o.id),
                        "entity_id": o.entity_id,
                        "label": o.label,
                        "properties": o.properties,
                    }
                    for o in obl_rows
                ]

        return {"entity_id": entity_id, "obligations": obligations}

    # ── Entity Registry ──────────────────────────────────────────────────────

    async def register_entity(
        self,
        tenant_id: str,
        name: str,
        entity_type: str,
        sectors: list[str],
        properties: dict | None = None,
    ) -> dict[str, Any]:
        """
        Upsert a ComplianceEntity row, create/update its graph vertex, then
        auto-wire APPLIES_TO edges to matching obligations.

        Returns {"entity_id": str, "vertex_id": str, "obligations_linked": int}.
        """
        props = properties or {}

        # Upsert ComplianceEntity row
        async with AsyncSessionLocal() as session:
            stmt = select(ComplianceEntity).where(
                ComplianceEntity.tenant_id == tenant_id,
                ComplianceEntity.name == name,
                ComplianceEntity.entity_type == EntityType(entity_type),
            )
            entity = (await session.execute(stmt)).scalar_one_or_none()

            if entity is None:
                entity = ComplianceEntity(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    name=name,
                    entity_type=EntityType(entity_type),
                    sectors=sectors,
                    properties=props,
                )
                session.add(entity)
            else:
                entity.sectors = sectors
                entity.properties = {**(entity.properties or {}), **props}

            await session.commit()
            entity_db_id = str(entity.id)

        # Upsert graph vertex for the entity
        vertex_id = await self.upsert_vertex(
            vertex_type="entity",
            entity_id=entity_db_id,
            label=name,
            properties={"entity_type": entity_type, "sectors": sectors, "tenant_id": tenant_id, **props},
        )

        # Auto-wire to matching obligations
        obligations_linked = await self._wire_entity_to_obligations(vertex_id, sectors, tenant_id)

        return {
            "entity_id": entity_db_id,
            "vertex_id": vertex_id,
            "obligations_linked": obligations_linked,
        }

    async def _wire_entity_to_obligations(
        self,
        entity_vertex_id: str,
        sectors: list[str],
        tenant_id: str | None = None,
    ) -> int:
        """
        Find all Obligation rows whose applies_to_sectors overlaps with sectors,
        then create APPLIES_TO edges from each obligation vertex → entity vertex.

        Falls back to Python-side filtering (acceptable for small obligation sets).
        Returns count of edges created.
        """
        if not sectors:
            return 0

        async with AsyncSessionLocal() as session:
            all_obs = (await session.execute(select(Obligation))).scalars().all()
            matching = [
                o for o in all_obs
                if any(s in (o.applies_to_sectors or []) for s in sectors)
            ]

        count = 0
        for ob in matching:
            # Find (or create) the obligation's graph vertex
            async with AsyncSessionLocal() as session:
                stmt = select(GraphVertex).where(
                    GraphVertex.vertex_type == "obligation",
                    GraphVertex.entity_id == ob.obligation_code,
                )
                obl_vertex = (await session.execute(stmt)).scalar_one_or_none()

            if obl_vertex is None:
                continue

            await self.upsert_edge(str(obl_vertex.id), entity_vertex_id, "APPLIES_TO")
            count += 1

        return count

    async def link_obligation_to_sectors(
        self,
        regulation_id: str,
        obligations_data: list[dict],
    ) -> dict[str, Any]:
        """
        For each obligation parsed by M1, create virtual 'sector' entity vertices
        and wire APPLIES_TO edges: obligation_vertex → sector_vertex.

        Called after add_regulation() in the M1 post-parse hook.
        Returns {"sector_vertices": int, "edges_created": int}.
        """
        sector_vertex_count = 0
        edge_count = 0

        for obl in obligations_data:
            obl_code = obl.get("obligation_code", "")
            sectors = obl.get("applies_to_sectors", [])
            if not obl_code or not sectors:
                continue

            # Find obligation vertex
            async with AsyncSessionLocal() as session:
                stmt = select(GraphVertex).where(
                    GraphVertex.vertex_type == "obligation",
                    GraphVertex.entity_id == obl_code,
                )
                obl_vertex = (await session.execute(stmt)).scalar_one_or_none()

            if obl_vertex is None:
                logger.debug("link_obligation_to_sectors: obligation vertex not found for %s", obl_code)
                continue

            for sector in sectors:
                sector_entity_id = f"sector:{sector}"

                # Upsert sector vertex
                sector_vid = await self.upsert_vertex(
                    vertex_type="entity",
                    entity_id=sector_entity_id,
                    label=sector,
                    properties={"entity_type": "sector", "sector": sector},
                )
                sector_vertex_count += 1

                # APPLIES_TO: obligation → sector
                await self.upsert_edge(str(obl_vertex.id), sector_vid, "APPLIES_TO")
                edge_count += 1

        return {"sector_vertices": sector_vertex_count, "edges_created": edge_count}

    async def graph_stats(self) -> dict[str, Any]:
        """Return high-level graph statistics."""
        async with AsyncSessionLocal() as session:
            v_stmt = text("SELECT vertex_type, COUNT(*) as cnt FROM graph_vertices GROUP BY vertex_type")
            e_stmt = text("SELECT edge_type, COUNT(*) as cnt FROM graph_edges GROUP BY edge_type")
            vertices = {row.vertex_type: row.cnt for row in await session.execute(v_stmt)}
            edges = {row.edge_type: row.cnt for row in await session.execute(e_stmt)}

        return {
            "vertices": vertices,
            "edges": edges,
            "total_vertices": sum(vertices.values()),
            "total_edges": sum(edges.values()),
        }


_graph: GraphService | None = None


def get_graph() -> GraphService:
    global _graph
    if _graph is None:
        _graph = GraphService()
    return _graph
