# ComplianceOS as an AI OS — Kernel vs. Vertical Architecture

**Created:** 2026-06-23 | **Owner:** Federico Carlos Polak | **Status:** Architecture assessment (no code moved yet)

---

## Thesis

ComplianceOS is built as one vertical (LATAM regulatory compliance) on top of a small set of
primitives that are *already* vertical-agnostic in practice, even though they aren't yet
packaged as a separate layer. The "AI OS for fintechs" question isn't "build a new platform" —
it's "name and harden the kernel that already exists, then prove a second vertical (Transaction
Monitoring / M10) can run on it without forking it." M10 just did that. This doc records what's
kernel, what's vertical, where the seams leak today, and what minimal moves would make the split
real in the file system, not just in this document.

---

## Part 1: The Kernel (vertical-agnostic today)

| Primitive | File | What makes it kernel, not vertical |
|---|---|---|
| **AI Orchestrator** | `backend/app/services/ai_orchestrator.py` | Sole point of contact with model providers (CLAUDE.md rule #1). Handles routing, fallback chains, rate limiting (40 RPM), cost/latency tracking, audit callback, prompt-injection screening. Nothing in it mentions "compliance" — it operates on `TaskType` + prompts. |
| **Audit hash chain** | `backend/app/core/audit.py` | `append_audit(session, tenant_id, event_type, payload, user_id)` + `verify_chain()`. INSERT-ONLY, SHA-256 chained, generic `event_type: str` + `payload: dict`. Used identically by M1-M10 — none of it encodes compliance semantics. This is the actual regulator-trust moat and is 100% reusable for any audited-decision vertical (lending, fraud, content moderation). |
| **Multi-tenant identity** | `backend/app/core/auth.py`, `Tenant`/`User`/`CurrentUser` in `backend/app/db/models.py` | JWT (local HS256, or RS256 via Auth0/Clerk JWKS) resolves to `CurrentUser(user_id, tenant_id, role)`. `Tenant.data_residency_policy` (JSONB) already exists as a per-tenant AI-provider allowlist. Generic identity/authz, not compliance-specific. |
| **Workflow / DAG state machine** | `backend/app/modules/workflows/engine.py` (rebuilt today) | `create_workflow()` validates the step DAG (DFS cycle detection), `advance_step()` enforces dependency-gating + approval-gating + terminal states, `check_step_timeouts()` escalates overdue steps. Nothing in the engine references compliance — `workflow_type`/`trigger_source`/`title` are caller-supplied strings. This is a generic approval/remediation engine that happens to live under `modules/workflows` today. |
| **DB base / tenant filtering convention** | `backend/app/db/base.py`, repo-wide convention | Async SQLAlchemy session factory + the codebase-wide discipline of filtering every query by `tenant_id`. Generic infra + convention, not a compliance concept. |

**Read on this list:** four of five rows require zero changes to serve a second vertical. The
workflow engine already *is* a kernel primitive; it's just filed under a vertical-sounding
directory name.

---

## Part 2: The Verticals (compliance-specific, built ON the kernel)

Every vertical module follows the same shape: accept a kernel `AIOrchestrator` via DI (never
instantiate a provider client directly), call `orch.infer(InferenceRequest(task=TaskType.X, ...))`,
write results through `append_audit()`, filter all reads/writes by `tenant_id`. Three distinct
**reusable patterns** have emerged across the ten modules — these patterns, not the modules
themselves, are what should be marketed as "AI OS capabilities":

| Pattern | First seen in | Shape | Reusable for |
|---|---|---|---|
| **Pure AI judgment** | M2 Copilot, M3 KYC/AML, M4 Monitoring | Prompt → orchestrator → parsed JSON, no deterministic check, no fallback if AI fails. | Any "ask an expert" task — but see Gap #1 below, this pattern has zero resilience if the model errors. |
| **DB-grounded AI synthesis** | M8 Predictive Risk (fixed today) | Query real aggregates first (e.g. regulation/obligation counts per country), inject them into the prompt as evidence, instruct the model "don't invent figures, reason from the data provided." | Any analytics/forecasting vertical where hallucinated numbers are unacceptable — underwriting risk, fraud trend analysis, market sizing. |
| **Deterministic rules + AI blend** | M10 Transaction Monitoring (built today) | Run cheap deterministic rules first (thresholds, velocity, geography, tenant-custom rules) → always have a `rule_score` → call AI for typology/context → blend `0.4*rule + 0.6*ai` → if AI fails, **fall back to rule-only, never fail open**. | Any scored-decision vertical: fraud scoring, credit decisioning, content moderation, claims triage. This is the most "AI OS"-shaped pattern in the codebase — it's the one to standardize and re-sell. |

M10 (Transaction Monitoring) is the first proof that a second capability can be added without
touching the kernel files at all — `transactions/engine.py` only imports `AIOrchestrator`,
`append_audit`, and its own models. That's the validation that the kernel/vertical split is real,
not aspirational.

---

## Part 3: Where the seams leak (gap analysis)

These are the concrete things that make the kernel *less* reusable than it looks, found while
doing the M7/M8/M10 work — not new work done today, just named so they're trackable:

1. **No deterministic fallback in M3 (KYC/AML) or M4 (Monitoring).** Confirmed by reading
   `backend/app/modules/kyc_aml/engine.py` and `backend/app/modules/monitoring/engine.py`: both are
   a single `orch.infer()` call with no rule-based floor. If the AI call fails, `screen_customer`
   and `analyze_transactions` return whatever `InferenceResult` gives back (likely an
   error/empty result) — unlike M10, which always has a `rule_score` to stand on. This is a real
   reliability gap (ties to premortem F1/F5/F15), not just an architecture nit: a KYC screen that
   silently degrades to nothing during an NVIDIA outage is worse than one that degrades to "rules
   only, flag for manual review."

2. **`TaskType` is one flat enum mixing kernel and vertical concerns.**
   `ai_orchestrator.py`'s `TaskType` enum and `ROUTING` dict hardcode every vertical's task names
   (`REGULATORY_PARSING`, `KYC_SCREENING`, `JURISDICTION_RISK`, ...) directly inside the kernel
   file. Adding a new vertical today means editing the orchestrator itself — the one file CLAUDE.md
   flags as requiring mandatory review for *every* change (the F1 single-point-of-failure control).
   A real kernel would let verticals register their own task→model routing without touching this
   file.

3. **Tenant `data_residency_policy` exists on the model but isn't enforced at inference time.**
   `Tenant.data_residency_policy` (e.g. `{"ai_providers_allowed": ["nvidia", "anthropic"]}`) is
   set on every tenant (see `app/main.py` admin-sync code) but `AIOrchestrator.infer()` never reads
   it before picking a model. This is already tracked as premortem F8/T1.3 — flagging it here
   because "policy-aware routing" is exactly the kind of feature that turns the orchestrator from
   "an LLM router" into "an AI OS kernel" (i.e. the routing decision is governed, not just
   load-balanced). Worth prioritizing if the fintech-AI-OS pitch is the strategic direction.

4. **The workflow engine is misfiled, not miscoded.** `app/modules/workflows/` reads like a
   vertical module (sits next to `kyc_aml/`, `monitoring/`, etc.) but contains zero
   compliance-specific logic. Today it's used for compliance remediation; nothing stops a future
   `transactions` dispute-resolution flow from reusing the same `WorkflowEngine.create_workflow()`
   directly. The only "fix" needed is conceptual: stop thinking of it as M7, start thinking of it
   as kernel infrastructure that M7 happens to be the first consumer of.

---

## Part 4: What would make the split real (future work, not done today)

Per the "Minimal Impact" principle, none of this was executed — it's the concrete next step if
the fintech-AI-OS direction gets prioritized over more compliance verticals:

- **Promote, don't rewrite.** Move `app/modules/workflows/` → `app/kernel/workflow_engine/` (pure
  `git mv` + import updates, zero logic changes — it's already vertical-agnostic per Part 1).
- **Split `TaskType`/`ROUTING` registration out of the orchestrator file.** Let each vertical
  module call `orchestrator.register_task(task_type, fallback_chain)` at import time instead of
  the orchestrator hardcoding every vertical's tasks. The routing *table* stays centrally owned
  (still one audited place to review fallback chains), but the *entries* stop requiring edits to
  `ai_orchestrator.py` itself.
- **Backport the M10 resilience pattern into M3/M4.** Give KYC and Monitoring a cheap deterministic
  floor (sanctions list match, basic threshold rules) so an AI outage degrades to "flagged for
  manual review" instead of an empty result — closes gap #1 and is the single highest-leverage
  reliability fix available given M10 already proved the pattern works.
- **Enforce `data_residency_policy` inside `infer()`** before model selection (closes gap #3,
  resolves premortem F8/T1.3, and is the feature that makes the routing layer genuinely
  governance-aware rather than just a load balancer).

None of these are required to ship M1-M10 for the compliance vertical. They become required the
moment a second paying vertical (e.g. a non-compliance fintech use case) needs to plug into the
same kernel without a fork.

---

## References

- AI Orchestrator: `backend/app/services/ai_orchestrator.py`
- Audit hash chain: `backend/app/core/audit.py`
- Auth/tenancy: `backend/app/core/auth.py`, `backend/app/db/models.py`
- Workflow engine (kernel candidate): `backend/app/modules/workflows/engine.py`
- Pattern reference implementations: `backend/app/modules/predictive/engine.py` (DB-grounded AI),
  `backend/app/modules/transactions/engine.py` (deterministic + AI blend)
- Related premortem risks: F1, F5, F8, F9, F15 in `tasks/premortem.md`
