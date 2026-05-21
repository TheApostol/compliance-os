# CLAUDE.md — ComplianceOS v0.4.0

## Context persistence file for Claude Code

Read this file at the start of every session.
Update it when significant changes are made.

-----

## PROJECT IDENTITY

**Product:** ComplianceOS
**Positioning:** AI-native Regulatory Intelligence & Compliance Operations Infrastructure for LATAM regulated industries
**Owner:** Federico Carlos Polak — Polkorp Global Ventures — Buenos Aires, Argentina
**Stack:** FastAPI + Python 3.11 · Next.js 14 · PostgreSQL 16 · Qdrant · Redis · Prometheus + Grafana · Docker Compose · NVIDIA NIM (40 RPM free tier)
**Version:** 0.4.0
**Branch:** main (after sprint 5 merge)
**Repo root:** ~/dev/complianceos/

-----

## ARCHITECTURE OVERVIEW

```
complianceos/
├── backend/
│   ├── app/
│   │   ├── main.py                    ← FastAPI app, router mounting, startup hooks
│   │   ├── core/
│   │   │   ├── config.py              ← Settings, CORS (field_validator mode=before)
│   │   │   └── database.py            ← Async SQLAlchemy engine + session
│   │   ├── models/                    ← 13 SQLAlchemy models + Alembic migrations
│   │   ├── routers/                   ← 61 endpoints across 18 routers
│   │   ├── services/
│   │   │   └── ai_orchestrator.py     ← ALL AI calls go through here. Never bypass.
│   │   └── crawlers/                  ← 9 regulatory crawlers
│   ├── alembic/                       ← 8 migrations (0001 baseline → 0008 workflows)
│   ├── tests/                         ← 21 test files, ~146 tests
│   ├── scripts/
│   │   ├── seed_demo.py               ← Seeds Polkorp tenant + sample regulations
│   │   └── run_benchmark.py           ← Integrated benchmark all modules
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── page.tsx                   ← Landing redirect
│   │   └── dashboard/
│   │       ├── page.tsx               ← Main CCO dashboard (Sprint 5A)
│   │       └── components/            ← Dashboard components
│   └── (2893 lines total)
├── docker-compose.yml                  ← PostgreSQL:5433, Qdrant, Redis, Backend, Frontend, Prometheus, Grafana
├── Makefile                           ← make up/down/logs/seed/benchmark/test
└── CLAUDE.md                          ← This file
```

-----

## MODULE STATUS

|# |Module                 |Status          |Key capability                                                               |
|--|-----------------------|----------------|-----------------------------------------------------------------------------|
|M1|Regulatory Intelligence|✅ PRODUCTION    |PDF→obligations, country-aware AR/BR, RAG index, graph hooks, deadline alerts|
|M2|Compliance Copilot     |✅ PRODUCTION    |RAG-augmented QA (top-4 Qdrant chunks), multi-jurisdiction                   |
|M3|AML/KYC Orchestration  |✅ PRODUCTION    |Entity screening, sanctions, risk scoring Q=100                              |
|M4|Continuous Monitoring  |✅ PRODUCTION    |Transaction anomaly, policy drift, Prometheus 5-panel Grafana                |
|M5|AI Governance          |✅ PRODUCTION    |LLM-as-judge, prompt injection, INSERT-ONLY SHA-256 hash chain               |
|M6|Evidence Automation    |✅ PRODUCTION    |PDF→SHA-256→obligations→Qdrant, chain of custody                             |
|M7|Workflow Orchestration |✅ LIVE (beta UI)|Remediation pipelines, escalation, approval chain, audit-linked              |
|M8|Predictive Intelligence|✅ LIVE (beta UI)|Jurisdiction scoring, market-entry simulation, AI-powered with fallback      |

-----

## AI MODEL ROUTING — NVIDIA NIM (40 RPM limit)

**CRITICAL: ALL AI calls exclusively through `backend/app/services/ai_orchestrator.py`**
**NEVER import providers directly anywhere else.**

