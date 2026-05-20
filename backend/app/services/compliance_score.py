"""
Compliance score: what % of an entity's obligations have a SATISFIES edge (i.e. a linked control).
Score = satisfied_obligations / total_obligations * 100
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ObligationScore:
    obligation_id: str
    title: str
    obligation_type: str
    is_satisfied: bool
    control_label: str | None  # label of the SATISFIES control, if any


@dataclass
class ComplianceScore:
    entity_id: str
    entity_name: str
    total_obligations: int
    satisfied_obligations: int
    score_pct: float          # 0.0–100.0
    breakdown: list[ObligationScore]
    tenant_id: str


async def compute_score(entity_id: str, tenant_id: str) -> ComplianceScore | None:
    """
    Compute compliance score for a ComplianceEntity.

    Algorithm:
    1. Look up the ComplianceEntity by entity_id + tenant_id
    2. Find its GraphVertex (vertex_type="entity", entity_id=entity_id)
    3. Find all APPLIES_TO edges where to_vertex_id = entity's vertex id
       (these represent obligations that apply to this entity)
    4. For each obligation vertex, check if any SATISFIES edge exists
       where from_vertex_id = some control vertex pointing to this obligation
    5. Compute score
    """
    from app.db.base import AsyncSessionLocal
    from app.db.models import ComplianceEntity, GraphVertex, GraphEdge
    from sqlalchemy import select

    try:
        async with AsyncSessionLocal() as session:
            # Step 1: get entity
            entity = (await session.execute(
                select(ComplianceEntity).where(
                    ComplianceEntity.id == entity_id,
                    ComplianceEntity.tenant_id == tenant_id,
                )
            )).scalar_one_or_none()
            if not entity:
                return None

            # Step 2: get entity's graph vertex
            entity_vertex = (await session.execute(
                select(GraphVertex).where(
                    GraphVertex.vertex_type == "entity",
                    GraphVertex.entity_id == entity_id,
                )
            )).scalar_one_or_none()
            if not entity_vertex:
                return ComplianceScore(
                    entity_id=entity_id,
                    entity_name=entity.name,
                    total_obligations=0,
                    satisfied_obligations=0,
                    score_pct=100.0,
                    breakdown=[],
                    tenant_id=tenant_id,
                )

            # Step 3: find obligation vertices via APPLIES_TO edges
            applies_edges = (await session.execute(
                select(GraphEdge).where(
                    GraphEdge.edge_type == "APPLIES_TO",
                    GraphEdge.to_vertex_id == entity_vertex.id,
                )
            )).scalars().all()

            obligation_vertex_ids = [e.from_vertex_id for e in applies_edges]

            breakdown: list[ObligationScore] = []
            satisfied = 0

            for ob_vertex_id in obligation_vertex_ids:
                ob_vertex = (await session.execute(
                    select(GraphVertex).where(GraphVertex.id == ob_vertex_id)
                )).scalar_one_or_none()
                if not ob_vertex:
                    continue

                # Step 4: check for SATISFIES edge (control → obligation)
                satisfies_edge = (await session.execute(
                    select(GraphEdge).where(
                        GraphEdge.edge_type == "SATISFIES",
                        GraphEdge.to_vertex_id == ob_vertex_id,
                    )
                )).scalar_one_or_none()

                control_label: str | None = None
                if satisfies_edge:
                    ctrl_vertex = (await session.execute(
                        select(GraphVertex).where(GraphVertex.id == satisfies_edge.from_vertex_id)
                    )).scalar_one_or_none()
                    control_label = ctrl_vertex.label if ctrl_vertex else "unknown"
                    satisfied += 1

                breakdown.append(ObligationScore(
                    obligation_id=ob_vertex.entity_id or str(ob_vertex.id),
                    title=ob_vertex.label or "Unknown obligation",
                    obligation_type=(ob_vertex.properties or {}).get("obligation_type", "unknown"),
                    is_satisfied=satisfies_edge is not None,
                    control_label=control_label,
                ))

            total = len(breakdown)
            score_pct = round((satisfied / total * 100), 1) if total > 0 else 100.0

            return ComplianceScore(
                entity_id=entity_id,
                entity_name=entity.name,
                total_obligations=total,
                satisfied_obligations=satisfied,
                score_pct=score_pct,
                breakdown=breakdown,
                tenant_id=tenant_id,
            )
    except Exception as e:
        logger.error("compute_score failed: %s", e)
        return None


def get_score_service():
    return _score_service


_score_service = object()  # placeholder — compute_score is stateless
