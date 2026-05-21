# ComplianceOS — Project Context for Claude Code

## What this is

AI-native Compliance Operating System for LATAM Regulated Industries.
Owner: Federico Carlos Polak (Polkorp Global Ventures).

Not a dashboard, not a KYC wrapper. **Regulatory infrastructure** that turns regulation into structured machine-readable obligations and orchestrates AI agents to monitor, audit, and act continuously.

## Stack

- **Backend**: FastAPI + Pydantic v2 + async SQLAlchemy + PostgreSQL
- **Frontend**: Next.js 14 (App Router) + Tailwind + SWR
- **Vector DB**: Qdrant (collection: `regulations`, 1024-dim NV-Embed-v2)
- **Cache**: Redis
- **AI**: NVIDIA NIM Free Endpoints (build.nvidia.com), 40 RPM rate limit
- **Container**: Docker Compose (7-service stack)
- **Observability**: Prometheus (9090) + Grafana (3001)
- **Migrations**: Alembic (7 versioned migrations)

## Modules

| ID | Name | Status | File |
|---|---|---|---|
| M1 | Regulatory Intelligence | ✅ | `backend/app/modules/regulatory/engine.py` |
| M2 | Compliance Copilot | ✅ | `backend/app/modules/copilot/copilot.py` |
| M3 | AML/KYC Orchestration | ✅ | `backend/app/modules/kyc_aml/engine.py` |
| M4 | Continuous Monitoring | ✅ | `backend/app/modules/monitoring/engine.py` |
| M5 | AI Governance | ✅ | `backend/app/modules/governance/engine.py` |
| M6 | Evidence Automation | ✅ | `backend/app/modules/evidence/engine.py` |
| M7 | Compliance Scoring | ✅ | `backend/app/services/compliance_score.py` |
| M8 | Operational Intelligence | ✅ | `backend/app/api/v1/m7_m8_router.py` |
| — | LATAM Crawlers | ✅ | `backend/app/modules/crawler/` |
| — | Compliance Gap Analysis | ✅ | `backend/app/modules/compliance/gap_analysis.py` |
| — | Workflow Orchestration | ✅ | `backend/app/modules/workflows/engine.py` |
| — | Predictive Risk | ✅ | `backend/app/modules/predictive/engine.py` |

## Validated AI models (benchmark 2026-05-11)

**USE these (verified working):**
- `nvidia/llama-3.3-nemotron-super-49b-v1` — Q=93.6 overall winner. Slow (33s avg). Best for: M1 parsing, M3 KYC, M4 monitoring.
- `meta/llama-3.3-70b-instruct` — Q=91.3 balanced. 21s avg. Best speed/quality tradeoff.
- `moonshotai/kimi-k2-instruct` — Q=91.2 fastest tier-1. 15.8s avg. Q=100 in M2 Copilot and M5 Governance. Multilingual ES/EN/ZH native.

**DEPRECATED — do not use:**
- `deepseek-ai/deepseek-v3.1` → EOL 2026-04-15, returns 410. Use `deepseek-ai/deepseek-v3.1-terminus` if needed.
- `mistralai/mistral-large-2-instruct` → 404. Use `mistralai/mistral-large-3-675b-instruct-2512` if needed.

**Available but not yet benchmarked:**
- `minimaxai/minimax-m2` (230B MoE, reasoning + function calling)
- `nvidia/nemotron-3-nano-30b-a3b` (fast/cheap for high-volume)

## Working commands

