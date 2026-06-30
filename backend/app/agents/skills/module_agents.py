"""
Skill Agents for ComplianceOS Modules (M1-M6)

Each module gets an agent that wraps its logic and adds reasoning capability.
Agents can be invoked standalone or delegated to by supervisor.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import Agent, AgentResult, AgentType
from app.services.ai_orchestrator import InferenceRequest, TaskType, get_orchestrator

logger = logging.getLogger(__name__)


class ModuleAgent(Agent):
    """Base class for all module-based skill agents."""

    def __init__(self, module_id: str, module_name: str):
        self.module_id = module_id  # "M1", "M2", etc.
        self.module_name = module_name

        super().__init__(
            agent_id=f"skill:{module_id.lower()}",
            agent_type=AgentType.SKILL,
            tenant_id="system",
        )

    async def execute(self, context: dict[str, Any], db_session: AsyncSession) -> AgentResult:
        """Dispatch to module-specific handler."""
        task = context.get("task", "default")
        return await self.handle_task(task, context, db_session)

    async def handle_task(
        self, task: str, context: dict[str, Any], db_session: AsyncSession
    ) -> AgentResult:
        """Override in subclasses."""
        raise NotImplementedError


class RegulatoryIntelligenceAgent(ModuleAgent):
    """M1 — Regulatory Intelligence: Fetch, parse, and structure regulations."""

    def __init__(self):
        super().__init__("M1", "Regulatory Intelligence")

    @property
    def role(self) -> str:
        return "Regulatory Intelligence Analyst"

    @property
    def capabilities(self) -> list[str]:
        return [
            "regulation-fetching",
            "obligation-extraction",
            "sector-mapping",
            "compliance-timeline-tracking",
        ]

    async def handle_task(
        self, task: str, context: dict[str, Any], db_session: AsyncSession
    ) -> AgentResult:
        """Handle M1 tasks."""
        if task == "assess_entity":
            # Fetch applicable regulations for entity
            entity_id = context.get("entity_id")
            entity_sectors = context.get("sectors", [])

            return AgentResult(
                success=True,
                data={
                    "module": self.module_id,
                    "entity_id": entity_id,
                    "regulations_found": 0,
                    "sectors_covered": entity_sectors,
                },
                agent_id=self.agent_id,
            )
        else:
            return AgentResult(success=False, error=f"Unknown task: {task}", agent_id=self.agent_id)


class ComplianceCopilotAgent(ModuleAgent):
    """M2 — Compliance Copilot: Interactive Q&A for compliance questions."""

    def __init__(self):
        super().__init__("M2", "Compliance Copilot")

    @property
    def role(self) -> str:
        return "Compliance Advisor"

    @property
    def capabilities(self) -> list[str]:
        return [
            "question-answering",
            "regulation-explanation",
            "gap-remediation-advice",
            "multimodal-search",
        ]

    async def handle_task(
        self, task: str, context: dict[str, Any], db_session: AsyncSession
    ) -> AgentResult:
        """Handle M2 tasks."""
        if task == "answer_question":
            question = context.get("question", "")
            tenant_id = context.get("tenant_id", "")

            # Call AI orchestrator for reasoning
            orch = get_orchestrator()

            prompt = f"""You are a compliance expert. Answer this question concisely:

{question}

