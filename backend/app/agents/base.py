"""
Base Agent Class — Foundation for all ComplianceOS agents.

Every agent:
- Has a role, capabilities, and jurisdiction (if domain-specific)
- Communicates via async message passing
- Logs decisions to audit trail
- Respects multi-tenant isolation
- Integrates with AI orchestrator for reasoning
"""

from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class AgentType(str, Enum):
    SUPERVISOR = "supervisor"
    DOMAIN = "domain"
    SKILL = "skill"
    TOOL = "tool"


class AgentStatus(str, Enum):
    IDLE = "idle"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    DELEGATING = "delegating"


@dataclass
class AgentMessage:
    """Message between agents."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    from_agent: str = ""
    to_agent: str = ""
    task: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    priority: int = 0  # 0 = high, 1+ = normal/low
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    response: Optional[dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class AgentResult:
    """Standardized result from any agent operation."""
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    agent_id: str = ""
    execution_time_ms: float = 0.0
    audit_log_entry_id: Optional[str] = None


class Agent(ABC):
    """
    Abstract base class for all agents in ComplianceOS.

    Subclasses must implement:
    - execute(): Main logic for the agent
    - get_capabilities(): List of what this agent can do
    """

    def __init__(self, agent_id: str, agent_type: AgentType, tenant_id: Optional[str] = None):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.tenant_id = tenant_id or "system"
        self.status = AgentStatus.IDLE
        self.created_at = datetime.now(timezone.utc)
        self.last_executed = None

    @property
    @abstractmethod
    def role(self) -> str:
        """E.g., 'Chief Compliance Officer', 'Brazil Regulatory Specialist'"""
        pass

    @property
    @abstractmethod
    def capabilities(self) -> list[str]:
        """E.g., ['risk-assessment', 'obligation-tracking', 'deadline-monitoring']"""
        pass

    @abstractmethod
    async def execute(self, context: dict[str, Any], db_session: AsyncSession) -> AgentResult:
        """
        Main agent logic. Must:
        1. Validate tenant_id in context
        2. Perform task
        3. Log to audit trail
        4. Return standardized AgentResult
        """
        pass

    async def execute_safe(self, context: dict[str, Any], db_session: AsyncSession) -> AgentResult:
        """
        Wrapper around execute() with error handling, logging, and audit trail.

        Subclasses should override execute(), not this method.
        """
        import time
        from app.core.audit import audit_log

        start_time = time.time()
        result = None

        try:
            # Validate tenant_id
            tenant_id = context.get("tenant_id", self.tenant_id)
            if not tenant_id:
                raise ValueError("tenant_id required in context")

            self.status = AgentStatus.PROCESSING
            logger.info(f"Agent {self.agent_id} executing task: {context.get('task', 'unknown')}")

            result = await self.execute(context, db_session)

            self.status = AgentStatus.SUCCEEDED
            self.last_executed = datetime.now(timezone.utc)

            # Log to audit trail
            audit_entry = await audit_log(
                db_session,
                tenant_id=tenant_id,
                action=f"agent:{self.agent_id}:{context.get('task', 'execute')}",
                resource="agent",
                resource_id=self.agent_id,
                status="success",
                details={"result": result.data},
            )
            result.audit_log_entry_id = audit_entry.id if audit_entry else None

        except Exception as e:
            self.status = AgentStatus.FAILED
            error_msg = str(e)
            logger.error(f"Agent {self.agent_id} failed: {error_msg}")

            # Log failure
            try:
                await audit_log(
                    db_session,
                    tenant_id=context.get("tenant_id", self.tenant_id),
                    action=f"agent:{self.agent_id}:{context.get('task', 'execute')}",
                    resource="agent",
                    resource_id=self.agent_id,
                    status="error",
                    details={"error": error_msg},
                )
            except Exception as audit_error:
                logger.error(f"Failed to log agent error: {audit_error}")

            result = AgentResult(success=False, error=error_msg, agent_id=self.agent_id)

        finally:
            result = result or AgentResult(
                success=False, error="Unknown error", agent_id=self.agent_id
            )
            result.execution_time_ms = (time.time() - start_time) * 1000
            return result

    async def delegate(
        self,
        to_agents: list[str],
        context: dict[str, Any],
        db_session: AsyncSession,
        registry: "AgentRegistry",
    ) -> list[AgentResult]:
        """
        Delegate task to multiple agents (e.g., supervisor → domain agents).

        Executes in parallel, waits for all, returns aggregated results.
        """
        import asyncio

        self.status = AgentStatus.DELEGATING
        logger.info(f"Agent {self.agent_id} delegating to: {to_agents}")

        tasks = []
        for agent_id in to_agents:
            agent = registry.get_agent(agent_id)
            if agent:
                tasks.append(agent.execute_safe(context, db_session))
            else:
                logger.warning(f"Agent {agent_id} not found in registry")

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to AgentResult
        final_results = []
        for result in results:
            if isinstance(result, Exception):
                final_results.append(AgentResult(success=False, error=str(result)))
            else:
                final_results.append(result)

        return final_results

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.agent_id} role={self.role} status={self.status}>"
