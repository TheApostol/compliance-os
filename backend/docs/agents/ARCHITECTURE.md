# ComplianceOS Agent Architecture

## Overview

The agent framework adds a reasoning/coordination layer on top of ComplianceOS modules. Agents:
- **Wrap** module logic without replacing it
- **Reason** about compliance decisions using the AI orchestrator
- **Delegate** tasks to other agents (supervisor → domain → skill)
- **Aggregate** results from multiple sources
- **Audit** every decision via the INSERT-ONLY audit log

---

## Three-Tier Hierarchy

```
┌─────────────────────────────────────────┐
│      Supervisor Agent (1)               │
│    ComplianceDirector: CCO               │
└─────────────────────────────────────────┘
              ↓ delegates to
┌──────────────────────────────────────────────────────────┐
│         Domain Agents (6 LATAM jurisdictions)            │
│  AR (BCRA), BR (BCB), CO (SuperFin), CL (CMF),          │
│  MX (CNBV), ANDEAN (CONASIF)                             │
└──────────────────────────────────────────────────────────┘
              ↓ coordinates with
┌──────────────────────────────────────────────────────────┐
│           Skill Agents (6 modules)                       │
│  M1 Regulatory, M2 Copilot, M3 KYC/AML, M4 Monitor,    │
│  M5 Governance, M6 Evidence                              │
└──────────────────────────────────────────────────────────┘
```

---

## Agent Types

### Supervisor Agent

**Role:** Chief Compliance Officer  
**ID:** `supervisor:director`  
**Type:** `AgentType.SUPERVISOR`

**Responsibilities:**
- Receive high-level compliance requests
- Delegate to domain and skill agents in parallel
- Aggregate multi-jurisdictional results
- Escalate risks to governance
- Serve dashboard and reporting APIs

**Example Flow:**
```
User: "How compliant is Company XYZ?"
  ↓
ComplianceDirector receives request
  ↓
Delegates to:
  - ArgentinaAgent (BCRA regulations)
  - BrazilAgent (BCB regulations)
  - ChileAgent (CMF regulations)
  - KYCMLAgent (AML assessment)
  - MonitoringAgent (deadline tracking)
  ↓
Aggregates → "73% compliant, 3 gaps, 1 deadline in 30 days"
```

### Domain Agents (Regulatory)

**Type:** `AgentType.DOMAIN`  
**Instances:** 6 (one per LATAM jurisdiction)

| Agent | ID | Regulators | Sectors |
|-------|----|----|---------|
| Argentina | `domain:ar` | BCRA, AFIP, CNV | Banking, Fintech, Crypto |
| Brazil | `domain:br` | BCB, CVM, COAF | Banking, Fintech, Pix, Crypto |
| Colombia | `domain:co` | SuperFinanciera, DIAN | Banking, Fintech |
| Chile | `domain:cl` | CMF, SBIF | Banking, Fintech, Pension |
| Mexico | `domain:mx` | CNBV, SAT, SHCP | Banking, Fintech |
| Andean | `domain:andean` | CONASIF | Multi-country |

**Responsibilities:**
- Track regulations for their jurisdiction
- Map regulations to applicable sectors/entity-types
- Calculate enforcement risk
- Provide deadline rules
- Stay updated on regulatory changes

**Example Task:**
```python
# Brazil agent assesses whether Company XYZ must comply with Pix regulations
agent = registry.get_agent("domain:br")
result = await agent.execute({
    "task": "assess_entity",
    "entity_id": "xyz",
    "entity_type": "fintech",
    "sectors": ["fintech", "payments"],
    "tenant_id": "polkorp"
}, db_session)
# → "7 Pix regulations apply, highest risk: MFA requirements"
```

### Skill Agents (Module-Based)

**Type:** `AgentType.SKILL`  
**Instances:** 6 (one per module M1-M6)