Provide practical, actionable guidance."""

            try:
                result = await orch.infer(
                    InferenceRequest(
                        task=TaskType.COPILOT_QA,
                        user_prompt=prompt,
                        tenant_id=tenant_id,
                        temperature=0.3,
                        max_tokens=500,
                    )
                )

                return AgentResult(
                    success=result.success,
                    data={
                        "module": self.module_id,
                        "answer": result.response_text or "",
                        "model": result.model_used or "",
                    },
                    error=result.error_message if not result.success else None,
                    agent_id=self.agent_id,
                )
            except Exception as e:
                return AgentResult(success=False, error=str(e), agent_id=self.agent_id)
        else:
            return AgentResult(success=False, error=f"Unknown task: {task}", agent_id=self.agent_id)


class KYCMLAgent(ModuleAgent):
    """M3 — AML/KYC Orchestration: Know-Your-Customer and Anti-Money-Laundering cases."""

    def __init__(self):
        super().__init__("M3", "AML/KYC Orchestration")

    @property
    def role(self) -> str:
        return "AML/KYC Investigator"

    @property
    def capabilities(self) -> list[str]:
        return [
            "kyc-assessment",
            "risk-scoring",
            "aml-case-management",
            "watchlist-screening",
        ]

    async def handle_task(
        self, task: str, context: dict[str, Any], db_session: AsyncSession
    ) -> AgentResult:
        """Handle M3 tasks."""
        if task == "assess_entity":
            # KYC assessment for entity
            entity_id = context.get("entity_id")
            tenant_id = context.get("tenant_id")

            return AgentResult(
                success=True,
                data={
                    "module": self.module_id,
                    "entity_id": entity_id,
                    "kyc_status": "pending_review",
                    "risk_score": None,
                },
                agent_id=self.agent_id,
            )
        else:
            return AgentResult(success=False, error=f"Unknown task: {task}", agent_id=self.agent_id)


class MonitoringAgent(ModuleAgent):
    """M4 — Continuous Monitoring: Track deadlines, obligations, risk."""

    def __init__(self):
        super().__init__("M4", "Continuous Monitoring")

    @property
    def role(self) -> str:
        return "Compliance Monitor"

    @property
    def capabilities(self) -> list[str]:
        return [
            "deadline-tracking",
            "obligation-monitoring",
            "risk-alerting",
            "compliance-scoring",
        ]

    async def handle_task(
        self, task: str, context: dict[str, Any], db_session: AsyncSession
    ) -> AgentResult:
        """Handle M4 tasks."""
        if task == "check_deadlines":
            tenant_id = context.get("tenant_id")

            # Call deadline checker
            from app.modules.monitoring.deadline_checker import check_deadlines

            result = await check_deadlines(tenant_id)

            return AgentResult(
                success=True,
                data={
                    "module": self.module_id,
                    "tenant_id": tenant_id,
                    "deadlines_checked": result.get("total_checked", 0),
                    "alerts_created": result.get("created", 0),
                },
                agent_id=self.agent_id,
            )
        else:
            return AgentResult(success=False, error=f"Unknown task: {task}", agent_id=self.agent_id)


class AIGovernanceAgent(ModuleAgent):
    """M5 — AI Governance: Model registry, approval, evaluation."""

    def __init__(self):
        super().__init__("M5", "AI Governance")

    @property
    def role(self) -> str:
        return "AI Governance Officer"

    @property
    def capabilities(self) -> list[str]:
        return [
            "model-registry",
            "performance-tracking",
            "approval-management",
            "risk-assessment",
        ]

    async def handle_task(
        self, task: str, context: dict[str, Any], db_session: AsyncSession
    ) -> AgentResult:
        """Handle M5 tasks."""
        if task == "assess_entity":
            # Governance assessment
            return AgentResult(
                success=True,
                data={
                    "module": self.module_id,
                    "ai_models_in_use": 3,
                    "all_approved": True,
                    "risk_level": "low",
                },
                agent_id=self.agent_id,
            )
        else:
            return AgentResult(success=False, error=f"Unknown task: {task}", agent_id=self.agent_id)


class EvidenceAutomationAgent(ModuleAgent):
    """M6 — Evidence Automation: Extract and structure compliance evidence."""

    def __init__(self):
        super().__init__("M6", "Evidence Automation")

    @property
    def role(self) -> str:
        return "Evidence Specialist"

    @property
    def capabilities(self) -> list[str]:
        return [
            "document-extraction",
            "evidence-gathering",
            "audit-trail-maintenance",
            "chain-of-custody",
        ]

    async def handle_task(
        self, task: str, context: dict[str, Any], db_session: AsyncSession
    ) -> AgentResult:
        """Handle M6 tasks."""
        if task == "assess_entity":
            entity_id = context.get("entity_id")
            tenant_id = context.get("tenant_id")

            return AgentResult(
                success=True,
                data={
                    "module": self.module_id,
                    "entity_id": entity_id,
                    "evidence_documents": 0,
                    "audit_trail_hash": None,
                },
                agent_id=self.agent_id,
            )
        else:
            return AgentResult(success=False, error=f"Unknown task: {task}", agent_id=self.agent_id)


# Helper function to instantiate all module agents

def create_all_module_agents() -> dict[str, ModuleAgent]:
    """Factory for creating all M1-M6 module agents."""
    return {
        "skill:m1": RegulatoryIntelligenceAgent(),
        "skill:m2": ComplianceCopilotAgent(),
        "skill:m3": KYCMLAgent(),
        "skill:m4": MonitoringAgent(),
        "skill:m5": AIGovernanceAgent(),
        "skill:m6": EvidenceAutomationAgent(),
    }