```bash
make init             # Bootstrap .env from .env.example (first-time setup)
make up               # docker compose up -d --build
make down             # docker compose down
make logs             # tail logs from all services
make restart          # restart all services
make ps               # show running containers
make clean            # WIPES all data + volumes

make seed             # load demo regulatory data
make benchmark        # test all modules with NVIDIA key
make test             # run pytest (inside backend container)
make ci-test          # pytest -x -q --tb=short (CI mode)
make smoke-test       # trigger crawler + verify DB (requires running stack)

make migrate                  # apply all pending Alembic migrations
make makemigrations msg=<msg> # generate a new Alembic migration
make db-migrate-status        # show current Alembic revision

make backend-shell    # shell into backend container
make db-shell         # psql into the database
make prometheus       # open Prometheus UI (port 9090)
make grafana          # open Grafana UI (port 3001, admin/complianceos)
```

## First-time setup

```bash
make init          # creates .env from .env.example
# edit .env and set NVIDIA_API_KEY=nvapi-...
make up            # starts all 7 services
make migrate       # applies Alembic migrations
make seed          # loads demo data
```

## Coding standards

- **Python**: ruff + type hints + async-first. Target Python 3.11+.
- **Secrets**: NEVER in code. Use `.env` (already in `.gitignore`).
- **AI calls**: ALL must go through `app/services/ai_orchestrator.py`. Never call OpenAI/NVIDIA SDK directly from modules.
- **Audit**: Every compliance decision must be logged via `app/core/audit.py` (hash chain).
- **Multi-tenant**: every DB query filtered by `tenant_id`. Auth: `get_current_user` dependency injects `CurrentUser(tenant_id, role)`.
- **JSON parsing**: Use the orchestrator's `_try_parse_json` — it handles ```json wrapping that some models add.
- **Timeouts**: AI calls timeout at 180s (nemotron can take 70s+).
- **Logging**: structlog. Never use `print()`. Use `log = structlog.get_logger()`.
- **Request tracing**: `RequestIDMiddleware` injects `X-Request-ID` on every response.

## Architecture rules

1. The AI Orchestrator is the **only** point that talks to AI providers. This gives us routing, fallbacks, rate limiting, cost tracking, and audit in one place.
2. Every module receives an `AIOrchestrator` instance (DI). Don't instantiate inside modules.
3. The audit log is **INSERT-ONLY**. Hash chain enforced. Tamper-evident by design.
4. Tenant data residency policy (`tenant.data_residency_policy`) determines which AI providers are allowed. Honor it.
5. Auth: `get_current_user` FastAPI dependency returns `CurrentUser`. Dev fallback: `X-Tenant-Id` header allowed when `APP_ENV=development` and no JWT present.

## Where to find things

### Core
- Config + env vars: `backend/app/core/config.py`
- Auth (JWT HS256): `backend/app/core/auth.py` — `create_token`, `decode_token`, `get_current_user`
- Audit log (hash chain): `backend/app/core/audit.py`
- Logging config (structlog): `backend/app/core/logging.py`
- Error handlers: `backend/app/core/errors.py`

### Services
- **AI Orchestrator** ← read this first: `backend/app/services/ai_orchestrator.py`
- RAG (Qdrant): `backend/app/services/rag.py` — `embed_regulation()`, `retrieve(query, tenant_id, top_k=4)`
- Compliance Graph (Postgres+AGE): `backend/app/services/graph_service.py`
- Compliance Scoring (M7): `backend/app/services/compliance_score.py`
- Event bus (async pub/sub): `backend/app/services/event_bus.py`
- Webhook dispatch + retry: `backend/app/services/webhook_service.py`
- API key generation/validation: `backend/app/services/api_key_service.py`
- Export (CSV/JSON): `backend/app/services/export_service.py`

### Modules
- Crawler base (fetch, dedup, retry): `backend/app/modules/crawler/base_crawler.py`
- BCRA crawler (3 strategies + fallback): `backend/app/modules/crawler/bcra_crawler.py`
- UIF crawler: `backend/app/modules/crawler/uif_crawler.py`
- Other LATAM crawlers: `backend/app/modules/crawler/` (SBS Peru/Ecuador, CNBV Mexico, CMF Chile, BCU Uruguay, SFC Colombia)
- Crawler scheduler (APScheduler): `backend/app/modules/crawler/scheduler.py`
- Deadline alerts: `backend/app/modules/monitoring/deadline_checker.py`
- Workflow state machine: `backend/app/modules/workflows/engine.py`

