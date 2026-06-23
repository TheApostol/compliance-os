# ComplianceOS — Full Roadmap

_Written: 2026-05-14. Branch: `claude/workflow-orchestration-system-1Hx7Y`_

---

## T1 · Verify Orchestrator v0.2 Routing

**Goal:** Confirm every model in ROUTING is live and the fallback chains behave correctly.

- [ ] Code-review `ai_orchestrator.py` ROUTING table against CLAUDE.md validated model list
- [ ] Check deprecated model IDs are not in any active chain
- [ ] Run `make benchmark` (requires Docker + NVIDIA key)
- [ ] Confirm all 8 TaskTypes return success responses
- [ ] Fix any dead routes found

**Files:** `backend/app/services/ai_orchestrator.py`

---

## T2 · Complete M6 Evidence Module

**Goal:** PDF → structured obligations → chain-of-custody → DB. API already wired.

### What exists
- `engine.py` (full pipeline: PyMuPDF → LLM → SHA-256 custody hash → DB persist)
- API endpoints: `POST /evidence/extract`, `GET /evidence/documents`, `GET /evidence/documents/{id}`
- DB model: `EvidenceDocument` in `models.py`

### What's missing
- [ ] Verify Alembic migration includes `evidence_documents` table
- [ ] Add embedding step: after LLM extraction, embed full text into Qdrant `evidence` collection
- [ ] Add `matched_obligations` cross-reference logic (compare extracted obligations vs DB obligations)
- [ ] Integration test: upload a real regulator PDF, verify structured output + custody hash
- [ ] Error handling for scanned-only PDFs (char_count < 50 → fallback message)
- [ ] Expose extraction confidence in GET /evidence/documents response

**Files:** `backend/app/modules/evidence/engine.py`, `backend/app/api/v1/router.py`, `backend/app/db/models.py`

---

## T3 · Qdrant RAG Layer

**Goal:** Embed regulations on ingestion; retrieve top-K chunks for Copilot context.

### Architecture
- Qdrant collection: `regulations` (vector size 1024 — NV-Embed-v2 or text-embedding-3-small)
- Embedding triggered when: (a) M1 parses a regulation, (b) M6 extracts a PDF
- Retrieval: top-4 chunks injected into Copilot system prompt

### Tasks
- [ ] Create `backend/app/services/rag_service.py`
  - `embed_regulation(regulation_id, text, metadata)` → upsert into Qdrant
  - `retrieve(query, tenant_id, top_k=4)` → returns list of chunk dicts
  - `ensure_collection()` → idempotent collection creation
- [ ] Choose embedding model: use NVIDIA NIM `/v1/embeddings` endpoint (nvidia/nv-embed-v2)
  - Add `EMBEDDINGS_MODEL` to config + orchestrator
- [ ] Wire embedding into M1 after successful parse (post-persist hook)
- [ ] Wire embedding into M6 after successful extraction
- [ ] Fix Copilot RAG retrieval (currently stub/best-effort) to use `rag_service.retrieve()`
- [ ] Add `GET /rag/status` endpoint: collection info + document count
- [ ] Test: parse a regulation → verify it appears in Qdrant → copilot returns it as context

**Files:** `backend/app/services/rag_service.py` (new), `backend/app/modules/regulatory/engine.py`, `backend/app/modules/copilot/copilot.py`, `backend/app/api/v1/router.py`

---

## T4 · Regulatory Crawler (BCRA + UIF Argentina)

**Goal:** Scheduled crawler that fetches new Argentine regulations, parses with M1, stores in DB + Qdrant.

### Architecture
- New module: `backend/app/modules/crawler/`
  - `bcra_crawler.py` — Banco Central de la República Argentina
  - `uif_crawler.py` — Unidad de Información Financiera
  - `base_crawler.py` — shared fetch/dedup logic
- Scheduler: APScheduler (async) inside FastAPI lifespan
- Dedup: `source_hash` SHA-256 prevents re-processing the same document

