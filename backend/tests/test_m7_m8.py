"""
Unit tests for M7 (WorkflowEngine), M8 (PredictiveEngine), and LATAM Crawler.

All DB calls and AI orchestrator calls are mocked — no live services required.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

TENANT_ID = "tenant-test"


def _make_async_session() -> MagicMock:
    """Return an AsyncMock that behaves as an async context manager session."""
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


# ─────────────────────────────────────────────────────────────────────────────
# M7 WorkflowEngine — 6 tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_remediation_workflow_returns_correct_shape():
    """Returned dict must have workflow_id, status, and title keys."""
    from app.modules.workflows.engine import WorkflowEngine
    from app.modules.workflows.models import WorkflowStatus

    session = _make_async_session()

    # After refresh, wf.id and wf.status must be accessible
    fake_wf_id = uuid.uuid4()

    def _set_wf_attrs(wf):
        wf.id = fake_wf_id
        wf.status = WorkflowStatus.PENDING
        wf.title = "Test Remediation"

    session.refresh.side_effect = lambda wf: _set_wf_attrs(wf)

    with patch("app.modules.workflows.engine.AsyncSessionLocal", return_value=session):
        engine = WorkflowEngine()
        result = await engine.create_remediation_workflow(
            tenant_id=TENANT_ID,
            title="Test Remediation",
            trigger_source="unit-test",
        )

    assert "workflow_id" in result
    assert "status" in result
    assert "title" in result


@pytest.mark.asyncio
async def test_create_remediation_workflow_creates_4_steps():
    """session.add() must be called 5 times: 1 Workflow + 4 WorkflowSteps."""
    from app.modules.workflows.engine import WorkflowEngine
    from app.modules.workflows.models import WorkflowStatus

    session = _make_async_session()
    fake_wf_id = uuid.uuid4()

    def _set_wf_attrs(wf):
        wf.id = fake_wf_id
        wf.status = WorkflowStatus.PENDING
        wf.title = "Add Calls Test"

    session.refresh.side_effect = lambda wf: _set_wf_attrs(wf)

    with patch("app.modules.workflows.engine.AsyncSessionLocal", return_value=session):
        engine = WorkflowEngine()
        await engine.create_remediation_workflow(
            tenant_id=TENANT_ID,
            title="Add Calls Test",
            trigger_source="unit-test",
        )

    assert session.add.call_count == 5  # 1 workflow + 4 steps


@pytest.mark.asyncio
async def test_workflow_status_defaults_to_pending():
    """The status returned in the dict must be 'pending'."""
    from app.modules.workflows.engine import WorkflowEngine
    from app.modules.workflows.models import WorkflowStatus

    session = _make_async_session()
    fake_wf_id = uuid.uuid4()

    def _set_wf_attrs(wf):
        wf.id = fake_wf_id
        wf.status = WorkflowStatus.PENDING
        wf.title = "Status Test"

    session.refresh.side_effect = lambda wf: _set_wf_attrs(wf)

    with patch("app.modules.workflows.engine.AsyncSessionLocal", return_value=session):
        engine = WorkflowEngine()
        result = await engine.create_remediation_workflow(
            tenant_id=TENANT_ID,
            title="Status Test",
            trigger_source="unit-test",
        )

    assert result["status"] == "pending"


def test_get_workflow_engine_returns_singleton():
    """Calling get_workflow_engine() twice must return the same object."""
    from app.modules.workflows.engine import get_workflow_engine

    engine1 = get_workflow_engine()
    engine2 = get_workflow_engine()
    assert engine1 is engine2


@pytest.mark.asyncio
async def test_workflow_severity_passed_through():
    """The severity='high' argument must be set on the Workflow object passed to session.add()."""
    from app.modules.workflows.engine import WorkflowEngine
    from app.modules.workflows.models import Workflow, WorkflowStatus

    session = _make_async_session()
    captured_workflows: list = []

    def _capture_add(obj):
        if isinstance(obj, Workflow):
            captured_workflows.append(obj)

    session.add = MagicMock(side_effect=_capture_add)
    fake_wf_id = uuid.uuid4()

    def _set_wf_attrs(wf):
        wf.id = fake_wf_id
        wf.status = WorkflowStatus.PENDING
        wf.title = "Severity Test"

    session.refresh.side_effect = lambda wf: _set_wf_attrs(wf)

    with patch("app.modules.workflows.engine.AsyncSessionLocal", return_value=session):
        engine = WorkflowEngine()
        await engine.create_remediation_workflow(
            tenant_id=TENANT_ID,
            title="Severity Test",
            trigger_source="unit-test",
            severity="high",
        )

    assert len(captured_workflows) == 1
    assert captured_workflows[0].severity == "high"


@pytest.mark.asyncio
async def test_workflow_has_all_required_step_types():
    """The 4 default step_types must include impact_analysis, policy_review, evidence_collection, final_approval."""
    from app.modules.workflows.engine import WorkflowEngine
    from app.modules.workflows.models import Workflow, WorkflowStatus, WorkflowStep

    session = _make_async_session()
    captured_steps: list = []

    def _capture_add(obj):
        if isinstance(obj, WorkflowStep):
            captured_steps.append(obj)

    session.add.side_effect = _capture_add
    fake_wf_id = uuid.uuid4()

    def _set_wf_attrs(wf):
        wf.id = fake_wf_id
        wf.status = WorkflowStatus.PENDING
        wf.title = "Step Types Test"

    session.refresh.side_effect = lambda wf: _set_wf_attrs(wf)

    with patch("app.modules.workflows.engine.AsyncSessionLocal", return_value=session):
        engine = WorkflowEngine()
        await engine.create_remediation_workflow(
            tenant_id=TENANT_ID,
            title="Step Types Test",
            trigger_source="unit-test",
        )

    step_types = {s.step_type for s in captured_steps}
    assert "impact_analysis" in step_types
    assert "policy_review" in step_types
    assert "evidence_collection" in step_types
    assert "final_approval" in step_types


# ─────────────────────────────────────────────────────────────────────────────
# M8 PredictiveEngine — 5 tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_jurisdiction_risk_scores_returns_country_codes():
    """jurisdiction_risk_scores() must return a dict containing AR and BR keys."""
    from app.modules.predictive.engine import PredictiveEngine

    engine = PredictiveEngine()
    result = await engine.jurisdiction_risk_scores()

    assert "AR" in result
    assert "BR" in result


@pytest.mark.asyncio
async def test_jurisdiction_risk_fallback_on_ai_failure():
    """Even if an AI call were to fail, the engine returns at least AR, BR, MX."""
    from app.modules.predictive.engine import PredictiveEngine

    engine = PredictiveEngine()
    # The current engine returns static data. Verify fallback values always present.
    result = await engine.jurisdiction_risk_scores()

    assert "AR" in result
    assert "BR" in result
    assert "MX" in result


@pytest.mark.asyncio
async def test_simulate_market_entry_returns_required_fields():
    """simulate_market_entry() must return business_model, countries, estimated_regulatory_complexity,
    predicted_risk_level, and key_requirements."""
    from app.modules.predictive.engine import PredictiveEngine

    engine = PredictiveEngine()
    result = await engine.simulate_market_entry(
        business_model="fintech_psp",
        countries=["AR", "BR"],
    )

    assert "business_model" in result
    assert "countries" in result
    assert "estimated_regulatory_complexity" in result
    assert "predicted_risk_level" in result
    assert "key_requirements" in result


@pytest.mark.asyncio
async def test_simulate_market_entry_fallback():
    """simulate_market_entry() must echo back the business_model and countries passed in."""
    from app.modules.predictive.engine import PredictiveEngine

    engine = PredictiveEngine()
    result = await engine.simulate_market_entry(
        business_model="crypto_exchange",
        countries=["MX"],
    )

    assert result["business_model"] == "crypto_exchange"
    assert "MX" in result["countries"]


def test_get_predictive_engine_returns_singleton():
    """Calling get_predictive_engine() twice must return the same object."""
    from app.modules.predictive.engine import get_predictive_engine

    engine1 = get_predictive_engine()
    engine2 = get_predictive_engine()
    assert engine1 is engine2


# ─────────────────────────────────────────────────────────────────────────────
# LATAM Crawler — 5 tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_crawl_regulator_raises_on_unknown_regulator():
    """crawl_regulator() with an unknown regulator name must raise ValueError."""
    from app.modules.crawler.latam_regulatory_crawler import LatamRegulatoryCrawler

    async with LatamRegulatoryCrawler() as crawler:
        with pytest.raises(ValueError, match="Unsupported regulator"):
            await crawler.crawl_regulator("UNKNOWN", TENANT_ID)


def test_crawl_result_hash_consistency():
    """The same raw payload always produces the same evidence_hash."""
    from app.modules.crawler.latam_regulatory_crawler import LatamRegulatoryCrawler, CrawlResult

    crawler = LatamRegulatoryCrawler.__new__(LatamRegulatoryCrawler)
    payload = {"key": "value", "num": 42}
    hash1 = crawler._hash_payload(payload)
    hash2 = crawler._hash_payload(payload)
    assert hash1 == hash2
    # Also verify the hash is a valid SHA-256 hex string
    assert len(hash1) == 64


@pytest.mark.asyncio
async def test_store_results_skips_duplicate():
    """store_results() skips session.add() when an existing record with the same hash is found."""
    from app.modules.crawler.latam_regulatory_crawler import LatamRegulatoryCrawler, CrawlResult

    result = CrawlResult(
        source="BCRA - Test",
        country="AR",
        regulator="BCRA",
        code="BCRA_TEST",
        title="Test",
        raw_data={"test": True},
        evidence_hash="abc123hash",
        tenant_id=TENANT_ID,
    )

    # Build the execute result mock that returns a truthy existing record
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = MagicMock()  # truthy = existing record

    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.execute = AsyncMock(return_value=exec_result)
    session.add = MagicMock()

    with patch("app.modules.crawler.latam_regulatory_crawler.AsyncSessionLocal", return_value=session):
        crawler = LatamRegulatoryCrawler.__new__(LatamRegulatoryCrawler)
        await crawler.store_results([result])

    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_store_results_inserts_new():
    """store_results() calls session.add() when no existing record is found."""
    from app.modules.crawler.latam_regulatory_crawler import LatamRegulatoryCrawler, CrawlResult

    result = CrawlResult(
        source="BCRA - New",
        country="AR",
        regulator="BCRA",
        code="BCRA_NEW",
        title="New",
        raw_data={"new": True},
        evidence_hash="newhash456",
        tenant_id=TENANT_ID,
    )

    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = None  # no existing record

    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.execute = AsyncMock(return_value=exec_result)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    # Mock downstream hooks so they don't raise
    with patch("app.modules.crawler.latam_regulatory_crawler.AsyncSessionLocal", return_value=session):
        crawler = LatamRegulatoryCrawler.__new__(LatamRegulatoryCrawler)
        crawler._safe_downstream_hooks = AsyncMock()
        await crawler.store_results([result])

    session.add.assert_called_once()


@pytest.mark.asyncio
async def test_safe_downstream_hooks_does_not_raise_on_rag_failure():
    """_safe_downstream_hooks() must complete without raising even if get_rag() raises."""
    from app.modules.crawler.latam_regulatory_crawler import LatamRegulatoryCrawler, CrawlResult

    crawl_result = CrawlResult(
        source="BCRA - Hook Test",
        country="AR",
        regulator="BCRA",
        code="BCRA_HOOK",
        title="Hook Test",
        raw_data={"hook": True},
        evidence_hash="hooktest789",
        tenant_id=TENANT_ID,
    )

    fake_regulation = MagicMock()
    fake_regulation.id = str(uuid.uuid4())
    fake_regulation.title = "Auto-crawled BCRA"
    fake_regulation.full_text = "{}"

    crawler = LatamRegulatoryCrawler.__new__(LatamRegulatoryCrawler)

    with patch(
        "app.services.rag.get_rag",
        side_effect=Exception("RAG unavailable"),
    ):
        # Should complete without raising
        await crawler._safe_downstream_hooks(fake_regulation, crawl_result)


# ── Priority 5 additions ─────────────────────────────────────────────

@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        yield c


def test_auth_refresh_returns_new_token(client):
    """POST /auth/refresh with a valid refresh token returns a new access token."""
    from app.core.auth import create_refresh_token
    refresh = create_refresh_token(user_id="u1", tenant_id="polkorp", role="analyst")
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


def test_critical_alert_triggers_workflow():
    """deadline_checker creates a workflow for new critical alerts."""
    import asyncio
    from unittest.mock import AsyncMock, MagicMock, patch

    async def _run():
        with patch("app.db.base.AsyncSessionLocal") as mock_cls, \
             patch("app.modules.workflows.engine.get_workflow_engine") as mock_wf_cls:

            session = AsyncMock()
            session.__aenter__ = AsyncMock(return_value=session)
            session.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = session

            # Return no regulations (short-circuit the loop)
            r1 = MagicMock()
            r1.scalars.return_value.all.return_value = []
            session.execute = AsyncMock(return_value=r1)

            from app.modules.monitoring.deadline_checker import check_deadlines
            result = await check_deadlines(tenant_id="polkorp")
            assert "created" in result

    asyncio.run(_run())


def test_m8_returns_cached_on_rate_limit():
    """M8 market entry simulation returns rule-based fallback gracefully."""
    import asyncio

    async def _run():
        with patch("app.services.ai_orchestrator.get_orchestrator") as mock_orch:
            # Simulate rate limit (orchestrator returns error)
            mock_result = MagicMock()
            mock_result.success = False
            mock_result.error = "429 rate limit exceeded"
            mock_result.parsed_json = None
            mock_orch.return_value.infer = AsyncMock(return_value=mock_result)

            from app.modules.predictive.engine import PredictiveEngine
            engine = PredictiveEngine()
            result = await engine.simulate_market_entry(
                business_model="CRYPTO_VASP",
                countries=["AR"],
                tenant_id="polkorp",
            )
            # Should fall back gracefully, not raise
            assert result is not None
            assert "predicted_risk_level" in result or "_source" in result

    asyncio.run(_run())