### API
- Main router (all endpoints): `backend/app/api/v1/router.py`
- M7/M8 router: `backend/app/api/v1/m7_m8_router.py`

### DB
- All ORM models: `backend/app/db/models.py`
- Alembic migrations: `backend/alembic/versions/` (0001–0007)

### Frontend
- Single-page dashboard: `frontend/app/page.tsx`

### Middleware
- `backend/app/middleware/request_id.py` — X-Request-ID tracing
- `backend/app/middleware/metrics.py` — Prometheus metrics
- `backend/app/middleware/rate_limit.py` — token bucket rate limiting

## API endpoint map

| Group | Key endpoints |
|---|---|
| Health | `GET /api/v1/health`, `GET /api/v1/health/detailed` |
| Auth | `POST /auth/token`, `POST /auth/register` |
| M1 Regulatory | `POST /parse-regulation` |
| M2 Copilot | `POST /copilot/query` |
| M3 KYC/AML | `POST /kyc-screen`, `POST /sanctions-screen` |
| M4 Monitoring | `POST /monitor-transactions`, `POST /detect-drift` |
| M5 Governance | `POST /audit-ai-response`, `POST /check-injection` |
| M6 Evidence | `POST /evidence/extract`, `GET /evidence/documents`, `GET /evidence/documents/{id}` |
| M7/M8 | `GET /compliance/score`, `GET /governance/status` |
| Crawler | `POST /crawler/run-now`, `GET /crawler/status`, `GET /crawler/events` (SSE) |
| Graph | `GET /graph/stats`, `GET /graph/regulation/{id}/obligations`, `GET /graph/entity/{id}/obligations`, `POST /graph/query` (admin) |
| RAG | `GET /rag/status`, `POST /rag/reindex` |
| Alerts | `GET /alerts`, `POST /alerts/{id}/acknowledge` |
| Admin | Tenants, API keys, webhooks, audit logs |

## LATAM Crawlers

9 regulatory crawlers under `backend/app/modules/crawler/`:

| Regulator | Country | File | Schedule |
|---|---|---|---|
| BCRA | Argentina | `bcra_crawler.py` | 6h |
| UIF | Argentina | `uif_crawler.py` | 12h |
| SBS | Peru | `sbs_pe_crawler.py` | 12h |
| SBS | Ecuador | `sbs_ec_crawler.py` | 12h |
| CNBV | Mexico | `cnbv_crawler.py` | 12h |
| CMF | Chile | `cmf_crawler.py` | 12h |
| BCU | Uruguay | `bcu_crawler.py` | 12h |
| SFC | Colombia | `sfc_crawler.py` | 12h |

Crawlers use SHA-256 `source_hash` dedup — same document is never re-processed. Base crawler has exponential-backoff retry and `CrawlerResult` dataclass.

## Compliance Graph (Postgres + Apache AGE)

Graph vertices: `Regulation`, `Obligation`, `Entity` (company/person), `Control`, `Regulator`
Graph edges: `REQUIRES`, `APPLIES_TO`, `SATISFIES`, `ISSUED_BY`, `CROSS_REFERENCES`

Key methods in `graph_service.py`:
- `ensure_graph()` — idempotent graph creation
- `upsert_regulation(regulation)` — vertex + edges
- `upsert_obligation(obligation)` — vertex + REQUIRES edge
- `register_entity(entity)` — auto-generates APPLIES_TO edges
- `cypher_query(query_str)` — raw Cypher (admin-only endpoint)

## Auth

JWT HS256, claims: `sub` (user_id), `tenant_id`, `role` (admin|analyst|viewer), `exp`.

Dev fallback: if `APP_ENV=development` and JWT absent, `X-Tenant-Id` header is accepted (backwards compat for local testing).