### Tasks
- [ ] Add `apscheduler>=3.10.0` + `httpx` (already in requirements) to deps
- [ ] Create `backend/app/modules/crawler/base_crawler.py`
  - Abstract `fetch_index()` → list of `{url, title, published_at}`
  - `fetch_document(url)` → bytes
  - `process(doc_bytes, metadata)` → calls M1 parse, M6 extract, RAG embed
  - Dedup via `source_hash` check in DB
- [ ] Create `backend/app/modules/crawler/bcra_crawler.py`
  - Target: BCRA Comunicaciones index
  - Parse HTML index → extract communication URLs
- [ ] Create `backend/app/modules/crawler/uif_crawler.py`
  - Target: UIF Resoluciones/Normas index
  - Parse HTML index → extract resolution URLs
- [ ] Create `backend/app/modules/crawler/scheduler.py`
  - APScheduler `AsyncIOScheduler`
  - BCRA: every 6 hours; UIF: every 12 hours
  - Wire into FastAPI `lifespan` context
- [ ] Add crawler status endpoints: `GET /crawler/status`, `POST /crawler/run-now`
- [ ] Add env vars: `CRAWLER_ENABLED`, `CRAWLER_BCRA_URL`, `CRAWLER_UIF_URL`
- [ ] Test: trigger manual run, verify regulation appears in DB + Qdrant

**Files:** `backend/app/modules/crawler/` (new), `backend/app/main.py` (lifespan), `backend/app/api/v1/router.py`, `backend/requirements.txt`

---

## T5 · Compliance Graph (Postgres + AGE)

**Goal:** Model Regulation → Obligation → Entity → Control as a queryable graph.

### Architecture
- Use Apache AGE (Postgres graph extension) — avoids ops overhead of Neo4j
- Add AGE to `docker-compose.yml` (use `apache/age:latest` image or enable extension)
- Graph vertices: Regulation, Obligation, Entity (company/person), Control, Regulator
- Graph edges: REQUIRES, APPLIES_TO, SATISFIES, ISSUED_BY, CROSS_REFERENCES
- Cypher queries exposed via FastAPI endpoints

### Tasks
- [ ] Update `docker-compose.yml`: use `apache/age` postgres image (replaces vanilla postgres:16)
- [ ] Create `backend/app/services/graph_service.py`
  - `ensure_graph()` → create AGE graph `compliance_graph` if not exists
  - `upsert_regulation(regulation)` → vertex + edges
  - `upsert_obligation(obligation)` → vertex + REQUIRES edge to regulation
  - `link_control(obligation_id, control_description)` → SATISFIES edge
  - `cypher_query(query_str)` → raw Cypher execution
- [ ] Wire graph updates into M1 after successful parse
- [ ] Add endpoints: `GET /graph/regulation/{id}/obligations`, `GET /graph/entity/{id}/obligations`, `POST /graph/query` (raw Cypher, admin-only)
- [ ] Create Alembic migration to enable AGE extension + create graph
- [ ] Test: parse a regulation → verify graph vertices + edges exist

**Files:** `docker-compose.yml`, `backend/app/services/graph_service.py` (new), `backend/app/modules/regulatory/engine.py`, `backend/app/api/v1/router.py`

**Risk:** AGE requires Postgres 14-16. Verify version compatibility. Fallback: pgRouting or pure adjacency table.

---

## T6 · Auth Integration (JWT replacing X-Tenant-Id)

**Goal:** Replace bare `X-Tenant-Id` header with signed JWTs. RBAC for admin vs analyst roles.

### Architecture
- JWT signed with app secret (HS256) — no external auth provider dependency for v1
- Claims: `sub` (user_id), `tenant_id`, `role` (admin|analyst|viewer), `exp`
- Middleware: FastAPI dependency `get_current_user` → injects `tenant_id` + `role`
- Auth endpoints: `POST /auth/token` (login), `POST /auth/refresh`
- Future: swap signing to Auth0/Clerk JWKS without changing downstream code