|Model key     |Full model ID                         |Best for                               |Avg latency|
|--------------|--------------------------------------|---------------------------------------|-----------|
|`kimi-k2`     |moonshotai/kimi-k2-instruct           |M2 Copilot RAG, M5 Governance, ES/EN/ZH|15s        |
|`llama-70b`   |meta/llama-3.3-70b-instruct           |M1 parsing, general fallback           |21s        |
|`nemotron-49b`|nvidia/llama-3.3-nemotron-super-49b-v1|M3 KYC, M4 monitoring, highest quality |33s        |

**DEPRECATED — do not use:**

- deepseek-ai/deepseek-v3.1 → 410 Gone (EOL 2026-04-15)
- mistralai/mistral-large-2-instruct → 404

**Benchmark results (2026-05-12, real data):**

- M1: Q=100, M2: Q=100, M3: Q=100, M4: Q=92, M5: Q=100
- Cost per full run: $0.000934
- Total latency: ~90s

-----

## DATABASE — 13 MODELS

### Alembic migrations:

- 0001: baseline (regulations, obligations, compliance_cases, ai_model_registry, evidence_documents)
- 0002: compliance_entities, graph_vertices, graph_edges, users (UserRole enum)
- 0003: tenants
- 0004: api_keys (csk_ prefix, SHA-256 hashed)
- 0005: deadline_alerts (AlertSeverity: critical/high/medium/low)
- 0006: webhook_configs (WebhookEvent enum, HMAC-signed delivery)
- 0007: regulations.full_text, source_url, source_hash
- 0008: workflows, workflow_steps (WorkflowStatus enum)
- 0009: tenants.vertical + vertical_regulators + vertical_obligation_types (Sprint 5B)

### Key model notes:

- Audit log: INSERT-ONLY, SHA-256 hash chain, tamper-evident
- API keys: csk_ prefix, stored as SHA-256 hash, never plaintext
- All tables: tenant-scoped via tenant_id FK

-----

## API ENDPOINTS — 61 TOTAL

|Group          |Endpoints                                                                                                                        |
|---------------|---------------------------------------------------------------------------------------------------------------------------------|
|Auth           |POST /auth/token, /auth/refresh, /auth/register                                                                                  |
|Regulatory     |POST /regulatory/parse                                                                                                           |
|Copilot        |POST /copilot/ask (RAG) · GET /copilot/canned-questions                                                                          |
|KYC            |POST /kyc/screen · GET /kyc/queue · POST /kyc/generate-rof                                                                       |
|Monitoring     |POST /monitoring/transactions, /monitoring/drift                                                                                 |
|Governance     |POST /governance/audit, /governance/injection                                                                                    |
|Evidence       |POST /evidence/extract · GET /evidence/documents{/id}                                                                            |
|RAG            |GET /rag/status · POST /rag/reindex                                                                                              |
|Graph          |GET /graph/stats, /graph/regulation/{id}/obligations · CRUD /graph/entities                                                      |
|Crawler        |GET /crawler/status · POST /crawler/run-now · GET /crawler/events (SSE)                                                          |
|Compliance     |GET /compliance/score/{id}, /compliance/score/{id}/history · POST /compliance/gap-analysis/{id}                                  |
|Alerts         |GET /alerts · POST /alerts/{id}/acknowledge, /alerts/run-check                                                                   |
|Audit          |GET /audit/entries, /audit/event-types                                                                                           |
|Search         |GET /search (Postgres ILIKE + Qdrant merged)                                                                                     |
|Export         |GET /export/obligations, /export/compliance-report, /export/evidence                                                             |
|Workflow (M7)  |POST /workflow/remediation · GET /workflow/{id} · POST /workflow/{id}/steps/{sid}/complete|approve · POST /workflow/{id}/escalate|
|Predictive (M8)|GET /predict/jurisdiction-risk · POST /simulate/market-entry                                                                     |
|LATAM Crawler  |POST /crawler/latam/{regulator}                                                                                                  |
|API Keys       |CRUD /api-keys                                                                                                                   |
|Webhooks       |CRUD /webhooks · POST /webhooks/{id}/test                                                                                        |
|Tenants        |CRUD /tenants (admin) · GET /tenant/{id}/vertical-config                                                                         |
|Health         |GET /health, /health/detailed                                                                                                    |

