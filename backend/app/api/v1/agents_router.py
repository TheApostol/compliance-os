"""
Agent Framework API Endpoints

Routes for triggering agent-based compliance operations:
- Full entity assessment via ComplianceDirector
- Agent registry queries
- Agent capability discovery
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import AsyncSessionLocal
from app.core.auth import get_current_user
from app.db.models import User

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


class EntityAssessmentRequest(BaseModel):
    """Full compliance assessment for an entity via ComplianceDirector."""
    tenant_id: str = Field(..., description="Tenant ID")
    entity_id: str = Field(..., description="Entity ID to assess")
    entity_type: Optional[str] = Field(default="company", description="Entity type (company, fintech, bank, etc.)")
    sectors: Optional[list[str]] = Field(default=None, description="Business sectors (payments, fintech, etc.)")


class EntityAssessmentResponse(BaseModel):
    """Result of a full compliance assessment."""
    success: bool
    compliance_score: Optional[float] = None
    jurisdictions_assessed: Optional[list[str]] = None
    applicable_regulations: Optional[int] = None
    gaps: Optional[list[str]] = None
    deadlines_upcoming: Optional[int] = None
    risk_level: Optional[str] = None
    error: Optional[str] = None


class AgentRegistryResponse(BaseModel):
    """Agent registry statistics and metadata."""
    total_agents: int
    supervisor_agents: int
    domain_agents: int
    skill_agents: int
    agents: Optional[list[dict]] = None


class AgentCapabilitiesRequest(BaseModel):
    """Query agents by capability."""
    capability: str = Field(..., description="Capability to search for")
    agent_type: Optional[str] = Field(default=None, description="Filter by agent type")


@router.post("/assess", response_model=EntityAssessmentResponse)
async def assess_entity(
    request: EntityAssessmentRequest,
    current_user: User = Depends(get_current_user),
    req: Request = None,
) -> EntityAssessmentResponse:
    """
    Full compliance assessment for an entity.

    Triggers ComplianceDirector supervisor agent to:
    1. Delegate to 6 LATAM domain agents for jurisdiction-specific regulations
    2. Delegate to module skill agents (M1-M6) for comprehensive assessment
    3. Aggregate results into compliance score + recommendations

    Returns: Compliance score, applicable regulations, gaps, upcoming deadlines, risk level.
    """
    db: AsyncSession = req.state.db if hasattr(req.state, "db") else AsyncSessionLocal()
    registry = req.app.state.agent_registry if hasattr(req.app.state, "agent_registry") else None

    try:
        if not registry:
            raise HTTPException(status_code=503, detail="Agent framework not initialized")

        # Get ComplianceDirector supervisor agent
        director = registry.get_agent("supervisor:director")
        if not director:
            raise HTTPException(status_code=500, detail="ComplianceDirector agent not found")

        # Execute assessment via supervisor
        result = await director.execute_safe(
            {
                "task": "assess_entity",
                "tenant_id": request.tenant_id,
                "entity_id": request.entity_id,
                "entity_type": request.entity_type,
                "sectors": request.sectors or [],
            },
            db,
        )

        if result.success:
            data = result.data or {}
            return EntityAssessmentResponse(
                success=True,
                compliance_score=data.get("compliance_score"),
                jurisdictions_assessed=data.get("jurisdictions", []),
                applicable_regulations=data.get("regulations_count", 0),
                gaps=data.get("gaps", []),
                deadlines_upcoming=data.get("deadlines_count", 0),
                risk_level=data.get("risk_level"),
            )
        else:
            return EntityAssessmentResponse(
                success=False,
                error=result.error or "Assessment failed",
            )
    except Exception as e:
        return EntityAssessmentResponse(
            success=False,
            error=str(e),
        )


@router.get("/registry", response_model=AgentRegistryResponse)
async def get_registry(
    current_user: User = Depends(get_current_user),
    req: Request = None,
) -> AgentRegistryResponse:
    """Get agent registry statistics and list of registered agents."""
    registry = req.app.state.agent_registry if hasattr(req.app.state, "agent_registry") else None

    if not registry:
        raise HTTPException(status_code=503, detail="Agent framework not initialized")

    stats = registry.stats()

    agents_list = []
    for agent_id, agent in registry.list_agents():
        agents_list.append({
            "id": agent_id,
            "type": agent.agent_type.value if hasattr(agent, "agent_type") else "unknown",
            "role": agent.role if hasattr(agent, "role") else "unknown",
            "capabilities": agent.capabilities if hasattr(agent, "capabilities") else [],
        })

    return AgentRegistryResponse(
        total_agents=stats.get("total_agents", 0),
        supervisor_agents=stats.get("by_type", {}).get("supervisor", 0),
        domain_agents=stats.get("by_type", {}).get("domain", 0),
        skill_agents=stats.get("by_type", {}).get("skill", 0),
        agents=agents_list,
    )


@router.get("/capabilities")
async def list_capabilities(
    current_user: User = Depends(get_current_user),
    req: Request = None,
):
    """List all available agent capabilities."""
    registry = req.app.state.agent_registry if hasattr(req.app.state, "agent_registry") else None

    if not registry:
        raise HTTPException(status_code=503, detail="Agent framework not initialized")

    capabilities = {}
    for agent_id, agent in registry.list_agents():
        caps = agent.capabilities if hasattr(agent, "capabilities") else []
        for cap in caps:
            if cap not in capabilities:
                capabilities[cap] = []
            capabilities[cap].append({
                "agent_id": agent_id,
                "role": agent.role if hasattr(agent, "role") else "unknown",
            })

    return {"capabilities": capabilities}


@router.get("/domains")
async def list_domain_agents(
    current_user: User = Depends(get_current_user),
    req: Request = None,
):
    """List all LATAM domain agents and their jurisdictions."""
    registry = req.app.state.agent_registry if hasattr(req.app.state, "agent_registry") else None

    if not registry:
        raise HTTPException(status_code=503, detail="Agent framework not initialized")

    domains = []
    for agent_id, agent in registry.list_agents():
        if hasattr(agent, "jurisdiction"):
            domains.append({
                "agent_id": agent_id,
                "jurisdiction": agent.jurisdiction,
                "role": agent.role if hasattr(agent, "role") else "unknown",
                "regulators": agent.regulators if hasattr(agent, "regulators") else [],
            })

    return {"domains": domains}


@router.get("/modules")
async def list_skill_agents(
    current_user: User = Depends(get_current_user),
    req: Request = None,
):
    """List all module skill agents (M1-M6)."""
    registry = req.app.state.agent_registry if hasattr(req.app.state, "agent_registry") else None

    if not registry:
        raise HTTPException(status_code=503, detail="Agent framework not initialized")

    modules = []
    for agent_id, agent in registry.list_agents():
        if agent_id.startswith("skill:m"):
            modules.append({
                "agent_id": agent_id,
                "module": agent_id.upper(),
                "role": agent.role if hasattr(agent, "role") else "unknown",
                "capabilities": agent.capabilities if hasattr(agent, "capabilities") else [],
            })

    return {"modules": modules}
