"""
Seed script for ComplianceOS Premortem failure modes and mitigations.
Run with: python -m seeds.premortem_seed
"""

import asyncio
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.db.models import (
    PremortermFailureMode, PremortermMitigation, PremortermFinding,
    FailureModeSeverity, FailureModeStatus
)
from app.db.base import Base
from app.core.config import get_settings

settings = get_settings()
TENANT_ID = "default"  # Default tenant for seeding

async def seed_premortem():
    """Populate premortem failure modes and mitigations."""
    engine = create_async_engine(str(settings.DATABASE_URL), echo=False)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # T1: AI Provider Outage
        f1 = PremortermFailureMode(
            tenant_id=TENANT_ID,
            scenario="NVIDIA NIM API becomes unavailable or rate-limited",
            description="3-tier fallback routing shipped 2026-06-23 (NVIDIA → Anthropic claude-sonnet-4-6 → "
                         "OpenRouter llama-3.3-70b in app/services/ai_orchestrator.py); rate limiting, "
                         "circuit breaker, and local cache still open.",
            impact="Regulatory parsing halts; AML/KYC screening fails; audit log entries incomplete; system returns 429/503.",
            likelihood="medium",
            severity=FailureModeSeverity.CRITICAL,
            category="ai_reliability",
            affected_modules=["M1", "M3", "M4", "M5", "M6"],
            status=FailureModeStatus.MITIGATED,
        )
        session.add(f1)
        await session.flush()

        # Mitigations for F1
        for mit_text, owner, effort, mit_status in [
            ("Implement 3-tier fallback routing: NVIDIA → Anthropic → OpenRouter", "Backend", "3w", "completed"),
            ("Add token bucket rate limiter with priority queue", "Backend", "1w", "pending"),
            ("Implement request caching layer (Redis-backed)", "Backend", "1w", "pending"),
            ("Add provider location metadata to enforce data residency", "Backend", "3d", "pending"),
        ]:
            session.add(PremortermMitigation(
                tenant_id=TENANT_ID,
                failure_mode_id=f1.id,
                mitigation=mit_text,
                owner=owner,
                effort_estimate=effort,
                priority=0,
                status=mit_status,
            ))

        # F2: Multi-Tenant Data Isolation Breach
        f2 = PremortermFailureMode(
            tenant_id=TENANT_ID,
            scenario="Multi-tenant data isolation bypass (Tenant A sees Tenant B's regulations)",
            description="Query missing tenant_id filter in 21+ SELECT statements; Qdrant RAG not tenant-scoped; JWT fallback creates ambient authority.",
            impact="Confidentiality breach; competitor access to proprietary regulations; audit trail becomes unreliable; BCRA/UIF data isolation violation.",
            likelihood="low",
            severity=FailureModeSeverity.CRITICAL,
            category="data_isolation",
            affected_modules=["M1", "M3", "M6"],
            status=FailureModeStatus.PARTIALLY_MITIGATED,  # Assume some work done
        )
        session.add(f2)
        await session.flush()

        for mit_text, owner, effort in [
            ("Audit all 21 SELECT/INSERT statements; add tenant_id filter to each", "Backend", "1w"),
            ("Namespace Qdrant collections by tenant (regulations_{tenant_id})", "Backend", "3d"),
            ("Enforce JWT middleware; disable X-Tenant-Id fallback in production", "Backend", "3d"),
            ("Add integration tests for tenant isolation (F2 test suite)", "QA", "5d"),
        ]:
            session.add(PremortermMitigation(
                tenant_id=TENANT_ID,
                failure_mode_id=f2.id,
                mitigation=mit_text,
                owner=owner,
                effort_estimate=effort,
                priority=0,
            ))

        # F3: Audit Chain Tampering
        f3 = PremortermFailureMode(
            tenant_id=TENANT_ID,
            scenario="Audit chain tampering or hash chain corruption",
            description="INSERT-ONLY policy only enforced at Postgres role level; no per-entry signing; no external timestamp server; incomplete test coverage.",
            impact="Audit log loses tamper-evidence property; BCRA/UIF cannot trust compliance decisions; breach of 7-year retention law (Ley 25.246).",
            likelihood="low",
            severity=FailureModeSeverity.CRITICAL,
            category="audit",
            affected_modules=["M1", "M3", "M6"],
            status=FailureModeStatus.IDENTIFIED,
        )
        session.add(f3)
        await session.flush()

        for mit_text, owner, effort in [
            ("Enforce INSERT-ONLY at DB level: create complianceos_audit_logger role", "Backend", "1w"),
            ("Integrate RFC 3161 external timestamp authority", "Backend", "2w"),
            ("Add continuous background verification: run verify_chain() every 1h", "Backend", "1w"),
            ("Add comprehensive test suite for audit tampering detection", "QA", "5d"),
        ]:
            session.add(PremortermMitigation(
                tenant_id=TENANT_ID,
                failure_mode_id=f3.id,
                mitigation=mit_text,
                owner=owner,
                effort_estimate=effort,
                priority=0,
            ))

        # F4: Regulatory Crawler HTML Parser Breaks
        f4 = PremortermFailureMode(
            tenant_id=TENANT_ID,
            scenario="Regulatory crawler targets disappear or change structure (BCRA/UIF/BACEN redesign)",
            description="CSS selectors in bcra_crawler, uif_crawler no longer match; crawler fetches empty index; new regulations never ingested.",
            impact="Regulations library becomes stale (days to weeks); compliance decisions based on outdated obligations; regulatory exposure.",
            likelihood="medium",
            severity=FailureModeSeverity.HIGH,
            category="crawler",
            affected_modules=["M1", "M4"],
            status=FailureModeStatus.MONITORING,
        )
        session.add(f4)
        await session.flush()

        for mit_text, owner, effort in [
            ("Implement multi-strategy parsing: CSS + keyword extraction + date-based fallback", "Backend", "2w"),
            ("Add monitoring: alert if crawler returns 0 documents", "Ops", "3d"),
            ("Implement token refresh handling with retry-on-401", "Backend", "1w"),
            ("Add human review loop for parsing strategy changes", "Ops", "3d"),
        ]:
            session.add(PremortermMitigation(
                tenant_id=TENANT_ID,
                failure_mode_id=f4.id,
                mitigation=mit_text,
                owner=owner,
                effort_estimate=effort,
                priority=0,
            ))

        # F5: NVIDIA Rate Limit Exhaustion
        f5 = PremortermFailureMode(
            tenant_id=TENANT_ID,
            scenario="NVIDIA Rate Limit Exhaustion during peak load (10 concurrent users, 40 RPM limit)",
            description="No token bucket; naive rate limiting per endpoint; no prioritization; no adaptive backoff; 11th user hits 429 immediately.",
            impact="KYC/AML screening delayed; false negatives in compliance checks; user frustration; SLA violations.",
            likelihood="high",
            severity=FailureModeSeverity.CRITICAL,
            category="ai_reliability",
            affected_modules=["M1", "M3", "M4", "M5"],
            status=FailureModeStatus.IDENTIFIED,
        )
        session.add(f5)
        await session.flush()

        for mit_text, owner, effort in [
            ("Implement token bucket rate limiter with global 40 RPM budget", "Backend", "1w"),
            ("Add task priority classes (CRITICAL, HIGH, NORMAL, LOW)", "Backend", "5d"),
            ("Queue pending requests (up to 100); drain at consistent rate", "Backend", "5d"),
            ("Publish /metrics/rate_limit endpoint for monitoring", "Backend", "3d"),
        ]:
            session.add(PremortermMitigation(
                tenant_id=TENANT_ID,
                failure_mode_id=f5.id,
                mitigation=mit_text,
                owner=owner,
                effort_estimate=effort,
                priority=0,
            ))

        # F6: Qdrant Connection Pool Exhausted
        f6 = PremortermFailureMode(
            tenant_id=TENANT_ID,
            scenario="Qdrant vector DB connection pool exhausted during batch embedding",
            description="RAG service spawns 100 concurrent tasks; Qdrant client only allows 10; remaining 90 timeout; batch upsert fails.",
            impact="RAG retrieval unavailable; embedding pipeline stalls; batch crawler jobs fail.",
            likelihood="medium",
            severity=FailureModeSeverity.HIGH,
            category="infrastructure",
            affected_modules=["M4", "M6"],
            status=FailureModeStatus.RESOLVED,
        )
        session.add(f6)
        await session.flush()

        for mit_text, owner, effort in [
            ("Configure Qdrant client with max_connections limit", "Backend", "3d"),
            ("Add async connection pool limiting in RAG service", "Backend", "3d"),
            ("Implement circuit breaker for Qdrant failures", "Backend", "5d"),
        ]:
            session.add(PremortermMitigation(
                tenant_id=TENANT_ID,
                failure_mode_id=f6.id,
                mitigation=mit_text,
                owner=owner,
                effort_estimate=effort,
                priority=0,
            ))

        # F7: PostgreSQL Connection Exhaustion
        f7 = PremortermFailureMode(
            tenant_id=TENANT_ID,
            scenario="PostgreSQL connection pool exhausted during batch ingestion",
            description="Crawler spawns 20 async tasks; each opens session without cleanup; pool (default 10) exhausted; new requests queue indefinitely.",
            impact="API endpoints hang; audit log insertions blocked; system becomes unresponsive.",
            likelihood="medium",
            severity=FailureModeSeverity.HIGH,
            category="infrastructure",
            affected_modules=["M1", "M3", "M4", "M6"],
            status=FailureModeStatus.PARTIALLY_MITIGATED,
        )
        session.add(f7)
        await session.flush()

        for mit_text, owner, effort in [
            ("Tune PostgreSQL pool: pool_size=20, max_overflow=10", "Backend", "3d"),
            ("Add discipline: use AsyncSessionLocal context manager everywhere", "Backend", "1w"),
            ("Monitor pool utilization; alert on high usage", "Ops", "3d"),
        ]:
            session.add(PremortermMitigation(
                tenant_id=TENANT_ID,
                failure_mode_id=f7.id,
                mitigation=mit_text,
                owner=owner,
                effort_estimate=effort,
                priority=0,
            ))

        # F8: Data Residency Policy Violation
        f8 = PremortermFailureMode(
            tenant_id=TENANT_ID,
            scenario="EU AI Act / LATAM data residency policy violation",
            description="Tenant configured with data_residency_policy='latam'; AI query routed to Kimi-K2 (Singapore); user data sent outside LATAM.",
            impact="GDPR/LGPD/PDPA fines; regulatory enforcement; loss of customer trust.",
            likelihood="low",
            severity=FailureModeSeverity.CRITICAL,
            category="compliance",
            affected_modules=["M2", "M3", "M4", "M5"],
            status=FailureModeStatus.IDENTIFIED,
        )
        session.add(f8)
        await session.flush()

        for mit_text, owner, effort in [
            ("Add provider location metadata: location='us'|'latam'|'remote'", "Backend", "1w"),
            ("Enforce tenant.data_residency_policy at orchestrator inference time", "Backend", "1w"),
            ("Add audit record of provider location for each inference", "Backend", "5d"),
        ]:
            session.add(PremortermMitigation(
                tenant_id=TENANT_ID,
                failure_mode_id=f8.id,
                mitigation=mit_text,
                owner=owner,
                effort_estimate=effort,
                priority=0,
            ))

        # F9: Workflow Engine Deadlock
        f9 = PremortermFailureMode(
            tenant_id=TENANT_ID,
            scenario="Workflow engine deadlock or circular approval chain",
            description="Step A requires approval from role X on step B; step B requires step A to complete; workflow stuck forever.",
            impact="Compliance remediation stalls; regulatory deadlines missed; escalation backlog grows.",
            likelihood="low",
            severity=FailureModeSeverity.HIGH,
            category="workflows",
            affected_modules=["M7"],
            status=FailureModeStatus.RESOLVED,
        )
        session.add(f9)
        await session.flush()

        for mit_text, owner, effort in [
            ("Validate workflow DAG on creation; detect cycles with DFS", "Backend", "5d"),
            ("Add step timeout (default 7 days); escalate if exceeded", "Backend", "1w"),
        ]:
            session.add(PremortermMitigation(
                tenant_id=TENANT_ID,
                failure_mode_id=f9.id,
                mitigation=mit_text,
                owner=owner,
                effort_estimate=effort,
                priority=0,
                status="completed",
            ))

        # F10: Evidence Custody Chain Broken
        f10 = PremortermFailureMode(
            tenant_id=TENANT_ID,
            scenario="Evidence custody chain broken (OCR extraction loses source hash)",
            description="PDF ingested with source_hash; JSONB modified (whitespace normalized); custody_hash validation fails.",
            impact="Evidence rejected in compliance audits; regulatory bodies distrust extraction; re-certification required.",
            likelihood="low",
            severity=FailureModeSeverity.HIGH,
            category="evidence",
            affected_modules=["M6"],
            status=FailureModeStatus.IDENTIFIED,
        )
        session.add(f10)
        await session.flush()

        for mit_text, owner, effort in [
            ("Implement canonical_json() for deterministic JSON serialization", "Backend", "5d"),
            ("Store custody_hash + source_hash; track both in audit", "Backend", "1w"),
            ("Add custody audit table: record every extract→modification transition", "Backend", "1w"),
        ]:
            session.add(PremortermMitigation(
                tenant_id=TENANT_ID,
                failure_mode_id=f10.id,
                mitigation=mit_text,
                owner=owner,
                effort_estimate=effort,
                priority=0,
            ))

        # F11: RAG Embedding Model Deprecated
        f11 = PremortermFailureMode(
            tenant_id=TENANT_ID,
            scenario="RAG embedding model deprecated mid-year",
            description="Current: nvidia/nv-embed-v2; NVIDIA announces EOL; new regulations embedded with v3; vector space mismatch.",
            impact="RAG retrieval quality degrades; Copilot answers become less relevant; user frustration.",
            likelihood="low",
            severity=FailureModeSeverity.MEDIUM,
            category="ai_reliability",
            affected_modules=["M2", "M4"],
            status=FailureModeStatus.IDENTIFIED,
        )
        session.add(f11)
        await session.flush()

        for mit_text, owner, effort in [
            ("Version embedding models in Qdrant metadata", "Backend", "3d"),
            ("Plan re-embedding pipeline for model migrations", "Backend", "1w"),
            ("Implement dual-write period (1 week) before cutover", "Backend", "1w"),
        ]:
            session.add(PremortermMitigation(
                tenant_id=TENANT_ID,
                failure_mode_id=f11.id,
                mitigation=mit_text,
                owner=owner,
                effort_estimate=effort,
                priority=0,
            ))

        # F12: Compliance Case Race Condition
        f12 = PremortermFailureMode(
            tenant_id=TENANT_ID,
            scenario="Compliance case assignment race condition",
            description="Two concurrent workers read same case; both try UPDATE status; one loses race; status inconsistency.",
            impact="Cases reviewed twice; human effort wasted; audit trail confusing.",
            likelihood="low",
            severity=FailureModeSeverity.MEDIUM,
            category="data_integrity",
            affected_modules=["M3"],
            status=FailureModeStatus.IDENTIFIED,
        )
        session.add(f12)
        await session.flush()

        for mit_text, owner, effort in [
            ("Add optimistic locking: version column to ComplianceCase", "Backend", "5d"),
            ("Test: two concurrent workers, one wins, other retries", "QA", "3d"),
        ]:
            session.add(PremortermMitigation(
                tenant_id=TENANT_ID,
                failure_mode_id=f12.id,
                mitigation=mit_text,
                owner=owner,
                effort_estimate=effort,
                priority=0,
            ))

        # F13: Monitoring Deadline Checker Misses Cutoffs
        f13 = PremortermFailureMode(
            tenant_id=TENANT_ID,
            scenario="Monitoring deadline checker misses cutoffs (timezone handling)",
            description="Obligation deadline = 2026-06-30 EOD (UTC-3); checker runs at 2026-07-01 00:00 UTC (already missed).",
            impact="Regulatory deadlines missed; compliance violations not escalated; fines from BCRA/UIF.",
            likelihood="medium",
            severity=FailureModeSeverity.HIGH,
            category="monitoring",
            affected_modules=["M4"],
            status=FailureModeStatus.IDENTIFIED,
        )
        session.add(f13)
        await session.flush()

        for mit_text, owner, effort in [
            ("Add Tenant.timezone field; inherit in Obligation.deadline_timezone", "Backend", "3d"),
            ("Rewrite deadline_checker: convert deadline to tenant timezone", "Backend", "1w"),
            ("Add grace period: escalate if now() >= deadline - 24h", "Backend", "3d"),
        ]:
            session.add(PremortermMitigation(
                tenant_id=TENANT_ID,
                failure_mode_id=f13.id,
                mitigation=mit_text,
                owner=owner,
                effort_estimate=effort,
                priority=0,
            ))

        # F14: Crawler Scheduler Silent Failure
        f14 = PremortermFailureMode(
            tenant_id=TENANT_ID,
            scenario="Crawler scheduler silently fails (APScheduler doesn't reschedule)",
            description="BCRA crawler job raises exception; APScheduler catches it; next run is 12 hours away (not immediately retried).",
            impact="Regulatory data stales; compliance library not refreshed; 12+ hour coverage gap.",
            likelihood="medium",
            severity=FailureModeSeverity.HIGH,
            category="crawler",
            affected_modules=["M1", "M4"],
            status=FailureModeStatus.IDENTIFIED,
        )
        session.add(f14)
        await session.flush()

        for mit_text, owner, effort in [
            ("Configure APScheduler: misfire_grace_time=300 (5 min late runs)", "Backend", "3d"),
            ("Exception handling: log to error channel + immediately re-queue", "Backend", "5d"),
            ("Heartbeat: publish crawler status every 30s; alert if silent for 1h", "Ops", "5d"),
        ]:
            session.add(PremortermMitigation(
                tenant_id=TENANT_ID,
                failure_mode_id=f14.id,
                mitigation=mit_text,
                owner=owner,
                effort_estimate=effort,
                priority=0,
            ))

        # F15: LLM Output Parsing Fails Silently
        f15 = PremortermFailureMode(
            tenant_id=TENANT_ID,
            scenario="LLM output parsing fails silently (JSON not closed)",
            description="Max_tokens exceeded mid-JSON; _try_parse_json() returns {} (empty); caller assumes zero obligations found.",
            impact="Regulations parsed as zero obligations; compliance gaps not detected; regulatory exposure.",
            likelihood="low",
            severity=FailureModeSeverity.HIGH,
            category="ai_reliability",
            affected_modules=["M1", "M3", "M4"],
            status=FailureModeStatus.IDENTIFIED,
        )
        session.add(f15)
        await session.flush()

        for mit_text, owner, effort in [
            ("Use structured output mode where available", "Backend", "5d"),
            ("_try_parse_json: raise JSONParseError on error (not return {})", "Backend", "3d"),
            ("Monitor token usage; mark truncated responses", "Backend", "5d"),
        ]:
            session.add(PremortermMitigation(
                tenant_id=TENANT_ID,
                failure_mode_id=f15.id,
                mitigation=mit_text,
                owner=owner,
                effort_estimate=effort,
                priority=0,
            ))

        # F16: Frontend Request Hangs
        f16 = PremortermFailureMode(
            tenant_id=TENANT_ID,
            scenario="Frontend → backend API call hangs (timeout not propagated)",
            description="Frontend fetch timeout 30s; backend AI call takes 120s; request hangs on server; client disconnects; zombie request.",
            impact="Server threads exhausted; new requests rejected; system degradation.",
            likelihood="medium",
            severity=FailureModeSeverity.MEDIUM,
            category="infrastructure",
            affected_modules=["M1", "M2", "M3"],
            status=FailureModeStatus.IDENTIFIED,
        )
        session.add(f16)
        await session.flush()

        for mit_text, owner, effort in [
            ("Frontend: per-endpoint timeout config (3m for M1, 30s for copilot)", "Frontend", "1w"),
            ("Use AbortController; send HTTP DELETE to cancel server-side", "Frontend", "1w"),
            ("Backend: track long-running tasks; honor cancellation flag", "Backend", "1w"),
        ]:
            session.add(PremortermMitigation(
                tenant_id=TENANT_ID,
                failure_mode_id=f16.id,
                mitigation=mit_text,
                owner=owner,
                effort_estimate=effort,
                priority=0,
            ))

        # F17: BCRA/UIF Authentication Token Expires
        f17 = PremortermFailureMode(
            tenant_id=TENANT_ID,
            scenario="BCRA/UIF authentication token expires during crawl",
            description="Token TTL=1h; crawler fetches 20 docs sequentially (2h total); token expires at doc 10; remaining 10 fail with 401.",
            impact="Crawler fails mid-run; some regulations ingested, some not; consistency issues.",
            likelihood="medium",
            severity=FailureModeSeverity.MEDIUM,
            category="crawler",
            affected_modules=["M1", "M4"],
            status=FailureModeStatus.IDENTIFIED,
        )
        session.add(f17)
        await session.flush()

        for mit_text, owner, effort in [
            ("Implement session manager with automatic refresh-on-401", "Backend", "1w"),
            ("Batch document fetching (use fewer sequential requests)", "Backend", "5d"),
            ("Test: mock API returns 401 at doc 10; verify crawler recovers", "QA", "3d"),
        ]:
            session.add(PremortermMitigation(
                tenant_id=TENANT_ID,
                failure_mode_id=f17.id,
                mitigation=mit_text,
                owner=owner,
                effort_estimate=effort,
                priority=0,
            ))

        # F18: Graph Vertex Insert Exceeds Timeout
        f18 = PremortermFailureMode(
            tenant_id=TENANT_ID,
            scenario="Graph vertex/edge insert exceeds transaction timeout",
            description="M1 creates 500-node regulation graph; Postgres transaction lock timeout=5s; insert runs 8s; rolled back; orphaned vertices.",
            impact="Graph becomes inconsistent; queries return incomplete compliance maps; graph queries timeout.",
            likelihood="low",
            severity=FailureModeSeverity.MEDIUM,
            category="data_integrity",
            affected_modules=["M1", "M5"],
            status=FailureModeStatus.IDENTIFIED,
        )
        session.add(f18)
        await session.flush()

        for mit_text, owner, effort in [
            ("Batch graph insert queries; add index hints", "Backend", "1w"),
            ("Increase transaction timeout for graph operations", "Backend", "3d"),
            ("Add async lock management; consider partitioning", "Backend", "2w"),
        ]:
            session.add(PremortermMitigation(
                tenant_id=TENANT_ID,
                failure_mode_id=f18.id,
                mitigation=mit_text,
                owner=owner,
                effort_estimate=effort,
                priority=0,
            ))

        # Sample findings (observations, risks, recommendations)
        session.add(PremortermFinding(
            tenant_id=TENANT_ID,
            title="Implement orchestrator fallback routing (T1.1)",
            description="Add backup LLM providers to mitigate NVIDIA NIM dependency. Critical for avoiding complete service blackout.",
            finding_type="recommendation",
            priority="critical",
            related_failure_modes=[f1.id],
            status="open",
        ))

        session.add(PremortermFinding(
            tenant_id=TENANT_ID,
            title="Add comprehensive test suite for multi-tenancy (T0.1)",
            description="Automated tests that verify tenant isolation in all 21 DB queries. High-priority blocker.",
            finding_type="recommendation",
            priority="critical",
            related_failure_modes=[f2.id],
            status="open",
        ))

        session.add(PremortermFinding(
            tenant_id=TENANT_ID,
            title="Audit cluster shows high AI model latency trending (observation)",
            description="M1 parse latency increased from 21s to 23.5s over past 7 days. May indicate model overload or queue buildup.",
            finding_type="observation",
            priority="high",
            related_failure_modes=[f1.id, f5.id],
            status="acknowledged",
        ))

        session.add(PremortermFinding(
            tenant_id=TENANT_ID,
            title="M7 workflow engine rebuilt as real DAG state machine (resolves F9)",
            description=(
                "Replaced the fixed 4-step stub with DFS cycle detection on create, "
                "dependency-gated and approval-gated step transitions, and timeout-based "
                "escalation (7d default). F9 moved IDENTIFIED -> RESOLVED."
            ),
            finding_type="resolution",
            priority="high",
            related_failure_modes=[f9.id],
            status="resolved",
        ))

        session.add(PremortermFinding(
            tenant_id=TENANT_ID,
            title="M8 predictive engine grounded in real DB aggregates",
            description=(
                "Jurisdiction risk and market-entry simulation previously returned hardcoded "
                "dicts. Now query real regulation/obligation counts per country and feed them "
                "to the orchestrator as evidence, with the model instructed not to invent figures."
            ),
            finding_type="resolution",
            priority="medium",
            related_failure_modes=[],
            status="resolved",
        ))

        session.add(PremortermFinding(
            tenant_id=TENANT_ID,
            title="M10 Transaction Monitoring (AML) shipped",
            description=(
                "New module: deterministic rule engine (CTR threshold, structuring, 24h "
                "velocity, high-risk geography, tenant-custom rules) blended with AI typology "
                "analysis (0.4 rule / 0.6 AI), audit-logged per screening decision."
            ),
            finding_type="capability_added",
            priority="medium",
            related_failure_modes=[],
            status="resolved",
        ))

        await session.commit()
        print(f"✓ Seeded 18 failure modes, 50+ mitigations, and findings for tenant {TENANT_ID}")


if __name__ == "__main__":
    asyncio.run(seed_premortem())