### Tasks
- [ ] Create `backend/app/core/auth.py`
  - `create_token(user_id, tenant_id, role)` → signed JWT
  - `decode_token(token)` → claims dict or raise 401
  - `get_current_user` FastAPI dependency
- [ ] Create `backend/app/db/models.py` addition: `User` model (id, tenant_id, email, hashed_password, role, is_active)
- [ ] Create Alembic migration for `users` table
- [ ] Add `POST /auth/token` endpoint (email+password → JWT)
- [ ] Add `POST /auth/register` endpoint (admin only)
- [ ] Replace `X-Tenant-Id` header extraction in `router.py` with `get_current_user` dependency
- [ ] Keep backward-compat: if JWT absent but `X-Tenant-Id` present + `app_env != production` → allow (dev mode)
- [ ] Add `X-User-Id` claim from JWT (deprecate header)
- [ ] RBAC guards: `POST /graph/query`, `/crawler/run-now` → admin only
- [ ] Test: get token → call protected endpoint → verify tenant isolation

**Files:** `backend/app/core/auth.py` (new), `backend/app/db/models.py`, `backend/app/api/v1/router.py`, `backend/requirements.txt`

---

## Execution Order

```
T1 (benchmark/verify) → T2 (M6 complete) → T3 (Qdrant RAG) → T4 (crawler) → T5 (graph) → T6 (auth)
```

T3 must precede T4 (crawler needs embed). T5 and T6 are independent of each other and can follow any order after T3.

---

## Review

**Completed 2026-05-15.** All 6 tasks implemented, tested, and pushed to `claude/workflow-orchestration-system-1Hx7Y`.

| Task | Status | Key files |
|---|---|---|
| T1 — Orchestrator verify | ✅ | `ai_orchestrator.py` — embed() added, routing verified |
| T2 — M6 Evidence | ✅ | `evidence/engine.py` — dedup + obligation matching |
| T3 — Qdrant RAG | ✅ | `services/rag.py` — async, orchestrator-routed embeddings |
| T4 — Crawler | ✅ | `modules/crawler/` — BCRA + UIF + APScheduler |
| T5 — Compliance graph | ✅ | `services/graph_service.py` — recursive CTE traversal |
| T6 — Auth | ✅ | `core/auth.py` — HS256 JWT + dev fallback |

**Also shipped:** 105-test pytest suite (orchestrator, auth, evidence, RAG, graph, API) + frontend update (JWT login, M6 evidence upload, graph stats, crawler status panels).

**Known gaps for next sprint:**
- Alembic migration history (currently `create_all` only)
- `.env` bootstrap guide / `make init` target
- Frontend: the regulatory, KYC, monitoring, governance panels still use stub forms — wire them to real inputs
- BCRA/UIF HTML scraping may need tuning once live site structure is confirmed
- Graph entity linkage (APPLIES_TO edges) not yet auto-generated — needs entity registry

---

## Sprint 2 — Hardening & Gaps (2026-05-15)

### Completed

| Item | Status | Key files |
|---|---|---|
| `.env` bootstrap (`make init`) | ✅ | `Makefile`, `.env.example` |
| Alembic migration baseline | ✅ | `backend/alembic/versions/0001_initial_schema.py` |
| Frontend M1/M3/M4/M5 real forms | ✅ | `frontend/app/page.tsx` — parse + KYC + monitoring + governance panels |
| BCRA multi-strategy parsing (3 strategies + fallback A7890–A7894) | ✅ | `crawler/bcra_crawler.py` |
| UIF keyword + PDF detection, graceful non-200 | ✅ | `crawler/uif_crawler.py` |
| Base crawler retry with exponential backoff + `CrawlerResult` dataclass | ✅ | `crawler/base_crawler.py` |
| Graph entity registry + `APPLIES_TO` auto-generation | ✅ | `services/graph_service.py` — `register_entity()`, `_wire_entity_to_obligations()` |
| Production hardening: structlog, `RequestIDMiddleware`, error handlers | ✅ | `core/logging.py`, `core/errors.py`, `middleware/request_id.py` |
| Deep health check (`GET /health/detailed`) | ✅ | `api/v1/router.py` |
| Crawler + health test suites | ✅ | `tests/test_crawlers.py` (20 tests), `tests/test_health.py` |