RBAC guards: `POST /graph/query`, `POST /crawler/run-now` → admin only.

Future: swap to Auth0/Clerk JWKS via `AUTH_MODE=auth0|clerk` in `.env` without changing downstream code.

## Observability

- **Prometheus** scrapes `http://backend:8000/metrics` every 15s
- **Grafana** dashboard at port 3001 (auto-provisioned, admin/complianceos)
- Alert rules: `observability/alert.rules.yml`
- All API responses include `X-Request-ID` for log correlation

## Tests (22 files, 105+ tests)

```bash
make test          # run all tests
make ci-test       # -x -q --tb=short (for CI)
```

Key test files:
- `tests/test_orchestrator.py` — AI routing table + fallback chains
- `tests/test_auth.py`, `test_auth_jwks.py` — JWT + JWKS endpoint
- `tests/test_evidence.py` — M6 PDF extraction + custody hash
- `tests/test_crawlers.py` — base crawler dedup + retry (20 tests)
- `tests/test_crawlers_latam.py`, `test_crawlers_andean.py` — BCRA/UIF/CNBV/SBS parsing
- `tests/test_graph.py` — vertices, edges, Cypher queries
- `tests/test_rag.py` — vector embedding + retrieval
- `tests/test_compliance_score.py` — M7 scoring
- `tests/test_tenant_isolation.py` — multi-tenancy boundaries
- `tests/test_webhooks.py`, `test_api_keys.py`, `test_deadline_alerts.py`

`conftest.py` patches env vars before module imports and provides auth override fixtures.

## Style for outputs / commits

- Commit messages: conventional commits (`feat:`, `fix:`, `docs:`, etc.)
- Branches: `feat/M6-evidence`, `fix/orchestrator-timeout`, etc.
- PR descriptions: what + why + how to test.

## Workflow Orchestration

### 1. Plan Mode Default
- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately
- Write detailed specs upfront to reduce ambiguity

### 2. Subagent Strategy
- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One task per subagent for focused execution

### 3. Self-Improvement Loop
- After ANY correction from the user: update `tasks/lessons.md` with the pattern
- Write rules for yourself that prevent the same mistake
- Review lessons at session start for relevant project

### 4. Verification Before Done
- Never mark a task complete without proving it works
- Run tests, check logs, demonstrate correctness
- Ask yourself: "Would a staff engineer approve this?"

### 5. Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- Skip this for simple, obvious fixes — don't over-engineer

### 6. Autonomous Bug Fixing
- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests — then resolve them

## Task Management

1. Plan First: Write plan to `tasks/todo.md` with checkable items
2. Verify Plan: Check in before starting implementation
3. Track Progress: Mark items complete as you go
4. Explain Changes: High-level summary at each step
5. Document Results: Add review section to `tasks/todo.md`
6. Capture Lessons: Update `tasks/lessons.md` after corrections

## Core Principles

- Simplicity First: Make every change as simple as possible. Impact minimal code.
- No Laziness: Find root causes. No temporary fixes. Senior developer standards.
- Minimal Impact: Only touch what's necessary. No side effects with new bugs.

## Open tasks (Sprint 3)

1. **Alembic versioned migrations** — `ComplianceEntity`, `GraphVertex/Edge`, `User` tables currently rely on `create_all`. Generate proper versioned migration files.
2. **Frontend graph visualization** — Currently shows raw JSON. Implement subgraph visualization (D3 or similar).
3. **Frontend real-time crawler status** — Replace manual refresh with SSE polling of `GET /crawler/events`.
4. **BCRA/UIF live site smoke test** — Confirm HTML selectors match live site structure; adjust if needed.
5. **JWT refresh token** — `POST /auth/refresh` endpoint not yet implemented.
6. **Rate limiting middleware** — Token bucket exists in `middleware/rate_limit.py`; verify it's wired into all public endpoints.
