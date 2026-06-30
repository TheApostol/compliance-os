"""
Agent Registry — Manages agent lifecycle, discovery, and message passing.

Single source of truth for all agents in the system.
Handles:
- Agent registration and lifecycle
- Message routing between agents
- Delegation and parallel execution
- Agent capability discovery
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from app.agents.base import Agent, AgentMessage, AgentStatus, AgentType

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Global registry of all agents."""

    _instance: Optional[AgentRegistry] = None
    _agents: dict[str, Agent] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register(self, agent: Agent) -> None:
        """Register an agent in the registry."""
        if agent.agent_id in self._agents:
            logger.warning(f"Agent {agent.agent_id} already registered, overwriting")
        self._agents[agent.agent_id] = agent
        logger.info(f"Registered agent: {agent.agent_id} ({agent.role})")

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID."""
        return self._agents.get(agent_id)

    def list_agents(self, agent_type: Optional[AgentType] = None) -> list[Agent]:
        """List all agents, optionally filtered by type."""
        if agent_type:
            return [a for a in self._agents.values() if a.agent_type == agent_type]
        return list(self._agents.values())

    def list_agents_by_capability(self, capability: str) -> list[Agent]:
        """Find agents that have a specific capability."""
        return [a for a in self._agents.values() if capability in a.capabilities]

    def list_domain_agents_for_jurisdiction(self, jurisdiction: str) -> list[Agent]:
        """Find domain agents for a specific jurisdiction."""
        return [
            a
            for a in self._agents.values()
            if a.agent_type == AgentType.DOMAIN
            and hasattr(a, "jurisdiction")
            and a.jurisdiction == jurisdiction
        ]

    async def send_message(
        self,
        message: AgentMessage,
        db_session: "AsyncSession",
    ) -> Optional[AgentMessage]:
        """
        Send a message from one agent to another.

        Returns the response message if successful.
        """
        target_agent = self.get_agent(message.to_agent)
        if not target_agent:
            logger.error(f"Agent {message.to_agent} not found")
            return None

        logger.info(
            f"Message from {message.from_agent} → {message.to_agent}: {message.task}"
        )

        # Execute target agent's task
        result = await target_agent.execute_safe(message.context, db_session)

        # Wrap result in response message
        response = AgentMessage(
            from_agent=message.to_agent,
            to_agent=message.from_agent,
            task=f"response:{message.task}",
            context={"result": result.data, "success": result.success},
            response=result.data if result.success else None,
            error=result.error if not result.success else None,
        )

        return response

    async def broadcast(
        self,
        from_agent: str,
        to_agents: list[str],
        context: dict,
        db_session: "AsyncSession",
    ) -> dict[str, dict]:
        """
        Send same message to multiple agents in parallel.

        Returns map of agent_id → result.
        """
        import asyncio

        messages = [
            AgentMessage(
                from_agent=from_agent,
                to_agent=agent_id,
                task=context.get("task", "execute"),
                context=context,
                priority=context.get("priority", 0),
            )
            for agent_id in to_agents
        ]

        # Send all in parallel
        responses = await asyncio.gather(
            *[self.send_message(msg, db_session) for msg in messages],
            return_exceptions=True,
        )

        # Aggregate results
        results = {}
        for agent_id, response in zip(to_agents, responses):
            if isinstance(response, Exception):
                results[agent_id] = {"success": False, "error": str(response)}
            elif response:
                results[agent_id] = {
                    "success": response.response is not None,
                    "data": response.response or {},
                    "error": response.error,
                }
            else:
                results[agent_id] = {"success": False, "error": "No response"}

        return results

    def stats(self) -> dict:
        """Get registry statistics."""
        by_type = {}
        for agent_type in AgentType:
            by_type[agent_type.value] = len(
                [a for a in self._agents.values() if a.agent_type == agent_type]
            )

        return {
            "total_agents": len(self._agents),
            "by_type": by_type,
            "statuses": {
                status.value: len([a for a in self._agents.values() if a.status == status])
                for status in AgentStatus
            },
        }

    def reset(self) -> None:
        """Clear all agents (for testing)."""
        self._agents.clear()
        logger.warning("Agent registry cleared")
