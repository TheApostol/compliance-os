"""
ComplianceOS Agent Framework

Exports main agent classes and initialization functions.
"""

from app.agents.agent_registry import AgentRegistry
from app.agents.base import Agent, AgentMessage, AgentResult, AgentStatus, AgentType
from app.agents.supervisor.compliance_director import ComplianceDirector
from app.agents.domain.latam_regulators import (
    ArgentinaAgent,
    BrazilAgent,
    ChileAgent,
    ColombiaAgent,
    MexicoAgent,
    AndeanAgent,
)
from app.agents.skills.module_agents import (
    RegulatoryIntelligenceAgent,
    ComplianceCopilotAgent,
    KYCMLAgent,
    MonitoringAgent,
    AIGovernanceAgent,
    EvidenceAutomationAgent,
    create_all_module_agents,
)

__all__ = [
    # Base classes
    "Agent",
    "AgentMessage",
    "AgentResult",
    "AgentStatus",
    "AgentType",
    # Registry
    "AgentRegistry",
    # Supervisor
    "ComplianceDirector",
    # Domain agents
    "ArgentinaAgent",
    "BrazilAgent",
    "ChileAgent",
    "ColombiaAgent",
    "MexicoAgent",
    "AndeanAgent",
    # Module agents
    "RegulatoryIntelligenceAgent",
    "ComplianceCopilotAgent",
    "KYCMLAgent",
    "MonitoringAgent",
    "AIGovernanceAgent",
    "EvidenceAutomationAgent",
    # Utilities
    "create_all_module_agents",
    "initialize_agents",
]


def initialize_agents() -> AgentRegistry:
    """
    Initialize all agents and register them in the global registry.

    Call this once at application startup.
    """
    registry = AgentRegistry()

    # Register supervisor
    registry.register(ComplianceDirector())

    # Register domain agents (LATAM)
    registry.register(ArgentinaAgent())
    registry.register(BrazilAgent())
    registry.register(ChileAgent())
    registry.register(ColombiaAgent())
    registry.register(MexicoAgent())
    registry.register(AndeanAgent())

    # Register module agents (M1-M6)
    for agent in create_all_module_agents().values():
        registry.register(agent)

    # Log stats
    stats = registry.stats()
    print(f"✓ Initialized {stats['total_agents']} agents:")
    print(f"  - Supervisor: 1")
    print(f"  - Domain agents: {stats['by_type'].get('domain', 0)}")
    print(f"  - Skill agents: {stats['by_type'].get('skill', 0)}")

    return registry
