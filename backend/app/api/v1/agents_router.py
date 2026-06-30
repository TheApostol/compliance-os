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


@router.post(
    "/assess",
    response_model=EntityAssessmentResponse,
    summary="Full Compliance Assessment",
    description="Trigger ComplianceDirector supervisor agent to assess entity compliance across all LATAM jurisdictions (AR, BR, CO, CL, MX, ANDEAN)",
    tags=["agents"],
    responses={
        200: {
            "description": "Assessment completed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "compliance_score": 73.0,
                        "jurisdictions_assessed": ["AR", "BR", "CL"],
                        "applicable_regulations": 47,
                        "gaps": ["MFA not implemented", "Transaction monitoring gaps"],
                        "deadlines_upcoming": 3,
                        "risk_level": "medium"
                    }
                }
            }
        },
        401: {
            "description": "Unauthorized — missing or invalid JWT token",
            "content": {"application/json": {"example": {"detail": "Not authenticated"}}}
        },
        403: {
            "description": "Forbidden — insufficient permissions (must be admin or analyst)",
            "content": {"application/json": {"example": {"detail": "Insufficient permissions"}}}
        },
        422: {
            "description": "Validation error — required fields missing or invalid type",
            "content": {"application/json": {"example": {"detail": "entity_id is required"}}}
        },
        503: {
            "description": "Service unavailable — agent framework not initialized",
            "content": {"application/json": {"example": {"detail": "Agent framework not initialized"}}}
        }
    }
)
async def assess_entity(
    request: EntityAssessmentRequest,
    current_user: User = Depends(get_current_user),
    req: Request = None,
) -> EntityAssessmentResponse:
    """
    Full compliance assessment for an entity.

    **What it does:**
    1. Delegates to 6 LATAM domain agents (AR/BR/CO/CL/MX/ANDEAN) for jurisdiction-specific regulations
    2. Delegates to 6 module skill agents (M1-M6) for comprehensive compliance check
    3. Aggregates results into compliance score, gaps, and recommendations

    **Request fields:**
    - `tenant_id`: Tenant ID (from JWT, required)
    - `entity_id`: Entity UUID to assess (required)
    - `entity_type`: Type of entity (company, fintech, bank, crypto, optional)
    - `sectors`: Business sectors like ["payments", "crypto"] (optional)

    **Response fields:**
    - `success`: Boolean indicating assessment completion
    - `compliance_score`: 0-100 percentage score
    - `jurisdictions_assessed`: List of LATAM jurisdictions evaluated
    - `applicable_regulations`: Count of regulations that apply to this entity
    - `gaps`: List of compliance gaps identified
    - `deadlines_upcoming`: Number of critical deadlines within 90 days
    - `risk_level`: 'low' | 'medium' | 'high' | 'critical'

    **Timing:** Typically 5-30 seconds depending on entity complexity

    **Example curl:**
    ```bash
    curl -X POST http://localhost:8000/api/v1/agents/assess \\
      -H "Authorization: Bearer $JWT_TOKEN" \\
      -H "X-Tenant-Id: polkorp" \\
      -H "Content-Type: application/json" \\
      -d '{
        "tenant_id": "polkorp",
        "entity_id": "corp-123",
        "entity_type": "fintech",
        "sectors": ["payments"]
      }'
    ```

    **Example Python:**
    ```python
    import requests
    response = requests.post(
        "http://localhost:8000/api/v1/agents/assess",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-Id": "polkorp"},
        json={"tenant_id": "polkorp", "entity_id": "corp-123", "entity_type": "fintech"}
    )
    print(response.json()["compliance_score"])
    ```
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


@router.get(
    "/registry",
    response_model=AgentRegistryResponse,
    summary="List All Agents",
    description="Discover registered agents and get framework statistics",
    tags=["agents"],
    responses={
        200: {
            "description": "Agent registry with 13 agents (1 supervisor, 6 domain, 6 skill)",
            "content": {
                "application/json": {
                    "example": {
                        "total_agents": 13,
                        "supervisor_agents": 1,
                        "domain_agents": 6,
                        "skill_agents": 6,
                        "agents": [
                            {
                                "id": "supervisor:director",
                                "type": "supervisor",
                                "role": "Chief Compliance Officer",
                                "capabilities": ["entity-compliance-assessment"]
                            }
                        ]
                    }
                }
            }
        },
        401: {"description": "Unauthorized"}
    }
)
async def get_registry(
    current_user: User = Depends(get_current_user),
    req: Request = None,
) -> AgentRegistryResponse:
    """
    Get agent registry statistics and list of registered agents.

    **Returns:**
    - `total_agents`: Total count (should be 13)
    - `supervisor_agents`: Count of supervisor agents (1)
    - `domain_agents`: Count of LATAM domain agents (6)
    - `skill_agents`: Count of module skill agents (6)
    - `agents`: List of agent metadata with id, type, role, capabilities

    **Use case:** Frontend agent discovery, debugging agent availability
    """
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


@router.get(
    "/capabilities",
    summary="List All Agent Capabilities",
    description="Discover what capabilities are available across all agents",
    tags=["agents"],
)
async def list_capabilities(
    current_user: User = Depends(get_current_user),
    req: Request = None,
):
    """
    List all available agent capabilities across the entire framework.

    **Response format:**
    ```json
    {
      "capabilities": {
        "entity-compliance-assessment": [
          {"agent_id": "supervisor:director", "role": "Chief Compliance Officer"}
        ],
        "risk-aggregation": [...],
        ...
      }
    }
    ```

    **Use case:** Frontend UI to show what operations are available
    """
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


@router.get(
    "/domains",
    summary="List LATAM Domain Agents",
    description="Discover domain agents for each jurisdiction (AR, BR, CO, CL, MX, ANDEAN)",
    tags=["agents"],
)
async def list_domain_agents(
    current_user: User = Depends(get_current_user),
    req: Request = None,
):
    """
    List all LATAM domain agents and their regulatory jurisdictions.

    **Response format:**
    ```json
    {
      "domains": [
        {
          "agent_id": "domain:ar",
          "jurisdiction": "AR",
          "role": "Argentina Regulatory Specialist (BCRA/AFIP)",
          "regulators": ["BCRA", "AFIP", "CNV"]
        },
        ...
      ]
    }
    ```

    **Jurisdictions covered:**
    - AR: Argentina (BCRA, AFIP, CNV)
    - BR: Brazil (BCB, CVM, COAF)
    - CO: Colombia (SuperFinanciera, DIAN)
    - CL: Chile (CMF, SBIF)
    - MX: Mexico (CNBV, SAT, SHCP)
    - ANDEAN: Andean Community (CONASIF)

    **Use case:** Jurisdictional compliance tracking
    """
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


@router.get(
    "/modules",
    summary="List Module Skill Agents",
    description="Discover M1-M6 skill agents and their capabilities",
    tags=["agents"],
)
async def list_skill_agents(
    current_user: User = Depends(get_current_user),
    req: Request = None,
):
    """
    List all module skill agents (M1-M6) and their capabilities.

    **Response format:**
    ```json
    {
      "modules": [
        {
          "agent_id": "skill:m1",
          "module": "SKILL:M1",
          "role": "Regulatory Intelligence Analyst",
          "capabilities": ["regulation-fetching", "obligation-extraction"]
        },
        ...
      ]
    }
    ```

    **Modules:**
    - M1: Regulatory Intelligence (fetches and parses regulations)
    - M2: Compliance Copilot (AI-powered Q&A)
    - M3: KYC/AML Orchestration (risk assessment)
    - M4: Continuous Monitoring (deadline tracking)
    - M5: AI Governance (model registry)
    - M6: Evidence Automation (document extraction & audit trail)

    **Use case:** Module capability discovery, debugging module status
    """
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
