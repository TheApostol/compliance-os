"""
Unit tests for M7 compliance gap analysis.
All DB calls and AI orchestrator calls are mocked — no live services required.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.compliance.gap_analysis import GapAnalysisResult, run_gap_analysis
from app.services.ai_orchestrator import InferenceResult


# ---------------------------------------------------------------------------
# Helpers — test fixtures
# ---------------------------------------------------------------------------

TENANT_ID = "tenant-test"


def _make_entity(entity_id: str, name: str = "Acme PSP", tenant_id: str = TENANT_ID) -> MagicMock:
    e = MagicMock()
    e.id = entity_id
    e.tenant_id = tenant_id
    e.name = name
    e.entity_type = MagicMock()
    e.entity_type.value = "company"
    e.sectors = ["PSP", "fintech"]
    return e


def _make_regulation(reg_id: str | None = None, code: str = "COM-A-7825") -> MagicMock:
    r = MagicMock()
    r.id = reg_id or str(uuid.uuid4())
    r.code = code
    r.title = f"Regulation {code}"
    r.country = "AR"
    r.regulator = "BCRA"
    r.sector = "PSP"
    r.tenant_id = None
    return r


def _make_vertex(
    vertex_id: str | None = None,
    vertex_type: str = "obligation",
    entity_id: str | None = None,
    label: str = "Test obligation",
    properties: dict | None = None,
) -> MagicMock:
    v = MagicMock()
    v.id = vertex_id or str(uuid.uuid4())
    v.vertex_type = vertex_type
    v.entity_id = entity_id or str(uuid.uuid4())
    v.label = label
    v.properties = properties or {}
    return v


def _make_edge(
    edge_type: str = "APPLIES_TO",
    from_vertex_id: str | None = None,
    to_vertex_id: str | None = None,
) -> MagicMock:
    e = MagicMock()
    e.id = str(uuid.uuid4())
    e.edge_type = edge_type
    e.from_vertex_id = from_vertex_id or str(uuid.uuid4())
    e.to_vertex_id = to_vertex_id or str(uuid.uuid4())
    return e


def _make_inference_result(
    success: bool = True,
    parsed_json: dict | None = None,
    response_text: str = "",
    model_used: str = "moonshotai/kimi-k2-instruct",
    error: str | None = None,
) -> InferenceResult:
    return InferenceResult(
        success=success,
        response_text=response_text,
        parsed_json=parsed_json,
        model_used=model_used,
        fallback_chain_used=[model_used] if model_used else [],
        latency_ttft_ms=100.0,
        latency_total_ms=500.0,
        tokens_in=200,
        tokens_out=300,
        estimated_cost_usd=0.0001,
        audit_id="abc123",
        timestamp="2026-05-21T00:00:00+00:00",
        error=error,
    )


def _build_session_mock(query_map: list) -> MagicMock:
    """
    Build an AsyncMock session where each successive execute() call returns the
    next item from query_map.

    - If the item is a list  → supports .scalars().all()
    - Otherwise              → supports .scalar_one_or_none()
    """
    call_results = []
    for result in query_map:
        exec_result = MagicMock()
        if isinstance(result, list):
            exec_result.scalar_one_or_none.return_value = None
            scalars_mock = MagicMock()
            scalars_mock.all.return_value = result
            exec_result.scalars.return_value = scalars_mock
        else:
            exec_result.scalar_one_or_none.return_value = result
            scalars_mock = MagicMock()
            scalars_mock.all.return_value = []
            exec_result.scalars.return_value = scalars_mock
        call_results.append(exec_result)

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=call_results)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    return session


# ---------------------------------------------------------------------------
# Test 1: entity_not_found → returns None
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_entity_not_found_returns_none():
    """When the entity does not exist for the tenant, run_gap_analysis returns None."""
    entity_id = str(uuid.uuid4())
    session = _build_session_mock([None])  # entity query returns nothing

    mock_orch = AsyncMock()

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr("app.modules.compliance.gap_analysis.AsyncSessionLocal", lambda: session)
        result = await run_gap_analysis(
            entity_id=entity_id,
            tenant_id=TENANT_ID,
            orchestrator=mock_orch,
        )

    assert result is None
    mock_orch.infer.assert_not_called()


# ---------------------------------------------------------------------------
# Test 2: no_gaps → gaps=[], score=100
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_no_gaps_returns_perfect_score():
    """Entity with all obligations satisfied → gaps=[], score_pct=100."""
    entity_id = str(uuid.uuid4())
    entity_vertex_id = str(uuid.uuid4())
    ob_vertex_id = str(uuid.uuid4())
    ctrl_vertex_id = str(uuid.uuid4())

    entity = _make_entity(entity_id)
    regulation = _make_regulation()
    entity_vertex = _make_vertex(entity_vertex_id, vertex_type="entity", entity_id=entity_id)
    applies_edge = _make_edge("APPLIES_TO", from_vertex_id=ob_vertex_id, to_vertex_id=entity_vertex_id)
    ob_vertex = _make_vertex(ob_vertex_id, vertex_type="obligation", label="SAR Reporting")
    satisfies_edge = _make_edge("SATISFIES", from_vertex_id=ctrl_vertex_id, to_vertex_id=ob_vertex_id)

    # DB call sequence: entity, [regulations], entity_vertex, [applies_edges], ob_vertex, satisfies_edge
    session = _build_session_mock([
        entity,            # ComplianceEntity
        [regulation],      # Regulations
        entity_vertex,     # entity graph vertex
        [applies_edge],    # APPLIES_TO edges
        ob_vertex,         # obligation vertex
        satisfies_edge,    # SATISFIES edge → obligation IS satisfied → no gap
    ])

    mock_orch = AsyncMock()
    mock_orch.infer.return_value = _make_inference_result(
        parsed_json={
            "summary": "All obligations are covered.",
            "priority_actions": [],
            "missing_regulations": [],
            "risk_level": "low",
        }
    )

    mock_score = MagicMock()
    mock_score.score_pct = 100.0

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr("app.modules.compliance.gap_analysis.AsyncSessionLocal", lambda: session)
        mp.setattr("app.modules.compliance.gap_analysis.compute_score", AsyncMock(return_value=mock_score))
        result = await run_gap_analysis(entity_id=entity_id, tenant_id=TENANT_ID, orchestrator=mock_orch)

    assert result is not None
    assert isinstance(result, GapAnalysisResult)
    assert result.gaps == []
    assert result.score_pct == 100.0
    assert result.risk_level == "low"


# ---------------------------------------------------------------------------
# Test 3: with_gaps → 2 unsatisfied obligations appear in result
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_with_gaps_returns_unsatisfied_obligations():
    """Two obligations without SATISFIES edges → both appear in gaps."""
    entity_id = str(uuid.uuid4())
    entity_vertex_id = str(uuid.uuid4())

    ob_vertex_id_1 = str(uuid.uuid4())
    ob_vertex_id_2 = str(uuid.uuid4())

    entity = _make_entity(entity_id)
    regulation = _make_regulation()
    entity_vertex = _make_vertex(entity_vertex_id, vertex_type="entity", entity_id=entity_id)

    applies_edge_1 = _make_edge("APPLIES_TO", from_vertex_id=ob_vertex_id_1, to_vertex_id=entity_vertex_id)
    applies_edge_2 = _make_edge("APPLIES_TO", from_vertex_id=ob_vertex_id_2, to_vertex_id=entity_vertex_id)

    ob_vertex_1 = _make_vertex(
        ob_vertex_id_1, vertex_type="obligation", label="AML Report",
        properties={"obligation_type": "reporting", "severity": "HIGH", "frequency": "MONTHLY"},
    )
    ob_vertex_2 = _make_vertex(
        ob_vertex_id_2, vertex_type="obligation", label="KYC Verification",
        properties={"obligation_type": "kyc", "severity": "CRITICAL", "frequency": "EVENT_DRIVEN"},
    )

    session = _build_session_mock([
        entity,                           # ComplianceEntity
        [regulation],                     # Regulations
        entity_vertex,                    # entity graph vertex
        [applies_edge_1, applies_edge_2], # APPLIES_TO edges
        ob_vertex_1, None,                # ob 1 vertex + no SATISFIES edge
        ob_vertex_2, None,                # ob 2 vertex + no SATISFIES edge
    ])

    mock_orch = AsyncMock()
    mock_orch.infer.return_value = _make_inference_result(
        parsed_json={
            "summary": "Two critical gaps identified.",
            "priority_actions": ["Implement KYC flow", "Automate AML reports"],
            "missing_regulations": ["COM-A-7825"],
            "risk_level": "high",
        }
    )

    mock_score = MagicMock()
    mock_score.score_pct = 0.0

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr("app.modules.compliance.gap_analysis.AsyncSessionLocal", lambda: session)
        mp.setattr("app.modules.compliance.gap_analysis.compute_score", AsyncMock(return_value=mock_score))
        result = await run_gap_analysis(entity_id=entity_id, tenant_id=TENANT_ID, orchestrator=mock_orch)

    assert result is not None
    assert len(result.gaps) == 2
    gap_titles = {g["title"] for g in result.gaps}
    assert "AML Report" in gap_titles
    assert "KYC Verification" in gap_titles
    assert result.score_pct == 0.0


# ---------------------------------------------------------------------------
# Test 4: ai_summary included when orchestrator returns JSON
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ai_summary_included_from_orchestrator():
    """When orchestrator returns valid JSON, ai_summary and recommendations are populated."""
    entity_id = str(uuid.uuid4())
    entity = _make_entity(entity_id)

    session = _build_session_mock([
        entity,   # entity found
        [],       # no regulations
        None,     # no entity vertex → no gaps
    ])

    expected_summary = "Entity has significant AML gaps requiring immediate action."
    expected_recs = ["File UIF reports", "Implement sanction screening"]

    mock_orch = AsyncMock()
    mock_orch.infer.return_value = _make_inference_result(
        parsed_json={
            "summary": expected_summary,
            "priority_actions": expected_recs,
            "missing_regulations": [],
            "risk_level": "high",
        }
    )

    mock_score = MagicMock()
    mock_score.score_pct = 60.0

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr("app.modules.compliance.gap_analysis.AsyncSessionLocal", lambda: session)
        mp.setattr("app.modules.compliance.gap_analysis.compute_score", AsyncMock(return_value=mock_score))
        result = await run_gap_analysis(entity_id=entity_id, tenant_id=TENANT_ID, orchestrator=mock_orch)

    assert result is not None
    assert result.ai_summary == expected_summary
    assert result.recommendations == expected_recs
    assert result.risk_level == "high"


# ---------------------------------------------------------------------------
# Test 5: ai_failure_graceful → result still returned with fallback values
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ai_failure_graceful_returns_result():
    """When the orchestrator throws, the function returns a result with fallback values."""
    entity_id = str(uuid.uuid4())
    entity = _make_entity(entity_id)

    session = _build_session_mock([
        entity,   # entity found
        [],       # no regulations
        None,     # no entity vertex → no gaps
    ])

    mock_orch = AsyncMock()
    mock_orch.infer.side_effect = RuntimeError("NVIDIA API timeout")

    mock_score = MagicMock()
    mock_score.score_pct = 80.0

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr("app.modules.compliance.gap_analysis.AsyncSessionLocal", lambda: session)
        mp.setattr("app.modules.compliance.gap_analysis.compute_score", AsyncMock(return_value=mock_score))
        result = await run_gap_analysis(entity_id=entity_id, tenant_id=TENANT_ID, orchestrator=mock_orch)

    assert result is not None
    assert isinstance(result, GapAnalysisResult)
    # Fallback summary is set
    assert result.ai_summary != ""
    assert result.score_pct == 80.0
    # Risk derived from score (80% → low)
    assert result.risk_level in {"low", "medium", "high", "critical"}


# ---------------------------------------------------------------------------
# Test 6: endpoint returns 404 when entity not found
# ---------------------------------------------------------------------------

def test_endpoint_404_when_entity_not_found():
    """POST /compliance/gap-analysis/{entity_id} returns 404 when entity is missing."""
    from contextlib import asynccontextmanager
    from fastapi.testclient import TestClient

    from app.main import app
    from app.core.auth import get_current_user, CurrentUser

    entity_id = str(uuid.uuid4())

    def _fake_user() -> CurrentUser:
        return CurrentUser(user_id="user-1", tenant_id=TENANT_ID, role="analyst")

    # Suppress lifespan (avoids DB/Qdrant connections)
    @asynccontextmanager
    async def _noop_lifespan(app):
        yield

    app.router.lifespan_context = _noop_lifespan
    app.dependency_overrides[get_current_user] = _fake_user

    import app.modules.compliance.gap_analysis as gap_mod
    original_fn = gap_mod.run_gap_analysis
    gap_mod.run_gap_analysis = AsyncMock(return_value=None)

    try:
        with TestClient(app, raise_server_exceptions=True) as client:
            resp = client.post(f"/api/v1/compliance/gap-analysis/{entity_id}")
        assert resp.status_code == 404
        assert "not found" in resp.json().get("detail", "").lower()
    finally:
        gap_mod.run_gap_analysis = original_fn
        app.dependency_overrides.pop(get_current_user, None)
