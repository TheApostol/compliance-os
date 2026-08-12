# Archived product direction — use ComplianceOS Copilot V2

> [!WARNING]
> This repository is a legacy prototype and is not the current source of truth. Do not continue product, research or AI-agent work here. Use the private canonical repository: [TheApostol/ComplianceOS-Copilot-V2](https://github.com/TheApostol/ComplianceOS-Copilot-V2).

# ComplianceOS

> AI-native Regulatory Intelligence & Compliance Operations Infrastructure for LATAM Regulated Industries.

ComplianceOS transforms regulations into:
- structured obligations
- operational workflows
- remediation pipelines
- evidence chains
- predictive regulatory intelligence
- graph-linked compliance operations
- AI-assisted governance automation

Built with:
- FastAPI
- Next.js 14
- PostgreSQL
- Redis
- Qdrant
- NVIDIA NIM
- Multi-tenant AI orchestration

---

# Platform Modules

| Module | Description | Status |
|---|---|---|
| M1 | Regulatory Intelligence | ✅ |
| M2 | Compliance Copilot | ✅ |
| M3 | AML / KYC | ✅ |
| M4 | Monitoring | ✅ |
| M5 | AI Governance | ✅ |
| M6 | Evidence Automation | ✅ |
| M7 | Workflow Orchestration & Remediation | 🚧 Beta |
| M8 | Predictive Regulatory Intelligence | 🚧 Beta |

---

# M7 — Workflow Orchestration & Remediation

M7 converts:
- regulations
- obligations
- AI outputs
- alerts
- evidence
- compliance risks

into executable workflows.

## Features

- remediation workflows
- approval chains
- escalation paths
- evidence collection
- workflow persistence
- audit-linked execution
- tenant-scoped operations
- downstream graph integration

## Endpoints

```text
POST /api/v1/workflow/remediation
```

---

# M8 — Predictive Regulatory Intelligence

M8 provides predictive regulatory analysis and jurisdiction intelligence.

## Features

- jurisdiction scoring
- AML strictness scoring
- regulatory velocity scoring
- market-entry simulation
- enforcement trend analysis
- expansion risk estimation

## Endpoints

```text
GET  /api/v1/predict/jurisdiction-risk
POST /api/v1/simulate/market-entry
```

---

# LATAM Regulatory Crawlers

ComplianceOS now includes a unified LATAM crawler engine capable of ingesting data from central banks and regulators across the region.

## Supported Regulators

| Country | Regulator |
|---|---|
| Argentina | BCRA |
| Brazil | BACEN |
| Chile | BCCh |
| Peru | BCRP |
| Mexico | Banxico |
| Colombia | SFC |

## Features

- async crawling
- retry handling
- tenant isolation
- AI obligation extraction
- evidence hashing
- graph integration hooks
- Qdrant RAG indexing hooks
- secure credential loading
- immutable audit-ready ingestion

## Crawler Endpoint

```text
POST /api/v1/crawler/latam/{regulator}
```

Example:

```text
POST /api/v1/crawler/latam/BCRA
```

---

# Current Architecture

```text
Frontend (Next.js 14)
        ↓
FastAPI API Gateway
        ↓
AI Orchestration Layer
        ↓
M1 → M8 Compliance Modules
        ↓
Workflow Engine + Predictive Engine
        ↓
PostgreSQL + Qdrant + Redis
        ↓
Graph + Evidence + Regulatory Crawlers
```

---

# Regulatory Coverage

## Jurisdictions

- Argentina
- Brazil
- Mexico
- Chile
- Colombia
- Peru
- Ecuador
- Uruguay

## Regulators

- BCRA
- UIF
- CNV
- BACEN
- CVM
- CMF
- SFC
- CNBV
- SBS Peru
- SBS Ecuador
- BCU

---

# AI Stack

## Models

- Llama 3.3
- Nemotron
- Kimi K2

## AI Capabilities

- regulatory parsing
- obligation extraction
- evidence extraction
- workflow remediation
- predictive scoring
- RAG retrieval
- graph contextualization

---

# Enterprise Features

- multi-tenant architecture
- JWT authentication
- API keys
- immutable audit logs
- RAG retrieval
- graph intelligence
- crawler scheduling
- SSE events
- observability
- Prometheus metrics
- webhook support
- workflow orchestration
- predictive intelligence

---

# Strategic Positioning

ComplianceOS is not a generic compliance dashboard.

It is:

> AI-native regulatory intelligence and compliance operations infrastructure for LATAM regulated industries.

---

# Roadmap

## In Progress

- workflow UI
- remediation dashboards
- graph explorer
- regulatory diff engine
- obligation engine
- predictive forecasting
- expansion simulator
- evidence pipelines
- automated sanctions ingestion

## Planned

- policy drafting AI
- enforcement prediction
- SOC2 readiness
- ServiceNow integration
- Jira integration
- Slack workflows
- advanced graph RAG
- regulatory timeline visualization

---

# License

Proprietary — Polkorp Global Ventures
