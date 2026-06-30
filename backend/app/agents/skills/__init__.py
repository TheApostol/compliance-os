"""Skill agents for ComplianceOS modules (M1-M6)."""

from app.agents.skills.module_agents import (
    ModuleAgent,
    RegulatoryIntelligenceAgent,
    ComplianceCopilotAgent,
    KYCMLAgent,
    MonitoringAgent,
    AIGovernanceAgent,
    EvidenceAutomationAgent,
    create_all_module_agents,
)

__all__ = [
    "ModuleAgent",
    "RegulatoryIntelligenceAgent",
    "ComplianceCopilotAgent",
    "KYCMLAgent",
    "MonitoringAgent",
    "AIGovernanceAgent",
    "EvidenceAutomationAgent",
    "create_all_module_agents",
]
