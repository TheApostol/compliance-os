# ComplianceOS — Project Context for Claude Code

## What this is

AI-native Compliance Operating System for LATAM Regulated Industries.
Owner: Federico Carlos Polak (Polkorp Global Ventures).

Not a dashboard, not a KYC wrapper. **Regulatory infrastructure** that turns regulation into structured machine-readable obligations and orchestrates AI agents to monitor, audit, and act continuously.

## Stack

- **Backend**: FastAPI + Pydantic v2 + async SQLAlchemy + PostgreSQL
- **Frontend**: Next.js 14 (App Router) + Tailwind
- **Vector DB**: Qdrant
- **Cache**: Redis
- **AI**: NVIDIA NIM Free Endpoints (build.nvidia.com), 40 RPM rate limit
- **Container**: Docker Compose

## Modules

| ID | Name | Status | File |
|---|---|---|---|
| M1 | Regulatory Intelligence | ✅ | `backend/app/modules/regulatory/engine.py` |
| M2 | Compliance Copilot | ✅ | `backend/app/modules/copilot/copilot.py` |
| M3 | AML/KYC Orchestration | ✅ | `backend/app/modules/kyc_aml/engine.py` |
| M4 | Continuous Monitoring | ✅ | `backend/app/modules/monitoring/engine.py` |
| M5 | AI Governance | ✅ | `backend/app/modules/governance/engine.py` |
| M6 | Evidence Automation | 🚧 | `backend/app/modules/evidence/` (scaffolded only) |

## Validated AI models (benchmark 2026-05-11 with Federico's API key)

**USE these (verified working):**
- `nvidia/llama-3.3-nemotron-super-49b-v1` — Q=93.6 overall winner. Slow (33s avg) but most thorough. Best for: M1 parsing, M3 KYC, M4 monitoring.
- `meta/llama-3.3-70b-instruct` — Q=91.3 balanced. 21s avg. Best speed/quality tradeoff.
- `moonshotai/kimi-k2-instruct` — Q=91.2 fastest tier-1. 15.8s avg. Q=100 in M2 Copilot and M5 Governance. Multilingual ES/EN/ZH native.

**DEPRECATED — do not use:**
- `deepseek-ai/deepseek-v3.1` → EOL 2026-04-15, returns 410. Use `deepseek-ai/deepseek-v3.1-terminus` if needed.
- `mistralai/mistral-large-2-instruct` → 404 Not Found. Use `mistralai/mistral-large-3-675b-instruct-2512` if needed.

**Available but not yet benchmarked:**
- `minimaxai/minimax-m2` (230B MoE, reasoning + function calling)
- `nvidia/nemotron-3-nano-30b-a3b` (fast/cheap for high-volume)

## Working commands

```bash
make up          # docker compose up -d --build
make down        # docker compose down
make logs        # tail logs from all services
make restart     # restart all services
make ps          # show running containers
make clean       # WIPES all data + volumes
make seed        # load demo regulatory data
make benchmark   # test all modules with NVIDIA key
make test        # run pytest
make backend-shell
make db-shell    # psql into the database
```

## Coding standards

- **Python**: ruff + type hints + async-first. Target Python 3.11+.
- **Secrets**: NEVER in code. Use `.env` (already in `.gitignore`).
- **AI calls**: ALL must go through `app/services/ai_orchestrator.py`. Never call OpenAI/NVIDIA SDK directly from modules.
- **Audit**: Every compliance decision must be logged via `app/core/audit.py` (hash chain).
- **Multi-tenant**: every DB query filtered by `tenant_id`. Header: `X-Tenant-Id`.
- **JSON parsing**: Use the orchestrator's `_try_parse_json` — it handles ```json wrapping that some models add.
- **Timeouts**: AI calls timeout at 180s (nemotron can take 70s+).

## Architecture rules

1. The AI Orchestrator is the **only** point that talks to AI providers. This gives us routing, fallbacks, rate limiting, cost tracking, and audit in one place.
2. Every module receives an `AIOrchestrator` instance (DI). Don't instantiate inside modules.
3. The audit log is **INSERT-ONLY**. Hash chain enforced. Tamper-evident by design.
4. Tenant data residency policy (`tenant.data_residency_policy`) determines which AI providers are allowed. Honor it.

## Open tasks (priority order)

1. **Verify orchestrator v0.2 routing** — Run `make benchmark` and confirm all routes work with current model list.
2. **Build M6 Evidence module** — OCR with `nvidia/nemotron-ocr-v1` or alternative. Should extract structured data from regulator PDFs (UIF, BCRA, BACEN).
3. **Build Qdrant RAG layer** — Embed regulations on ingestion, retrieve top-K for Copilot context.
4. **Build regulatory crawler** — Start with BCRA + UIF Argentina. Cron job that fetches new regulations, parses with M1, stores in DB + Qdrant.
5. **Compliance graph** — Model regulations + obligations + entities + controls as a graph. Consider Postgres+AGE first (less ops overhead than Neo4j).
6. **Auth integration** — Replace `X-Tenant-Id` header with JWT (Auth0 or Clerk).

## Where to find things

- Config (with CORS fix): `backend/app/core/config.py`
- AI Orchestrator: `backend/app/services/ai_orchestrator.py` ← critical, read first
- Audit log: `backend/app/core/audit.py`
- DB models: `backend/app/db/models.py`
- API endpoints: `backend/app/api/v1/router.py`
- Frontend: `frontend/app/page.tsx`

## Style for outputs / commits

- Commit messages: conventional commits (`feat:`, `fix:`, `docs:`, etc.)
- Branches: `feat/M6-evidence`, `fix/orchestrator-timeout`, etc.
- PR descriptions: what + why + how to test.