| Agent | Module | ID | Capabilities |
|-------|--------|----|----|
| Regulatory Intel | M1 | `skill:m1` | Fetch, parse, structure regulations |
| Copilot | M2 | `skill:m2` | Answer compliance Q&A |
| KYC/AML | M3 | `skill:m3` | Risk assessment, case management |
| Monitoring | M4 | `skill:m4` | Deadline tracking, scoring |
| Governance | M5 | `skill:m5` | Model registry, approval |
| Evidence | M6 | `skill:m6` | Document extraction, audit trail |

**Responsibilities:**
- Wrap module logic with reasoning
- Interface with AI orchestrator for explanations
- Support supervisor delegation
- Can be called independently for testing

**Example Task:**
```python
# Copilot agent answers a user question
agent = registry.get_agent("skill:m2")
result = await agent.execute({
    "task": "answer_question",
    "question": "What are Brazil's AML reporting requirements?",
    "tenant_id": "polkorp"
}, db_session)
# → LLM-generated explanation of COAF reporting rules
```

---

## Agent Lifecycle

### Initialization

```python
# At application startup (backend/app/main.py)
from app.agents import initialize_agents

registry = initialize_agents()
# ✓ Initializes 13 agents (1 supervisor + 6 domain + 6 skill)
# ✓ Registers in global singleton registry
# ✓ Ready for requests
```

### Execution Flow

```python
# Any external interface can invoke agents:

# Option 1: Direct invocation
agent = registry.get_agent("skill:m4")
result = await agent.execute_safe(context, db_session)

# Option 2: Message-based (async)
message = AgentMessage(
    from_agent="supervisor:director",
    to_agent="domain:br",
    task="assess_entity",
    context={...}
)
response = await registry.send_message(message, db_session)

# Option 3: Broadcast (parallel delegation)
results = await registry.broadcast(
    from_agent="supervisor:director",
    to_agents=["domain:ar", "domain:br", "domain:cl"],
    context={...},
    db_session=db_session
)
```

### Multi-Tenancy

**Every agent must validate tenant_id:**

```python
async def execute(self, context, db_session):
    tenant_id = context.get("tenant_id")
    if not tenant_id:
        raise ValueError("tenant_id required")
    
    # All DB queries scoped by tenant_id
    result = await db_session.execute(
        select(Entity).where(Entity.tenant_id == tenant_id)
    )
```

### Audit Trail

**Every agent decision is logged:**

```python
# Automatically logged by Agent.execute_safe()
audit_log(
    tenant_id=context["tenant_id"],
    action="agent:skill:m4:check_deadlines",
    resource="agent",
    resource_id="skill:m4",
    status="success",
    details={"deadlines_checked": 5, "alerts_created": 2}
)
```

---

## Integration Points

### With API Layer

```python
# backend/app/api/v1/agents.py (new endpoint)

@router.post("/agents/assess")
async def assess_entity(request: EntityAssessmentRequest, db: AsyncSession):
    """Trigger full compliance assessment via ComplianceDirector."""
    registry = AgentRegistry()
    director = registry.get_agent("supervisor:director")
    
    result = await director.execute_safe({
        "task": "assess_entity",
        "tenant_id": request.tenant_id,
        "entity_id": request.entity_id,
    }, db)
    
    return result.data
```

### With AI Orchestrator

```python
# Agents call orchestrator for reasoning
orch = get_orchestrator()

result = await orch.infer(InferenceRequest(
    task=TaskType.COPILOT_QA,
    system="You are a compliance expert...",
    user_prompt="Why is this regulation important?",
    tenant_id=context["tenant_id"],
))
```

### With Modules

```python
# Agents call module functions (not replacing them)
from app.modules.monitoring.deadline_checker import check_deadlines

result = await check_deadlines(tenant_id)
# Agent wraps and logs the result
```

---

## Example Workflows

### Workflow 1: Full Entity Assessment