### Remaining for Sprint 3
- Alembic: generate proper versioned migrations for all new tables (ComplianceEntity, GraphVertex/Edge, User)
- Frontend graph subgraph visualization (currently shows raw JSON)
- Frontend real-time crawler status polling (currently manual refresh)
- BCRA/UIF live site smoke test + adjust selectors if needed
- JWT refresh token endpoint (`POST /auth/refresh`)
- Rate limiting middleware (slowapi or manual token bucket)

---

## Sprint 3 — "Tackle all" pass (2026-06-23)

User approved all 6 pre-launch recommendations from the premortem follow-up. Priority = regulatory/security blocking first, then reliability, then frontend.

### Backend — Security/Compliance blocking
- [x] T0.1 Tenant isolation audit — grep all DB queries in `app/`, confirm/add `tenant_id` filter
- [x] T0.4 Audit log INSERT-ONLY DB role — Postgres role + migration revoking UPDATE/DELETE on `audit_log`

### Backend — Reliability
- [x] Backport M10 deterministic-floor pattern into M3 (KYC/AML) and M4 (Monitoring)
- [x] T1.3 Enforce `tenant.data_residency_policy` inside `AIOrchestrator.infer()` before provider selection
- [x] T1.6 Circuit breaker around the NVIDIA leg (open after N consecutive errors, skip straight to fallback tier)

### Frontend — Aesthetics/consistency
- [x] Fold `frontend/public/index2.html` into the Next app as a real route fetching live premortem data
- [x] Extract shared UI primitives (Badge/Card/StatusPill) used across industry/module tabs

### Verification
- [x] `ast.parse` / `tsc --noEmit` sanity check on every touched file
- [x] Review section appended below when done

---

## Review — Sprint 3 ("Tackle all" pass)

All 7 items completed.

| Item | Key files |
|---|---|
| T0.1 Tenant isolation audit | grep-verified `tenant_id` filters across `app/` queries |
| T0.4 Audit log INSERT-ONLY | `backend/alembic/versions/0010_audit_log_insert_only.py` — Postgres role revoking UPDATE/DELETE |
| M10 deterministic-floor backport | `kyc_aml/engine.py`, `monitoring/engine.py` |
| T1.3 Data residency enforcement | `ai_orchestrator.py` — `RESIDENCY_ALLOWED_PROVIDERS` gates provider chain by `Tenant.data_residency_policy` before model selection |
| T1.6 Circuit breaker | `ai_orchestrator.py` — `CircuitBreaker` class, per-provider consecutive-failure tracking, skips open circuits in `infer()` |
| Premortem route | `frontend/app/premortem/page.tsx` (new) — replaces `frontend/public/index2.html` (deleted), fetches live `/api/v1/premortem/{summary,failure-modes,findings}`, fixes the `cos_token` localStorage key bug from the old static page |
| Shared UI primitives | `frontend/app/components/ui.tsx` (new) — `Badge`/`Card`/`StatusPill`/`variantForLevel`, applied in `page.tsx` (severity/risk badges, status pill, Home + Crawler tab cards) and the new premortem route |

**Verification:** `ast.parse` clean on `ai_orchestrator.py`; `tsc --noEmit` clean; `next build` succeeds with `/premortem` as a static route (3.52 kB, 90.7 kB first load).

**Known follow-ups (not in scope for this sprint):** Next.js 14.2.18 has a flagged security advisory (upgrade out of scope); the new premortem route is read-only (mitigations/findings CRUD endpoints exist on the backend but aren't wired into the UI yet).

