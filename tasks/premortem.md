# ComplianceOS Premortem Exercise
## Project Failure Mode Analysis & Mitigation Roadmap

**Created:** 2026-06-23 | **Timeline:** 13 weeks (to 2026-08-06) | **Owner:** Federico Carlos Polak

---

## Executive Summary

ComplianceOS is an ambitious AI-native regulatory compliance platform for 9 LATAM countries. Through a structured premortem exercise, we've identified **18 high-impact failure modes** and designed testable mitigations prioritized by regulatory impact and operational criticality.

**Current Risk Score:** 59/100 → 55/100 → 51/100 → **47/100** (recalculated 2026-06-24, see Review & Updates) → **Target:** 11/100 (by 2026-08-06)

---

## Part 1: Failure Mode Inventory (18 Risks)

### TIER 1: CRITICAL (Regulatory Exposure + Revenue Risk)

| ID | Scenario | Category | Severity | Status | Impact |
|---|---|---|---|---|---|
| **F1** | NVIDIA NIM outage → Complete service blackout | AI Reliability | 🔴 CRITICAL | MITIGATED (70%) | All M1/M3/M4/M5/M6 parsing stops; 429/503 errors; audit trail incomplete — 3-tier fallback (NVIDIA→Anthropic→OpenRouter) shipped 2026-06-23, T1.2 rate limiting + T1.6 circuit breaker still open |
| **F2** | Multi-tenant data isolation breach (Tenant A sees B's regulations) | Data Isolation | 🔴 CRITICAL | MITIGATED (90%) | Confidentiality breach; competitor access; regulatory violation — T0.1 (89 tenant_id-filtered queries verified), T0.2 (per-tenant Qdrant collections), T0.3 (JWT) all shipped; remaining 10%: T5.3 security audit |
| **F3** | Audit chain tampering or hash corruption | Audit | 🔴 CRITICAL | MITIGATED (70%) | Audit log loses tamper-evidence; BCRA/UIF cannot trust compliance decisions — T0.4 (`complianceos_audit_logger` INSERT-ONLY role + trigger) shipped; remaining: external timestamp authority |
| **F4** | Regulatory crawler HTML parser breaks (BCRA/UIF redesign) | Crawler | 🟠 HIGH | MITIGATED (40%) | Regulations stale (days→weeks); outdated compliance decisions — T0.5 (zero-doc Prometheus alert + webhook) shipped; multi-strategy parsing (T2.3) still open |
| **F5** | NVIDIA rate limit exhaustion (40 RPM @ peak load) | AI Reliability | 🔴 CRITICAL | IDENTIFIED | KYC/AML screening delayed; false negatives; SLA violations |
| **F8** | Data residency policy violation (route to Singapore despite "latam" config) | Compliance | 🔴 CRITICAL | IDENTIFIED | GDPR/LGPD/PDPA fines; regulatory enforcement; loss of trust |

### TIER 2: HIGH (Operational Instability + Data Integrity)

| ID | Scenario | Category | Status | Mitigation ETA |
|---|---|---|---|---|
| **F6** | Qdrant connection pool exhausted | Infrastructure | RESOLVED | 2026-06-25 |
| **F7** | PostgreSQL connection pool exhausted | Infrastructure | MITIGATED (80%) | 2026-07-01 |
| **F9** | Workflow engine deadlock (circular approval chains) | Workflows | ✅ RESOLVED | 2026-06-23 (done) |
| **F10** | Evidence custody chain broken (JSONB hash mutation) | Evidence | IDENTIFIED | 2026-07-22 |
| **F11** | RAG embedding model deprecated mid-year | AI Reliability | IDENTIFIED | 2026-07-29 |
| **F12** | Compliance case race condition (concurrent UPDATE) | Data Integrity | IDENTIFIED | 2026-07-08 |
| **F13** | Monitoring deadline checker misses cutoffs (timezone) | Monitoring | IDENTIFIED | 2026-07-08 |
| **F14** | Crawler scheduler silent failure (exception not retried) | Crawler | IDENTIFIED | 2026-07-15 |
| **F15** | LLM output parsing fails silently (JSON truncation) | AI Reliability | IDENTIFIED | 2026-07-01 |
| **F16** | Frontend request hangs (timeout not propagated) | Infrastructure | IDENTIFIED | 2026-07-22 |
| **F17** | BCRA/UIF auth token expires during crawl | Crawler | IDENTIFIED | 2026-07-15 |
| **F18** | Graph vertex insert exceeds transaction timeout | Data Integrity | IDENTIFIED | 2026-07-29 |

---

## Part 2: Implementation Roadmap (5 Phases)

### Phase 0: Foundation (W1-2) — Data Isolation + Audit
**Goal:** Fix blocking data isolation bugs; establish monitoring. **Status:** ✅ DONE (all 5 tasks shipped 2026-06-24)

- [x] **T0.1** Tenant ID audit (21 queries) — Add `tenant_id` filter to all DB queries | 3d | Backend | ✓ DONE — verified 89 `tenant_id`-filtered query sites in `app/api/v1/router.py` (originally undercounted as 21); zero unfiltered queries found
- [x] **T0.2** Qdrant tenant namespacing — Use `regulations_{tenant_id}` collections | 2d | Backend | ✓ DONE — `app/services/rag.py`: `_collection_name()` routes to per-tenant collections (`regulations_{tenant_id}`, `regulations_global` for tenant-less crawler data), `retrieve()` federates tenant + global, `index_all_regulations` fixed to use each row's real `tenant_id`, `migrate_legacy_collection()` added to backfill the old single `regulations` collection (exposed via `POST /rag/migrate-legacy-collection`)
- [x] **T0.3** JWT middleware enforcement — Replace `X-Tenant-Id` header with signed JWT | 3d | Backend | ✓ DONE (`app/core/auth.py` — local HS256 + Auth0/Clerk RS256 via JWKS; `X-Tenant-Id` header remains only as documented dev-mode fallback when `APP_ENV != production`)
- [x] **T0.4** Audit log DB role enforcement — Create `complianceos_audit_logger` role; INSERT-ONLY | 1d | Backend | ✓ DONE — Alembic migration `0010_audit_log_insert_only.py`: `prevent_audit_log_mutation()` trigger + `trg_audit_log_insert_only` + `complianceos_audit_logger` role (SELECT+INSERT only)
- [x] **T0.5** Monitoring: crawler success rate — Alert if crawler returns 0 docs | 2d | Ops | ✓ DONE — `app/services/event_bus.py`: `publish()` detects `crawled == 0` on `crawler:{tenant_id}` channels, increments `crawler_zero_doc_total` Prometheus counter, logs a structured warning, and tags the event `alert: "zero_doc"` before SSE/webhook dispatch

**Verification:**
- Tenant isolation test suite passes (F2 coverage: 90%)
- Audit chain verification detects tampering (F3 coverage: 70%)
- All 89 tenant_id-filtered query sites verified (originally tracked as 21 — undercounted)

**Target Completion:** 2026-07-01

---

### Phase 1: Resilience (W3-5) — Provider Failover + Rate Limiting
**Goal:** Handle provider failures; protect rate limits; ensure deadlines work. **Status:** 🟡 IN PROGRESS (T1.1 done)

- [x] **T1.1** Fallback routing (3-tier: NVIDIA → Anthropic → OpenRouter) | 3d | Backend | ✓ DONE — `app/services/ai_orchestrator.py`: every `ROUTING` chain now carries a `claude-sonnet-4-6` → `openrouter-llama-3.3-70b` tail; `_call_model` dispatches per `ModelSpec.provider`; `infer()` skips unconfigured providers in the chain instead of hard-failing when NVIDIA alone is down. Resolves F1.
- [ ] **T1.2** Token bucket rate limiter (40 RPM global budget, priority queue) | 4d | Backend | Depends: T1.1
- [ ] **T1.3** Data residency enforcement (check `tenant.data_residency_policy` at inference) | 2d | Backend | Depends: T1.1
- [ ] **T1.4** Timezone & deadline checker rewrite (convert deadline to tenant TZ) | 3d | Backend | Depends: -
- [ ] **T1.5** Connection pool tuning (PostgreSQL: 20+10, Qdrant: configured) | 2d | Backend | Depends: -
- [ ] **T1.6** Circuit breaker for AI (open after 5 errors, auto-close after improvement) | 2d | Backend | Depends: T1.1

**Verification:**
- Simulate NVIDIA outage; fallback to Anthropic succeeds (F1 coverage: 100%)
- Rate limit: 50 concurrent requests queued, depth ~35 (F5 coverage: 100%)
- Deadline: obligation due tomorrow escalates correctly (F13 coverage: 100%)

**Target Completion:** 2026-07-22

---

### Phase 2: Integrity & Observability (W6-7) — Parsing + Evidence + Crawler
**Goal:** Fix parsing robustness; add evidence chain auditing; crawler monitoring. **Status:** 🔴 NOT STARTED

- [ ] **T2.1** LLM output parsing robustness (_try_parse_json raises, not returns {}) | 3d | Backend | Depends: -
- [ ] **T2.2** Evidence custody chain audit (canonical_json, audit table) | 4d | Backend | Depends: -
- [ ] **T2.3** Crawler multi-strategy + token refresh (CSS + keyword + date fallback) | 4d | Backend | Depends: -
- [ ] **T2.4** APScheduler resilience (misfire_grace_time, immediate re-queue, heartbeat) | 2d | Backend | Depends: T2.3
- [ ] **T2.5** Request timeout handling (frontend per-endpoint, AbortController, server-side cancel) | 4d | Frontend + Backend | Depends: -

**Verification:**
- Truncated JSON: parser raises error (F15 coverage: 100%)
- Evidence upload: custody_hash immutable (F10 coverage: 100%)
- Crawler fails at doc 10/20: recovers and completes all 20 (F4 coverage: 100%)

**Target Completion:** 2026-08-06

---

### Phase 3: State Machines & Data Quality (W8-9)
**Goal:** Fix workflow/case state transitions; embed model versioning. **Status:** 🟡 IN PROGRESS (T3.1, T3.2 done)

- [x] **T3.1** Workflow DAG validation (cycle detection with DFS) | 2d | Backend | ✓ DONE — `_validate_dag()` in `app/modules/workflows/engine.py`, resolves F9
- [x] **T3.2** Workflow step timeout + escalation (7d default, auto-escalate if exceeded) | 2d | Backend | ✓ DONE — `check_step_timeouts()`, `DEFAULT_STEP_TIMEOUT_DAYS = 7`, resolves F9
- [ ] **T3.3** Compliance case optimistic locking (version column, StaleObjectError) | 2d | Backend
- [ ] **T3.4** Embedding model versioning + migration plan (dual-write, 1w cutover) | 3d | Backend

**Target Completion:** 2026-08-20

---

### Phase 4: Frontend Dashboard & Integration Tests (W10-11)
**Goal:** Build premortem dashboard; add comprehensive integration tests. **Status:** 🟢 STARTED

- [x] **T4.1** Premortem dashboard (index2.html) — Real-time risk inventory UI | 4d | Frontend | ✓ DONE
- [x] **T4.2** Premortem API endpoints — /premortem/* routes | 2d | Backend | ✓ DONE
- [ ] **T4.3** Premortem data aggregation (risk scores, health calculation) | 3d | Backend | Depends: T0-T3
- [ ] **T4.4** Integration test suite (F1-F18 failure scenarios) | 5d | QA | Depends: T0-T3

**Target Completion:** 2026-08-27

---

### Phase 5: Hardening & Rollout (W12-13)
**Goal:** Load testing; compliance audit; production rollout. **Status:** 🔴 NOT STARTED

- [ ] **T5.1** Load test (100 concurrent users, 40 RPM limit, zero errors) | 3d | QA
- [ ] **T5.2** Chaos engineering (5 random failures injected, recovery < 5min) | 3d | QA
- [ ] **T5.3** Security audit (JWT, tenant isolation, audit log) | 3d | Security
- [ ] **T5.4** Compliance readiness (UIF/BACRA/BCRA checklist, legal sign-off) | 2d | Legal
- [ ] **T5.5** Rollout: canary 10% → 50% → 100% | 3d | Ops

**Target Completion:** 2026-09-10

---

## Part 3: Critical Files for Implementation

### Phase 0 Files (Priority 1)
- `backend/app/api/v1/router.py` — Tenant ID audit + JWT enforcement
- `backend/app/services/ai_orchestrator.py` — Routing logic
- `backend/app/core/auth.py` — JWT generation/validation
- `backend/app/core/audit.py` — Hash chain, DB role enforcement
- `backend/app/db/models.py` — Add timezone to Tenant, version to Case

### Phase 1 Files (Priority 2)
- `backend/app/middleware/rate_limit.py` — Token bucket
- `backend/app/db/base.py` — Connection pool tuning
- `backend/app/modules/monitoring/deadline_checker.py` — Timezone-aware logic
- `backend/app/modules/crawler/base_crawler.py` — Token refresh, retry
- `backend/app/modules/crawler/scheduler.py` — APScheduler resilience

### Phase 2-4 Files (Priority 3)
- `backend/app/modules/evidence/engine.py` — Custody hash canonicalization
- `backend/app/services/rag.py` — Qdrant tenant namespacing
- `backend/app/modules/workflows/engine.py` — DAG validation, state machine
- `backend/app/api/v1/premortem_router.py` — Premortem endpoints ✓
- `frontend/public/index2.html` — Dashboard ✓

### New Files to Create
- `backend/app/services/premortem.py` — Risk scoring + aggregation
- `tests/test_premortem_scenarios.py` — F1-F18 integration tests

### Shipped Today (2026-06-23) — Beyond the Original 18 Risks
- `backend/app/modules/workflows/engine.py` — Real DAG state machine, resolves F9 (see T3.1/T3.2)
- `backend/app/modules/predictive/engine.py` — M8 predictive risk now grounded in real DB
  aggregates (regulation/obligation counts) instead of hardcoded dicts; no F-number assigned
  but directly addresses the "fake data" trust gap flagged in the M7/M8 review
- `backend/app/modules/transactions/engine.py`, `app/api/v1/transactions_router.py` — New M10
  Transaction Monitoring module: deterministic AML rule engine (CTR/structuring/velocity/geography)
  blended with AI typology analysis, audit-logged per screening
- `tasks/ai_os_architecture.md` — Kernel-vs-vertical architecture assessment; identifies that M3
  (KYC) and M4 (Monitoring) have **no deterministic fallback** if AI fails, unlike the new M10
  pattern — flagged as a reliability gap adjacent to F1/F5/F15, not yet fixed

---

## Part 4: Go-Live Criteria (All Required for Production)

- [ ] **Data Isolation:** Zero tenant isolation bugs (F2 = 100% done)
- [ ] **Audit Trail:** Chain verified + external timestamp authority live (F3 = 100%)
- [ ] **Provider Resilience:** Fallback routing tested + rate limiting under load (F1, F5 = 100%)
- [ ] **Crawler Robustness:** Multi-strategy parsing tested (F4 = 100%)
- [ ] **Phase 0 Tests:** All passing (T0.1-T0.5)
- [ ] **Chaos Test:** < 5 min recovery from random failures
- [ ] **Security Audit:** Zero findings on tenant isolation, JWT, audit chain
- [ ] **Compliance Checklist:** Signed off by Legal (UIF, BCRA, BACEN requirements)

---

## Ruthless Prioritization Matrix

| Phase | Timeline | Must-Ship | Can-Defer |
|---|---|---|---|
| 0 | W1-2 | T0.1, T0.3, T0.4 | T0.2, T0.5 |
| 1 | W3-5 | T1.1, T1.2, T1.4 | T1.3, T1.6 |
| 2 | W6-7 | T2.1, T2.3 | T2.2, T2.5 |
| 3 | W8-9 | T3.1, T3.3 | T3.2, T3.4 |
| 4 | W10-11 | T4.4 (tests) | T4.1, T4.3 (dashboard) |
| 5 | W12-13 | T5.2, T5.3, T5.5 | T5.1, T5.4 |

**Rationale:** Focus on data isolation + audit integrity first (regulatory blocking issues). Then resilience + rate limiting (operational stability). Dashboard and advanced features follow.

---

## Review & Updates

- **2026-06-23 (AM):** Premortem exercise completed. 18 failure modes identified, mitigations planned, 5-phase roadmap drafted.
- **2026-06-23 (PM):** M7 (workflow engine) rebuilt as a real DAG-validated, dependency/approval-gated
  state machine with timeout escalation — **F9 moved IDENTIFIED → RESOLVED**, T3.1/T3.2 done.
  M8 (predictive risk) rebuilt to ground AI output in real DB aggregates instead of hardcoded
  data. New M10 module (Transaction Monitoring/AML) shipped. Audit found T0.3 (JWT) was already
  implemented in `app/core/auth.py` and is corrected from NOT STARTED → DONE. Risk score
  recalculated: **59 → 55/100** (Operational Stability 64→56 from F9 resolution; Regulatory
  Compliance 72→68 from the JWT correction; Service Availability and Data Integrity unchanged —
  F1/F2/F3/F5/F8/F10/F12/F18 are untouched and remain the path to 11/100). See
  `tasks/ai_os_architecture.md` for the architectural framing behind today's M7/M8/M10 work and
  a newly-flagged gap (M3/M4 have no deterministic fallback if AI fails, unlike M10).
- **2026-06-23 (PM, cont'd):** T1.1 (provider fallback routing) shipped — `ai_orchestrator.py` now has a
  3-tier chain (NVIDIA → Anthropic `claude-sonnet-4-6` → OpenRouter `llama-3.3-70b`) appended to every
  `ROUTING` entry. `infer()` no longer hard-fails when NVIDIA alone is down; it skips unconfigured
  providers in the chain and only fails if zero providers are configured at all. Added
  `has_anthropic`/`has_openrouter` to `Settings` (`app/core/config.py`) and `anthropic>=0.40.0` to
  `requirements.txt`. **F1 moved IDENTIFIED → MITIGATED (70%)** — not yet 100% because T1.2 (rate
  limiting) and T1.6 (circuit breaker) are still open, and the new fallback path is untested against a
  live NVIDIA outage (no integration test yet — tracked under T4.4). Risk score recalculated:
  **55 → 51/100** (Service Availability 42→55 from the fallback path; other dimensions unchanged).
- **2026-06-24:** Phase 0 completed — all 5 tasks (T0.1-T0.5) now done. Investigation found T0.1
  (89 tenant_id-filtered query sites, not 21 as previously tracked) and T0.4 (Postgres
  `complianceos_audit_logger` INSERT-ONLY role, migration `0010`) had already shipped prior to
  this review but were marked NOT STARTED — corrected to DONE. T0.2 (Qdrant per-tenant collection
  namespacing — `_collection_name()`, federated tenant+global retrieval, `migrate_legacy_collection()`
  in `app/services/rag.py`) and T0.5 (crawler zero-doc Prometheus counter + structured log +
  webhook alert tag in `app/services/event_bus.py`) shipped today. Also confirmed M6 (Evidence
  Automation) and the Qdrant RAG layer for M2 Copilot — both listed elsewhere as open/scaffolded —
  are fully implemented already (`app/modules/evidence/engine.py`, `app/services/rag.py` +
  `app/modules/copilot/copilot.py` integration); README.md/CLAUDE.md's "Open tasks" list is stale
  on these two items. **F2 moved MITIGATED (60%) → MITIGATED (90%)**, **F3 IDENTIFIED → MITIGATED
  (70%)**, **F4 MONITORING → MITIGATED (40%)**. Risk score recalculated: **51 → 47/100** (Data
  Integrity 58→38 from the Phase 0 isolation/audit work; other dimensions unchanged).
- **Next Review:** 2026-07-01 (Phase 1 checkpoint)

---

## References

- Premortem data: `/backend/seeds/premortem_seed.py`
- Dashboard: `/frontend/public/index2.html`
- API endpoints: `/backend/app/api/v1/premortem_router.py`
- Models: `/backend/app/db/models.py` (Premortem* tables)
- Engine: `/backend/app/modules/premortem/engine.py`
- AI OS architecture (kernel vs. vertical): `/tasks/ai_os_architecture.md`