```
User calls: POST /api/v1/agents/assess
  ├─ tenant: "polkorp"
  └─ entity_id: "corp-123"

ComplianceDirector
  ├─ Delegates to: ArgentinaAgent, BrazilAgent, ChileAgent
  ├─ Delegates to: KYCMLAgent, MonitoringAgent, GovernanceAgent
  │
  ├─ ArgentinaAgent
  │  └─ Finds 12 BCRA regulations applicable to fintech
  │
  ├─ BrazilAgent
  │  └─ Finds 18 BCB regulations + Pix requirements
  │
  ├─ KYCMLAgent
  │  └─ Risk assessment: MEDIUM (no PEP match, 1 open case)
  │
  ├─ MonitoringAgent
  │  └─ 3 deadlines in 30 days (compliance priority: HIGH)
  │
  └─ Aggregates
     └─ Returns: "73% compliant, 4 gaps, 3 deadlines"
```

### Workflow 2: Copilot Q&A

```
User: "What does Brazil's Pix regulation require?"

ComplianceCopilotAgent
  ├─ Receives question
  ├─ Calls AI Orchestrator:
  │  "Explain Brazil's Pix AML requirements..."
  ├─ LLM generates explanation
  └─ Returns to user
```

### Workflow 3: Deadline Monitoring

```
Cron job: Every 6 hours

MonitoringAgent
  ├─ Calls check_deadlines(tenant_id)
  ├─ Creates/updates DeadlineAlert records
  ├─ Logs to audit_log
  └─ Triggers webhook to frontend (if critical)
```

---

## Best Practices

### 1. Always Validate tenant_id

```python
async def execute(self, context, db_session):
    tenant_id = context.get("tenant_id")
    if not tenant_id:
        return AgentResult(success=False, error="tenant_id required")
    # ... rest of logic
```

### 2. Use execute_safe(), Not execute()

```python
# ✓ Good: automatic audit logging + error handling
result = await agent.execute_safe(context, db_session)

# ✗ Bad: no audit trail, raw exceptions
result = await agent.execute(context, db_session)
```

### 3. Delegate Parallel Work

```python
# ✓ Good: 3 domain agents in parallel
results = await registry.broadcast(
    from_agent="supervisor:director",
    to_agents=["domain:ar", "domain:br", "domain:cl"],
    context=...,
    db_session=db_session
)

# ✗ Bad: sequential (slow)
for agent_id in ["domain:ar", "domain:br", "domain:cl"]:
    await registry.send_message(...)
```

### 4. Log Decisions

```python
# Agents automatically log via execute_safe(), but you can add detail:
from app.core.audit import audit_log

await audit_log(
    db_session,
    tenant_id=context["tenant_id"],
    action="agent:domain:br:escalate_risk",
    resource="agent",
    resource_id="domain:br",
    status="success",
    details={"risk_level": "critical", "reason": "OFAC match found"}
)
```

---

## Testing Agents

See `backend/tests/test_agents/` for unit tests. Example:

```python
# test_agents/test_supervisor.py
@pytest.mark.asyncio
async def test_director_assesses_entity(db_session):
    registry = AgentRegistry()
    director = registry.get_agent("supervisor:director")
    
    result = await director.execute_safe({
        "task": "assess_entity",
        "tenant_id": "test-tenant",
        "entity_id": "test-entity",
    }, db_session)
    
    assert result.success
    assert result.data["compliance_score"] is not None
```

---

## Future Enhancements

1. **Agent Memory:** Persistent state for domain agents (e.g., "last_regulation_fetch: 2026-06-30")
2. **Agent Chains:** Compose multiple agents into workflows (e.g., "Assess → Identify Gaps → Create Action Plan")
3. **Tool Use:** Agents invoke MCP tools directly (e.g., graph_query, deadline_calc)
4. **Streaming:** Stream agent decisions to frontend in real-time
5. **Cost Tracking:** Track AI orchestrator token usage per agent/tenant

---

*Last updated: 2026-06-30*
