# ComplianceOS

> **AI-native Compliance Operating System for LATAM Regulated Industries**

The operating system for regulated companies in LATAM. Built on NVIDIA NIM, FastAPI, Next.js, PostgreSQL, and Qdrant. AI-orchestrated, modular, multi-tenant by design.

---

## What this is

Not a dashboard. Not another KYC wrapper. ComplianceOS is **regulatory infrastructure** that turns regulation into structured, machine-readable obligations and orchestrates AI agents to monitor, audit, and act on them continuously.

### Six core modules

| Module | Function | Status |
|---|---|---|
| **M1 — Regulatory Intelligence** | Crawls + parses BCRA, UIF, CNV, BACEN, CMF, SFC. Converts regulation into structured obligations. | ✅ Functional |
| **M2 — Compliance Copilot** | Multi-jurisdiction Q&A. Cross-border regulatory analysis. Policy generation. | ✅ Functional |
| **M3 — AML/KYC Orchestration** | Red flag detection, OFAC/sanctions screening, EDD workflows. | ✅ Functional |
| **M4 — Continuous Monitoring** | Transaction anomaly detection, policy drift detection, vendor risk. | ✅ Functional |
| **M5 — AI Governance** | Self-auditing agents, prompt injection detection, model registry, audit trails. | ✅ Functional |
| **M6 — Evidence Automation** | OCR of regulator PDFs, structured extraction, evidence chain of custody. | 🚧 Scaffolded |

---

## AI Stack (calibrated on real benchmark — May 2026)

| Use case | Primary | Fallback | Quality (real measured) |
|---|---|---|---|
| Regulatory parsing (M1) | `meta/llama-3.3-70b-instruct` | `nvidia/llama-3.3-nemotron-super-49b-v1` | Q=100, 21s |
| Compliance Copilot (M2) | `moonshotai/kimi-k2-instruct` | `meta/llama-3.3-70b-instruct` | Q=100, 30s |
| KYC/AML screening (M3) | `nvidia/llama-3.3-nemotron-super-49b-v1` | `meta/llama-3.3-70b-instruct` | Q=100, 26s |
| Transaction monitoring (M4) | `nvidia/llama-3.3-nemotron-super-49b-v1` | `meta/llama-3.3-70b-instruct` | Q=92, 24s |
| AI Self-audit (M5) | `moonshotai/kimi-k2-instruct` | `nvidia/llama-3.3-nemotron-super-49b-v1` | Q=100, 10s |

All endpoints free via [build.nvidia.com](https://build.nvidia.com). Rate limit: 40 RPM.

---

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│  Frontend (Next.js 14)                                     │
│  Dashboard / Copilot UI / Evidence Viewer                  │
└────────────────────────┬───────────────────────────────────┘
                         │ REST + SSE
┌────────────────────────▼───────────────────────────────────┐
│  API Gateway (FastAPI)                                     │
│  Auth / Multi-tenant / Rate limiting / Audit logging       │
└────────────────────────┬───────────────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────────────┐
│  AI Orchestration Layer                                    │
│  Model selection / Fallback chains / Cost caps / Caching   │
└─┬───────┬────────┬─────────┬─────────┬─────────┬───────────┘
  │       │        │         │         │         │
  ▼       ▼        ▼         ▼         ▼         ▼
┌────┐ ┌────┐ ┌──────┐ ┌──────────┐ ┌─────────┐ ┌─────┐
│ M1 │ │ M2 │ │  M3  │ │    M4    │ │   M5    │ │ M6  │
└────┘ └────┘ └──────┘ └──────────┘ └─────────┘ └─────┘
  │       │        │         │         │         │
  ▼       ▼        ▼         ▼         ▼         ▼
┌────────────────────────────────────────────────────────────┐
│  PostgreSQL (relational + immutable audit log)             │
│  Qdrant (vector DB for regulatory RAG)                     │
│  Redis (cache + rate limiting + job queue)                 │
└────────────────────────────────────────────────────────────┘
```

---

## Quickstart

### 1. Configure
```bash
cp .env.example .env
# Edit .env and add your NVIDIA_API_KEY (get one at https://build.nvidia.com)
# NEVER commit .env
```

### 2. Run
```bash
make up      # docker compose up -d --build
make logs    # follow logs
```

### 3. Open
- Frontend: http://localhost:3000
- API docs: http://localhost:8000/docs
- Qdrant UI: http://localhost:6333/dashboard

### 4. Validate AI
```bash
make benchmark   # tests all 6 modules with your NVIDIA key
```

---

## Repo structure

```
complianceos/
├── backend/
│   └── app/
│       ├── core/              # config, audit log, security
│       ├── services/          # AI orchestration (NIM router)
│       ├── modules/           # M1-M6 business logic
│       ├── api/v1/            # REST endpoints
│       └── db/                # SQLAlchemy models
├── frontend/                  # Next.js 14 (App Router)
├── infra/docker/              # Dockerfiles
├── docker-compose.yml
├── Makefile
├── CLAUDE.md                  # Context for Claude Code
└── .env.example
```

---

## Security & Compliance principles (eat your own dog food)

- **Secrets never in code or chat.** Use `.env` locally, Doppler/Infisical/Vault in prod.
- **Immutable audit log.** Every AI inference, every decision, every override is logged with hash chain.
- **PII never sent to AI providers** without explicit tenant config + tokenization.
- **Multi-tenant by default.** Row-level security on every query.
- **Data residency aware.** Tenant config decides which AI providers are allowed.

---

## Working with Claude Code

This repo has a `CLAUDE.md` at the root that gives Claude Code persistent context. Just run `claude` in this directory and it'll know:
- The full stack and architecture
- Which models work and which are deprecated
- All available `make` commands
- The current task priorities

---

## Roadmap

- [x] M1-M5 module scaffolding + functional code
- [x] AI orchestration with NVIDIA NIM (calibrated routing)
- [x] Multi-tenant data layer
- [x] Immutable audit log with hash chain
- [x] Frontend dashboard MVP
- [ ] M6 Evidence module (OCR + structured extraction)
- [ ] Regulatory crawler (AR/BR/MX/CL/CO)
- [ ] Qdrant RAG over regulations
- [ ] Compliance graph (Neo4j or Postgres + AGE)
- [ ] Auth0/JWT integration
- [ ] Self-hosted NIM containers (data residency)
- [ ] SOC2 Type II prep

---

## License

Proprietary — Polkorp Global Ventures
