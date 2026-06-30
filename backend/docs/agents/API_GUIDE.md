# ComplianceOS Agent Framework — API Guide

**Date:** 2026-06-30  
**Status:** Production Ready  
**Base URL:** `https://api.complianceos.io/api/v1` (or `http://localhost:8000/api/v1` for local)

---

## Quick Start

### 1. Authenticate

Get a JWT token from `/api/v1/auth/login`:

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "your-password"}'

# Response:
# {
#   "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
#   "token_type": "bearer"
# }
```

### 2. Call an Agent Endpoint

```bash
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

curl -X POST http://localhost:8000/api/v1/agents/assess \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-Id: polkorp" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "polkorp",
    "entity_id": "corp-123",
    "entity_type": "fintech"
  }'
```

### 3. Parse the Response

```json
{
  "success": true,
  "compliance_score": 73.0,
  "jurisdictions_assessed": ["AR", "BR", "CL"],
  "applicable_regulations": 47,
  "gaps": [
    "MFA not implemented for customer-facing systems",
    "Transaction monitoring AML gaps in Brazil"
  ],
  "deadlines_upcoming": 3,
  "risk_level": "medium"
}
```

---

## API Endpoints

### POST `/agents/assess`

**Purpose:** Trigger ComplianceDirector to assess entity compliance across all LATAM jurisdictions.

**Authentication:** Required (JWT token + X-Tenant-Id header)

**Request Body:**

```json
{
  "tenant_id": "polkorp",
  "entity_id": "corp-123",
  "entity_type": "fintech",
  "sectors": ["payments", "crypto"]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `tenant_id` | string | Yes | Tenant ID (from JWT claim, validated) |
| `entity_id` | string | Yes | Entity UUID to assess |
| `entity_type` | string | No | Type: company, fintech, bank, crypto (default: company) |
| `sectors` | array | No | Business sectors: payments, crypto, etc. |

**Response (200 OK):**

```json
{
  "success": true,
  "compliance_score": 73.0,
  "jurisdictions_assessed": ["AR", "BR", "CL"],
  "applicable_regulations": 47,
  "gaps": [
    "MFA not implemented",
    "Transaction monitoring gaps"
  ],
  "deadlines_upcoming": 3,
  "risk_level": "medium"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Assessment completed without errors |
| `compliance_score` | number | 0-100 compliance percentage |
| `jurisdictions_assessed` | array | LATAM jurisdictions evaluated (AR/BR/CO/CL/MX/ANDEAN) |
| `applicable_regulations` | number | Count of regulations applicable to entity |
| `gaps` | array | Identified compliance gaps |
| `deadlines_upcoming` | number | Critical deadlines in next 90 days |
| `risk_level` | string | low, medium, high, critical |

**Response (401 Unauthorized):**

```json
{
  "detail": "Not authenticated"
}
```

**Response (403 Forbidden):**

```json
{
  "detail": "Insufficient permissions"
}
```

**Response (503 Service Unavailable):**

```json
{
  "detail": "Agent framework not initialized"
}
```

**Timing:** 5-30 seconds (depends on entity complexity and number of applicable regulations)

**Behind the Scenes:**

1. ComplianceDirector receives request
2. Validates tenant_id from JWT
3. Delegates to 6 domain agents in parallel (AR, BR, CO, CL, MX, ANDEAN)
4. Each domain agent queries applicable regulations for entity
5. Delegates to 6 skill agents in parallel (M1-M6)
6. Aggregates results into compliance_score + gaps + deadlines
7. Logs entire operation to audit_log (hash-chained)

---

### GET `/agents/registry`

**Purpose:** Discover all registered agents and framework statistics.

**Authentication:** Required (JWT token)

**Query Parameters:** None

**Response (200 OK):**

```json
{
  "total_agents": 13,
  "supervisor_agents": 1,
  "domain_agents": 6,
  "skill_agents": 6,
  "agents": [
    {
      "id": "supervisor:director",
      "type": "supervisor",
      "role": "Chief Compliance Officer",
      "capabilities": [
        "entity-compliance-assessment",
        "risk-aggregation",
        "multi-jurisdiction-coordination"
      ]
    },
    {
      "id": "domain:ar",
      "type": "domain",
      "role": "Argentina Regulatory Specialist (BCRA/AFIP)",
      "capabilities": [
        "jurisdiction-assessment",
        "regulation-tracking"
      ]
    },
    {
      "id": "skill:m1",
      "type": "skill",
      "role": "Regulatory Intelligence Analyst",
      "capabilities": [
        "regulation-fetching",
        "obligation-extraction"
      ]
    }
  ]
}
```

**Use Case:** Frontend agent discovery, debugging agent availability, system health check

---

### GET `/agents/capabilities`

**Purpose:** List all available capabilities across the framework.

**Authentication:** Required (JWT token)

**Query Parameters:** None

**Response (200 OK):**

```json
{
  "capabilities": {
    "entity-compliance-assessment": [
      {
        "agent_id": "supervisor:director",
        "role": "Chief Compliance Officer"
      }
    ],
    "risk-aggregation": [
      {
        "agent_id": "supervisor:director",
        "role": "Chief Compliance Officer"
      }
    ],
    "jurisdiction-assessment": [
      {
        "agent_id": "domain:ar",
        "role": "Argentina Regulatory Specialist"
      },
      {
        "agent_id": "domain:br",
        "role": "Brazil Regulatory Specialist"
      }
    ],
    "regulation-fetching": [
      {
        "agent_id": "skill:m1",
        "role": "Regulatory Intelligence Analyst"
      }
    ]
  }
}
```

**Use Case:** UI capability explorer, feature availability checking

---

### GET `/agents/domains`

**Purpose:** List LATAM domain agents and their regulatory jurisdictions.

**Authentication:** Required (JWT token)

**Query Parameters:** None

**Response (200 OK):**

```json
{
  "domains": [
    {
      "agent_id": "domain:ar",
      "jurisdiction": "AR",
      "role": "Argentina Regulatory Specialist (BCRA/AFIP)",
      "regulators": ["BCRA", "AFIP", "CNV"]
    },
    {
      "agent_id": "domain:br",
      "jurisdiction": "BR",
      "role": "Brazil Regulatory Specialist (BCB/CVM)",
      "regulators": ["BCB", "CVM", "COAF"]
    },
    {
      "agent_id": "domain:co",
      "jurisdiction": "CO",
      "role": "Colombia Regulatory Specialist",
      "regulators": ["SuperFinanciera", "DIAN"]
    },
    {
      "agent_id": "domain:cl",
      "jurisdiction": "CL",
      "role": "Chile Regulatory Specialist",
      "regulators": ["CMF", "SBIF"]
    },
    {
      "agent_id": "domain:mx",
      "jurisdiction": "MX",
      "role": "Mexico Regulatory Specialist",
      "regulators": ["CNBV", "SAT", "SHCP"]
    },
    {
      "agent_id": "domain:andean",
      "jurisdiction": "ANDEAN",
      "role": "Andean Community Regulatory Specialist",
      "regulators": ["CONASIF"]
    }
  ]
}
```

**Jurisdiction Reference:**

| Code | Country | Regulators |
|------|---------|-----------|
| AR | Argentina | BCRA (Central Bank), AFIP (Tax Authority), CNV (Securities) |
| BR | Brazil | BCB (Central Bank), CVM (Securities), COAF (AML) |
| CO | Colombia | SuperFinanciera (Financial Superintendent), DIAN (Tax) |
| CL | Chile | CMF (Financial Market Commission), SBIF (Banking Superintendent) |
| MX | Mexico | CNBV (Securities Commission), SAT (Tax), SHCP (Treasury) |
| ANDEAN | Andean Pact | CONASIF (Andean Community Financial Superintendents) |

**Use Case:** Jurisdictional compliance tracking, regulatory landscape understanding

---

### GET `/agents/modules`

**Purpose:** List M1-M6 skill agents and their module capabilities.

**Authentication:** Required (JWT token)

**Query Parameters:** None

**Response (200 OK):**

```json
{
  "modules": [
    {
      "agent_id": "skill:m1",
      "module": "SKILL:M1",
      "role": "Regulatory Intelligence Analyst",
      "capabilities": [
        "regulation-fetching",
        "obligation-extraction",
        "regulatory-change-tracking"
      ]
    },
    {
      "agent_id": "skill:m2",
      "module": "SKILL:M2",
      "role": "Compliance Advisor",
      "capabilities": [
        "question-answering",
        "regulation-explanation",
        "compliance-guidance"
      ]
    },
    {
      "agent_id": "skill:m3",
      "module": "SKILL:M3",
      "role": "AML/KYC Investigator",
      "capabilities": [
        "risk-assessment",
        "case-management",
        "screening"
      ]
    },
    {
      "agent_id": "skill:m4",
      "module": "SKILL:M4",
      "role": "Compliance Monitor",
      "capabilities": [
        "deadline-tracking",
        "obligation-monitoring",
        "alert-generation"
      ]
    },
    {
      "agent_id": "skill:m5",
      "module": "SKILL:M5",
      "role": "AI Governance Officer",
      "capabilities": [
        "model-registry",
        "performance-tracking",
        "approval-workflow"
      ]
    },
    {
      "agent_id": "skill:m6",
      "module": "SKILL:M6",
      "role": "Evidence Specialist",
      "capabilities": [
        "document-extraction",
        "audit-trail-maintenance",
        "evidence-collection"
      ]
    }
  ]
}
```

| Module | Purpose | Key Capability |
|--------|---------|----------------|
| M1 | Regulatory Intelligence | Fetches and structures regulations from 50+ LATAM sources |
| M2 | Compliance Copilot | AI-powered Q&A about regulations and compliance |
| M3 | KYC/AML | Customer due diligence and AML screening |
| M4 | Monitoring | Continuous deadline tracking and obligation monitoring |
| M5 | AI Governance | Model registry and performance evaluation |
| M6 | Evidence | Automatic evidence collection and audit trail |

**Use Case:** Module capability discovery, feature availability checking, debugging module status

---

## Examples

### Python

```python
import requests
import json

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
TOKEN = "your-jwt-token"
TENANT_ID = "polkorp"

def assess_entity(entity_id: str, entity_type: str = "company"):
    """Run full compliance assessment for an entity."""
    
    response = requests.post(
        f"{BASE_URL}/agents/assess",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "X-Tenant-Id": TENANT_ID,
            "Content-Type": "application/json",
        },
        json={
            "tenant_id": TENANT_ID,
            "entity_id": entity_id,
            "entity_type": entity_type,
            "sectors": ["payments", "fintech"],
        }
    )
    
    result = response.json()
    
    if result["success"]:
        print(f"✓ Assessment Complete")
        print(f"  Compliance Score: {result['compliance_score']}%")
        print(f"  Risk Level: {result['risk_level']}")
        print(f"  Gaps: {len(result['gaps'])} identified")
        print(f"  Deadlines: {result['deadlines_upcoming']} upcoming")
    else:
        print(f"✗ Assessment Failed: {result['error']}")
    
    return result

