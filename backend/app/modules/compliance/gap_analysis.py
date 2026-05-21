"""
M7 — Compliance Gap Analysis
==============================
AI-powered obligation gap identification for registered entities.

For a given ComplianceEntity, this module:
1. Loads all applicable obligations via the graph (APPLIES_TO edges → entity vertex).
2. Identifies gaps: obligations that have no SATISFIES edge pointing to them.
3. Calls the AI orchestrator to produce a structured risk summary + recommendations.
4. Returns a GapAnalysisResult with score, gaps, and actionable AI guidance.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.db.base import AsyncSessionLocal
from app.db.models import ComplianceEntity, GraphVertex, GraphEdge, Regulation
from app.services.ai_orchestrator import (
    AIOrchestrator, InferenceRequest, TaskType, get_orchestrator
)
from app.services.compliance_score import compute_score
from sqlalchemy import select

logger = logging.getLogger(__name__)


GAP_ANALYSIS_SYSTEM = """You are ComplianceOS Gap Analyst, an expert in regulatory compliance for LATAM regulated industries.

Given an entity profile, its applicable regulations, and a list of unsatisfied obligations (gaps), produce a structured risk assessment.

Rules:
1. Be specific about which regulations are missing controls.
2. Prioritize actions by regulatory risk (CRITICAL > HIGH > MEDIUM > LOW).
3. Output ONLY valid JSON — no markdown, no explanations outside the JSON.
4. Keep the summary concise (2-3 sentences max).
5. Priority actions must be concrete and actionable.
"""


@dataclass
class GapAnalysisResult:
    entity_id: str
    entity_name: str
    entity_type: str
    sectors: list[str]
    score_pct: float
    applicable_regulations: list[dict]
    gaps: list[dict]                  # obligations without controls
    recommendations: list[str]
    ai_summary: str
    risk_level: str                   # low | medium | high | critical
    model_used: str
    tenant_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_name": self.entity_name,
            "entity_type": self.entity_type,
            "sectors": self.sectors,
            "score_pct": self.score_pct,
            "applicable_regulations": self.applicable_regulations,
            "gaps": self.gaps,
            "gap_count": len(self.gaps),
            "recommendations": self.recommendations,
            "ai_summary": self.ai_summary,
            "risk_level": self.risk_level,
            "model_used": self.model_used,
            "tenant_id": self.tenant_id,
        }


async def run_gap_analysis(
    entity_id: str,
    tenant_id: str,
    orchestrator: AIOrchestrator | None = None,
) -> GapAnalysisResult | None:
    """
    Run a full compliance gap analysis for a registered entity.

    Returns None if the entity is not found for the given tenant.
    Never raises — AI failures are handled gracefully with a fallback summary.
    """
    orch = orchestrator or get_orchestrator()

    # ── Step 1: Load the entity ────────────────────────────────────────────
    try:
        async with AsyncSessionLocal() as session:
            entity = (await session.execute(
                select(ComplianceEntity).where(
                    ComplianceEntity.id == entity_id,
                    ComplianceEntity.tenant_id == tenant_id,
                )
            )).scalar_one_or_none()

            if not entity:
                return None

            entity_name = entity.name
            entity_type = entity.entity_type.value if hasattr(entity.entity_type, "value") else str(entity.entity_type)
            sectors = list(entity.sectors or [])

            # ── Step 2: Load all regulations for the tenant ────────────────
            all_regs = (await session.execute(
                select(Regulation).where(
                    (Regulation.tenant_id == tenant_id) | (Regulation.tenant_id.is_(None))
                )
            )).scalars().all()

            applicable_regulations = [
                {
                    "regulation_id": str(r.id),
                    "code": r.code,
                    "title": r.title,
                    "country": r.country,
                    "regulator": r.regulator,
                    "sector": r.sector,
                }
                for r in all_regs
            ]

            # ── Step 3: Find gaps via graph ────────────────────────────────
            # Get entity's graph vertex
            entity_vertex = (await session.execute(
                select(GraphVertex).where(
                    GraphVertex.vertex_type == "entity",
                    GraphVertex.entity_id == entity_id,
                )
            )).scalar_one_or_none()

            gaps: list[dict] = []

            if entity_vertex:
                # Find all APPLIES_TO edges pointing to this entity vertex
                applies_edges = (await session.execute(
                    select(GraphEdge).where(
                        GraphEdge.edge_type == "APPLIES_TO",
                        GraphEdge.to_vertex_id == entity_vertex.id,
                    )
                )).scalars().all()

                for edge in applies_edges:
                    ob_vertex = (await session.execute(
                        select(GraphVertex).where(GraphVertex.id == edge.from_vertex_id)
                    )).scalar_one_or_none()

                    if not ob_vertex:
                        continue

                    # Check for a SATISFIES edge pointing TO this obligation vertex
                    satisfies_edge = (await session.execute(
                        select(GraphEdge).where(
                            GraphEdge.edge_type == "SATISFIES",
                            GraphEdge.to_vertex_id == ob_vertex.id,
                        )
                    )).scalar_one_or_none()

                    if satisfies_edge is None:
                        # This obligation has no control — it's a gap
                        props = ob_vertex.properties or {}
                        gaps.append({
                            "obligation_id": ob_vertex.entity_id or str(ob_vertex.id),
                            "title": ob_vertex.label or "Unknown obligation",
                            "obligation_type": props.get("obligation_type", "unknown"),
                            "severity": props.get("severity", "unknown"),
                            "frequency": props.get("frequency", "unknown"),
                        })

    except Exception as e:
        logger.error("Gap analysis DB phase failed for entity %s: %s", entity_id, e)
        return None

    # ── Step 4: Compute compliance score ──────────────────────────────────
    score_obj = await compute_score(entity_id=entity_id, tenant_id=tenant_id)
    score_pct = score_obj.score_pct if score_obj else 0.0

    # ── Step 5: Build prompt and call AI ──────────────────────────────────
    reg_summary = "\n".join(
        f"- {r['code']} ({r['country']} / {r['regulator']}): {r['title']}"
        for r in applicable_regulations[:10]  # cap to avoid token bloat
    ) or "No regulations loaded."

    gaps_summary = "\n".join(
        f"- [{g['severity']}] {g['title']} (type: {g['obligation_type']}, freq: {g['frequency']})"
        for g in gaps
    ) or "No gaps identified."

    prompt = f"""Entity profile:
- Name: {entity_name}
- Type: {entity_type}
- Sectors: {', '.join(sectors) or 'not specified'}
- Compliance score: {score_pct}%

Applicable regulations:
{reg_summary}

Identified gaps (obligations without controls):
{gaps_summary}

Return ONLY this JSON (no markdown):
{{
  "summary": "<2-3 sentence executive summary of the compliance posture>",
  "priority_actions": ["<action 1>", "<action 2>", ...],
  "missing_regulations": ["<regulation code or topic>", ...],
  "risk_level": "low|medium|high|critical"
}}"""

    ai_summary = "Gap analysis complete. Review identified obligations without controls."
    recommendations: list[str] = []
    risk_level = _derive_risk_level(score_pct, gaps)
    model_used = ""

    try:
        result = await orch.infer(InferenceRequest(
            task=TaskType.COPILOT_QA,
            system=GAP_ANALYSIS_SYSTEM,
            user_prompt=prompt,
            tenant_id=tenant_id,
            temperature=0.3,
            max_tokens=1500,
            json_mode=True,
        ))

        model_used = result.model_used or ""

        # ── Step 7: Parse AI response ──────────────────────────────────────
        if result.success and result.parsed_json:
            parsed = result.parsed_json
            ai_summary = parsed.get("summary", ai_summary)
            recommendations = parsed.get("priority_actions", [])
            risk_level = parsed.get("risk_level", risk_level)
        elif result.success and result.response_text:
            # Try manual parse as fallback
            parsed = AIOrchestrator._try_parse_json(result.response_text)
            if parsed:
                ai_summary = parsed.get("summary", ai_summary)
                recommendations = parsed.get("priority_actions", [])
                risk_level = parsed.get("risk_level", risk_level)

    except Exception as e:
        logger.warning("Gap analysis AI call failed for entity %s: %s", entity_id, e)
        # Graceful fallback — continue with derived values

    # ── Step 8: Return result ──────────────────────────────────────────────
    return GapAnalysisResult(
        entity_id=entity_id,
        entity_name=entity_name,
        entity_type=entity_type,
        sectors=sectors,
        score_pct=score_pct,
        applicable_regulations=applicable_regulations,
        gaps=gaps,
        recommendations=recommendations,
        ai_summary=ai_summary,
        risk_level=risk_level,
        model_used=model_used,
        tenant_id=tenant_id,
    )


def _derive_risk_level(score_pct: float, gaps: list[dict]) -> str:
    """Derive a risk level from score and gap severities when AI is unavailable."""
    critical_gaps = sum(1 for g in gaps if g.get("severity", "").upper() == "CRITICAL")
    high_gaps = sum(1 for g in gaps if g.get("severity", "").upper() == "HIGH")

    if score_pct < 25 or critical_gaps >= 2:
        return "critical"
    if score_pct < 50 or critical_gaps >= 1 or high_gaps >= 3:
        return "high"
    if score_pct < 75 or high_gaps >= 1:
        return "medium"
    return "low"