-----

## REGULATORY CRAWLERS — 9

|Crawler          |Regulator|Country|Schedule|Strategy                            |
|-----------------|---------|-------|--------|------------------------------------|
|bcra_crawler.py  |BCRA     |AR     |6h      |3-strategy + A7890–A7894 fallback   |
|uif_crawler.py   |UIF      |AR     |12h     |keyword + PDF detection             |
|bacen_crawler.py |BACEN    |BR     |8h      |3-strategy + Circ.3950–3954 fallback|
|cmf_crawler.py   |CMF      |CL     |12h     |3-strategy + fallback               |
|sfc_crawler.py   |SFC      |CO     |12h     |3-strategy + fallback               |
|cnbv_crawler.py  |CNBV     |MX     |12h     |3-strategy + fallback               |
|sbs_pe_crawler.py|SBS      |PE     |12h     |3-strategy + fallback               |
|sbs_ec_crawler.py|SBES     |EC     |24h     |3-strategy + fallback               |
|bcu_crawler.py   |BCU      |UY     |24h     |3-strategy + fallback               |

All crawlers: SHA-256 dedup · exponential backoff · tenant isolation · RAG + graph hooks.

On-demand: POST /crawler/latam/{regulator} covers all 9 + BCCh, BCRP, Banxico.

-----

## AUTHENTICATION & SECURITY

|Feature        |Implementation                                        |
|---------------|------------------------------------------------------|
|Local JWT      |HS256 · create_access_token() + create_refresh_token()|
|Auth0/Clerk    |RS256 JWKS with 1h key cache (JWKSValidator)          |
|Dev fallback   |X-Tenant-Id header allowed when app_env != production |
|API Keys       |csk_ prefix · SHA-256 hashed · expiry · last_used_at  |
|RBAC           |viewer / analyst / admin via require_admin dependency |
|Rate limiting  |slowapi on AI-heavy endpoints                         |
|Audit log      |INSERT-ONLY · SHA-256 hash chain · tamper-evident     |
|Request tracing|X-Request-ID + X-Response-Time-Ms headers             |

-----

## INFRASTRUCTURE

|Service   |Image               |Port     |Status              |
|----------|--------------------|---------|--------------------|
|PostgreSQL|postgres:16-alpine  |5433:5432|✅ Healthy           |
|Qdrant    |qdrant/qdrant:latest|6333     |✅ Healthy (1024-dim)|
|Redis     |redis:7-alpine      |6379     |✅ Healthy           |
|Backend   |FastAPI/Python 3.11 |8000     |✅ Healthy           |
|Frontend  |Next.js 14          |3000     |✅ Healthy           |
|Prometheus|prom/prometheus     |9090     |✅ Active            |
|Grafana   |grafana/grafana     |3001     |✅ Active (5 panels) |

**Port note:** PostgreSQL mapped to 5433 (not 5432) to avoid host conflicts.

-----

## OBSERVABILITY

- **Logs:** structlog — ConsoleRenderer (dev) / JSONRenderer (prod)
- **Metrics:** prometheus-fastapi-instrumentator → Prometheus → Grafana
- **Grafana panels (5):** req rate, latency p50/p95, in-progress, error rate, [crawl_success_rate — Sprint 5C]
- **Prometheus alerts (4):** HighErrorRate (>5%), SlowAIResponses (>30s), CrawlerNotRunning (>13h), HighInProgress (>20)
- **CI/CD:** GitHub Actions — parallel pytest -x -q + ruff lint

-----

## MULTI-VERTICAL SUPPORT (Sprint 5B)

### Verticals & accent colors:

|Vertical       |Accent |Key regulators            |
|---------------|-------|--------------------------|
|FINTECH        |#4A9FD4|BCRA, UIF, CNV, BACEN     |
|CRYPTO_VASP    |#FFE135|BCRA A8094, UIF, CNV, FATF|
|INSURANCE      |#10B981|SSN, SUSEP, CNSF          |
|HEALTH_PHARMA  |#EF4444|ANMAT, ANVISA, COFEPRIS   |
|GAMING         |#8B5CF6|LOTBA, SEGOB, COLJUEGOS   |
|CAPITAL_MARKETS|#F59E0B|CNV, CVM, CMF             |
|TELECOM        |#06B6D4|ENACOM, ANATEL, IFT       |