def list_all_agents():
    """Get agent registry."""
    response = requests.get(
        f"{BASE_URL}/agents/registry",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "X-Tenant-Id": TENANT_ID,
        }
    )
    
    data = response.json()
    print(f"✓ Agents Loaded: {data['total_agents']} total")
    print(f"  - Supervisor: {data['supervisor_agents']}")
    print(f"  - Domain: {data['domain_agents']}")
    print(f"  - Skill: {data['skill_agents']}")
    
    return data

# Run
if __name__ == "__main__":
    agents = list_all_agents()
    assessment = assess_entity("corp-123", "fintech")
    print(json.dumps(assessment, indent=2))
```

### JavaScript/TypeScript

```typescript
// Configuration
const BASE_URL = "http://localhost:8000/api/v1"
const TENANT_ID = "polkorp"

async function assessEntity(entityId: string, entityType = "company") {
  const token = localStorage.getItem("auth_token")
  
  const response = await fetch(`${BASE_URL}/agents/assess`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${token}`,
      "X-Tenant-Id": TENANT_ID,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      tenant_id: TENANT_ID,
      entity_id: entityId,
      entity_type: entityType,
      sectors: ["payments", "fintech"],
    }),
  })
  
  const result = await response.json()
  
  if (result.success) {
    console.log(`✓ Assessment Complete`)
    console.log(`  Compliance Score: ${result.compliance_score}%`)
    console.log(`  Risk Level: ${result.risk_level}`)
    console.log(`  Gaps: ${result.gaps.length}`)
    console.log(`  Deadlines: ${result.deadlines_upcoming}`)
  } else {
    console.error(`✗ Assessment Failed: ${result.error}`)
  }
  
  return result
}

async function listAgents() {
  const token = localStorage.getItem("auth_token")
  
  const response = await fetch(`${BASE_URL}/agents/registry`, {
    headers: {
      "Authorization": `Bearer ${token}`,
      "X-Tenant-Id": TENANT_ID,
    },
  })
  
  const data = await response.json()
  console.log(`✓ Agents: ${data.total_agents} (${data.supervisor_agents} supervisor, ${data.domain_agents} domain, ${data.skill_agents} skill)`)
  
  return data
}

// Run
(async () => {
  await listAgents()
  await assessEntity("corp-123", "fintech")
})()
```

### cURL

```bash
# 1. Login and get token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}' | jq -r '.access_token')

echo "Token: $TOKEN"

# 2. List agents
curl -s http://localhost:8000/api/v1/agents/registry \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-Id: polkorp" | jq

# 3. Run assessment
curl -s -X POST http://localhost:8000/api/v1/agents/assess \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-Id: polkorp" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "polkorp",
    "entity_id": "corp-123",
    "entity_type": "fintech"
  }' | jq

# 4. Extract compliance score
SCORE=$(curl -s -X POST http://localhost:8000/api/v1/agents/assess \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-Id: polkorp" \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "polkorp", "entity_id": "corp-123"}' | jq '.compliance_score')

echo "Compliance Score: $SCORE%"
```

---

## Error Handling

### HTTP Status Codes

| Code | Meaning | Response |
|------|---------|----------|
| 200 | Success | Assessment/data returned |
| 400 | Bad Request | Invalid JSON or required fields missing |
| 401 | Unauthorized | JWT expired or invalid; set Authorization header |
| 403 | Forbidden | User lacks permission (e.g., viewer cannot create assessments) |
| 422 | Validation Error | Field type mismatch (e.g., entity_id not a string) |
| 503 | Service Unavailable | Agent framework not initialized; try again in a moment |

### Example Error Response

```json
{
  "success": false,
  "error": "Entity 'corp-999' not found in tenant 'polkorp'"
}
```

---

## Rate Limiting

**Global Budget:** 40 requests per minute (NVIDIA provider)

**Priority Queue:**
- Interactive calls (priority 0): Assessed in real-time
- Bulk operations (priority 1): Queued after interactive calls

**Fallback Chain:**
1. NVIDIA (primary, 40 RPM)
2. Anthropic Claude (secondary, unlimited)
3. OpenRouter (tertiary, unlimited)

If rate limited, wait and retry with exponential backoff.

---

## Security & Multi-Tenancy

**Every request requires:**
1. Valid JWT token in `Authorization: Bearer` header
2. `X-Tenant-Id` header matching JWT's tenant_id claim

**All queries are automatically scoped to your tenant:**
- You cannot access other tenants' entities or assessments
- Audit logs are per-tenant
- Graph data (regulations, obligations) is tenant-isolated

**Token expiration:** 8 hours (configurable)

---

## Troubleshooting

**"Not authenticated"**
```
→ JWT token missing or expired
→ Solution: Get new token from /api/v1/auth/login
```

**"Agent framework not initialized"**
```
→ Backend still starting up
→ Solution: Wait 10 seconds and retry
```

**"Assessment took too long"**
```
→ Rate limit reached or provider timeout
→ Solution: Implement exponential backoff; check /agents/registry for agent health
```

**Cross-origin (CORS) error**
```
→ Frontend calling API from different domain
→ Solution: Ensure CORS_ORIGINS env var includes your frontend URL
```

---

## What's Next?

- Webhook notifications when assessments complete
- Batch assessment endpoint for multiple entities
- Real-time streaming results via Server-Sent Events (SSE)
- Agent memory (persistent state for regulators)
- Custom agent chains for specialized workflows
