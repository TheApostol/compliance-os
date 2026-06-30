"""
ComplianceDirector — Chief Compliance Officer Agent

Main orchestrator that:
1. Receives high-level compliance requests
2. Delegates to domain/skill agents
3. Aggregates results into cohesive recommendations
4. Escalates risks to governance
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.agents.base import Agent, AgentResult, AgentType
from app.db.models import Tenant, ComplianceEntity
from app.services.compliance_score import compute_score

logger = logging.getLogger(__name__)


class ComplianceDirector(Agent):
    """
    Supervisor agent. Routes requests to domain and skill agents.
    Single instance per system (though could be per-tenant if needed).
    """

    def __init__(self):
        super().__init__(
            agent_id="supervisor:director",
            agent_type=AgentType.SUPERVISOR,
            tenant_id="system",  # Operates cross-tenant
        )

    @property
    def role(self) -> str:
        return "Chief Compliance Officer"

    @property
    def capabilities(self) -> list[str]:
        return [
            "entity-compliance-assessment",
            "risk-aggregation",
            "multi-jurisdiction-coordination",
            "escalation-routing",
            "dashboard-reporting",
        ]

    async def execute(self, context: dict[str, Any], db_session: AsyncSession) -> AgentResult:
        """
        Main orchestration logic.

        Context keys:
        - task: "assess_entity" | "get_risk_report" | "monitor_deadlines"
        - tenant_id: (required)
        - entity_id: (for entity tasks)
        - jurisdiction: (optional, for single-jurisdiction assessments)
        """
        task = context.get("task", "assess_entity")
        tenant_id = context.get("tenant_id")
        entity_id = context.get("entity_id")

        if not tenant_id:
            return AgentResult(success=False, error="tenant_id required")

        # Dispatch to appropriate handler
        if task == "assess_entity":
            return await self._assess_entity(entity_id, tenant_id, db_session)
        elif task == "get_risk_report":
            return await self._get_risk_report(tenant_id, db_session)
        elif task == "monitor_deadlines":
            return await self._monitor_deadlines(tenant_id, db_session)
        else:
            return AgentResult(success=False, error=f"Unknown task: {task}")

    async def _assess_entity(
        self, entity_id: str, tenant_id: str, db_session: AsyncSession
    ) -> AgentResult:
        """
        Comprehensive compliance assessment for a single entity.

        Delegates to:
        1. Domain agents (for jurisdiction-specific regulations)
        2. Skill agents (for compliance scoring, gap analysis, KYC)
        """
        from app.agents.agent_registry import AgentRegistry

        try:
            # Load entity
            entity = (
                await db_session.execute(
                    select(ComplianceEntity).where(
                        ComplianceEntity.id == entity_id,
                        ComplianceEntity.tenant_id == tenant_id,
                    )
                )
            ).scalar_one_or_none()

            if not entity:
                return AgentResult(success=False, error=f"Entity {entity_id} not found")

            registry = AgentRegistry()

            # Parallel delegation to domain agents (by jurisdiction)
            jurisdictions = self._infer_jurisdictions(entity)
            domain_agents = [
                f"domain:{jur.lower()}"
                for jur in jurisdictions
                if registry.get_agent(f"domain:{jur.lower()}")
            ]

            context = {
                "task": "assess_entity",
                "tenant_id": tenant_id,
                "entity_id": entity_id,
                "entity_type": entity.entity_type.value,
                "sectors": entity.sectors or [],
            }

            domain_results = await registry.broadcast(
                "supervisor:director",
                domain_agents,
                context,
                db_session,
            )

            # Delegate to skill agents (M1-M6)
            skill_agents = ["skill:regulatory_intel", "skill:gap_analysis", "skill:governance"]
            skill_results = await registry.broadcast(
                "supervisor:director",
                skill_agents,
                context,
                db_session,
            )

            # Compute compliance score
            score_obj = await compute_score(entity_id=entity_id, tenant_id=tenant_id)

            # Aggregate
            return AgentResult(
                success=True,
                data={
                    "entity_id": entity_id,
                    "entity_name": entity.name,
                    "compliance_score": score_obj.score_pct if score_obj else 0.0,
                    "domain_assessments": domain_results,
                    "skill_assessments": skill_results,
                    "recommendation": self._compute_recommendation(domain_results, skill_results),
                },
                agent_id=self.agent_id,
            )

        except Exception as e:
            logger.error(f"Error assessing entity: {e}")
            return AgentResult(success=False, error=str(e), agent_id=self.agent_id)

    async def _get_risk_report(
        self, tenant_id: str, db_session: AsyncSession
    ) -> AgentResult:
        """
        Tenant-wide risk dashboard.

        Aggregates risk from all entities, all jurisdictions.
        """
        try:
            # Load all entities for tenant
            entities = (
                await db_session.execute(
                    select(ComplianceEntity).where(ComplianceEntity.tenant_id == tenant_id)
                )
            ).scalars().all()

            # Assess each entity (simplified)
            assessments = []
            for entity in entities:
                score_obj = await compute_score(entity_id=str(entity.id), tenant_id=tenant_id)
                assessments.append(
                    {
                        "entity_id": str(entity.id),
                        "entity_name": entity.name,
                        "score": score_obj.score_pct if score_obj else 0.0,
                    }
                )

            # Aggregate risk
            avg_score = sum(a["score"] for a in assessments) / len(assessments) if assessments else 0
            risk_level = (
                "critical"
                if avg_score < 25
                else "high"
                if avg_score < 50
                else "medium"
                if avg_score < 75
                else "low"
            )

            return AgentResult(
                success=True,
                data={
                    "tenant_id": tenant_id,
                    "entity_count": len(entities),
                    "avg_compliance_score": avg_score,
                    "risk_level": risk_level,
                    "entities": assessments,
                },
                agent_id=self.agent_id,
            )

        except Exception as e:
            logger.error(f"Error generating risk report: {e}")
            return AgentResult(success=False, error=str(e), agent_id=self.agent_id)

    async def _monitor_deadlines(
        self, tenant_id: str, db_session: AsyncSession
    ) -> AgentResult:
        """
        Delegate to M4 monitoring agent to check upcoming deadlines.
        """
        from app.agents.agent_registry import AgentRegistry

        registry = AgentRegistry()
        monitoring_agent = registry.get_agent("skill:monitoring")

        if not monitoring_agent:
            return AgentResult(
                success=False,
                error="Monitoring agent not available",
                agent_id=self.agent_id,
            )

        context = {"task": "check_deadlines", "tenant_id": tenant_id}
        result = await monitoring_agent.execute_safe(context, db_session)

        return result if result else AgentResult(success=False, error="No result from agent")

    def _infer_jurisdictions(self, entity) -> list[str]:
        """
        Infer which jurisdictions apply to this entity based on sectors.

        E.g., if entity.sectors = ["banking", "fintech"], infer all LATAM jurisdictions.
        """
        # Simplified: return all LATAM jurisdictions
        return ["AR", "BR", "CO", "CL", "MX"]

    def _compute_recommendation(self, domain_results: dict, skill_results: dict) -> str:
        """
        Compute human-readable recommendation from aggregated results.
        """
        # Placeholder: real implementation would analyze results
        return "Continue compliance monitoring and review identified gaps quarterly"
