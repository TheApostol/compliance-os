# Lessons Learned

_Updated after every correction. Prevents repeating mistakes._

---

## 2026-05-14

### L1 — Workflow: Plan before code
- **Mistake pattern:** Diving into implementation without a written plan leads to missed dependencies and rework.
- **Rule:** For any task with 3+ steps or architectural impact, write `tasks/todo.md` first. Get sign-off before first line of code.

### L2 — Commit hygiene: always push after changes
- **Mistake pattern:** Leaving uncommitted changes triggers the stop hook and breaks flow.
- **Rule:** After every meaningful change to files, commit + push to the feature branch before moving on.

### L3 — Architecture: orchestrator is the single AI gateway
- **Rule:** Never call NVIDIA/OpenAI SDK directly from a module. All inference goes through `AIOrchestrator.infer()`. This is non-negotiable — it's where rate limiting, audit, and cost tracking live.

### L4 — Multi-tenancy: every DB query must filter by tenant_id
- **Rule:** Every `SELECT`, `INSERT`, `UPDATE` that touches tenant data must include a `WHERE tenant_id = :tenant_id` clause. Failing this is a data isolation bug.

### L5 — JSON responses from LLMs: use `_try_parse_json`
- **Rule:** Models sometimes wrap JSON in ```json ... ``` fences. Always use the orchestrator's `_try_parse_json()` — never `json.loads()` directly on LLM output.