### Tenant config endpoint:

GET /tenant/{id}/vertical-config → { vertical, regulators[], canned_questions[], accent_color }

-----

## KNOWN GAPS — SPRINT 5 BACKLOG

### HIGH PRIORITY:

- [ ] M7 frontend panel (workflow UI, step list, approve/escalate) → Sprint 5A
- [ ] M8 frontend panel (jurisdiction heatmap, simulation form) → Sprint 5A
- [ ] Unified CCO dashboard — Lemon Cash → Sprint 5A
- [ ] GET /kyc/queue endpoint → Sprint 5A
- [ ] POST /kyc/generate-rof endpoint → Sprint 5A
- [ ] GET /compliance/score/{id}/history (6 months) → Sprint 5A
- [ ] GET /copilot/canned-questions?vertical=X → Sprint 5A

### MEDIUM:

- [ ] POST /auth/refresh not wired in router → Sprint 5C
- [ ] Alert → Workflow auto-trigger (critical alert → auto-create M7 workflow) → Sprint 5C
- [ ] M8 fallback: return cached result when NVIDIA NIM rate limited → Sprint 5B

### LOW:

- [ ] Alembic full history (0001 is no-op baseline)
- [ ] BCRA/UIF live smoke test (HTML selectors need validation)
- [ ] Graph APPLIES_TO auto-gen
- [ ] Grafana 6th panel: crawl_success_rate

-----

## CRITICAL RULES

1. **ALL AI calls through ai_orchestrator.py** — never direct provider imports
1. **Never use deprecated models** — deepseek-v3.1 and mistral-large-2 return errors
1. **Audit log is INSERT-ONLY** — never UPDATE or DELETE audit entries
1. **Tenant isolation** — every query must filter by tenant_id
1. **CORS fix** — config.py uses field_validator with mode="before" for flexible parsing
1. **Port 5432 is mapped to 5433** — use 5433 for external connections
1. **API keys stored as SHA-256 hash** — never store or log plaintext keys
1. **pydantic-settings** installed separately from pydantic

-----

## MAKE COMMANDS

```bash
make up          # Start all services
make down        # Stop all services  
make logs        # Follow all logs
make seed        # Seed Polkorp demo tenant
make benchmark   # Run integrated benchmark (needs NVIDIA_API_KEY in .env)
make test        # Run pytest
make backend-shell  # Shell into backend container
make db-shell    # psql into PostgreSQL
```

-----

## ENV VARIABLES (in .env, never commit)

```
NVIDIA_API_KEY=nvapi-...         # NVIDIA NIM
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://localhost:6379
QDRANT_URL=http://localhost:6333
SECRET_KEY=...                   # JWT signing
AUTH0_DOMAIN=...                 # Optional
CLERK_JWKS_URL=...               # Optional
APP_ENV=development              # or production
```

-----

## SPRINT HISTORY

|Sprint|Version|Key deliverables                                    |
|------|-------|----------------------------------------------------|
|1     |v0.1   |M1-M5 core, basic FastAPI, Docker setup             |
|2     |v0.2   |M6 evidence, AI orchestrator, NVIDIA NIM benchmark  |
|3     |v0.2.1 |M7/M8 backend, 9 crawlers, auth hardening, 146 tests|
|4     |v0.3.0 |RAG improvements, Grafana, CI/CD, multi-tenant      |
|5A    |v0.4.0 |Lemon Cash dashboard, KYC queue, RoF generation     |
|5B    |v0.4.1 |Multi-vertical architecture, 6 industry packs       |
|5C    |v0.4.2 |Auth refresh, alert→workflow trigger, minor fixes   |

-----

*Last updated: 2026-05-21 — Federico Carlos Polak / Polkorp Global Ventures*
*Next session: read this file, check `git log --oneline -10`, run `make benchmark`*
