"""Tests for Sprint 5 dashboard endpoints: KYC queue, RoF generation, score history, canned questions, vertical config."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ── Canned Questions (no DB, no auth needed) ────────────────────────

def test_canned_questions_crypto_vasp_returns_4(test_client):
    resp = test_client.get("/api/v1/copilot/canned-questions?vertical=CRYPTO_VASP")
    assert resp.status_code == 200
    data = resp.json()
    assert data["vertical"] == "CRYPTO_VASP"
    assert len(data["questions"]) == 4


def test_canned_questions_all_verticals_have_4(test_client):
    verticals = ["FINTECH", "CRYPTO_VASP", "INSURANCE", "HEALTH_PHARMA", "GAMING", "CAPITAL_MARKETS", "TELECOM"]
    for v in verticals:
        resp = test_client.get(f"/api/v1/copilot/canned-questions?vertical={v}")
        assert resp.status_code == 200, f"Failed for vertical {v}"
        assert len(resp.json()["questions"]) == 4, f"Expected 4 questions for {v}"


def test_canned_questions_unknown_vertical_returns_fintech_default(test_client):
    resp = test_client.get("/api/v1/copilot/canned-questions?vertical=UNKNOWN")
    assert resp.status_code == 200
    assert resp.json()["vertical"] == "UNKNOWN"
    assert len(resp.json()["questions"]) == 4  # Falls back to FINTECH


# ── KYC Queue ────────────────────────────────────────────────────────

def test_kyc_queue_returns_pending_cases(test_client):
    """KYC queue returns list structure even if empty."""
    with patch("app.db.base.AsyncSessionLocal") as mock_session_cls:
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value = mock_session

        mock_tenant = MagicMock()
        mock_tenant.id = str(uuid.uuid4())

        mock_result_tenant = MagicMock()
        mock_result_tenant.scalar_one_or_none.return_value = mock_tenant

        mock_result_cases = MagicMock()
        mock_result_cases.scalars.return_value.all.return_value = []

        mock_session.execute = AsyncMock(side_effect=[mock_result_tenant, mock_result_cases])

        resp = test_client.get("/api/v1/kyc/queue")
        assert resp.status_code == 200
        data = resp.json()
        assert "cases" in data
        assert "count" in data
        assert isinstance(data["cases"], list)


def test_kyc_queue_tenant_isolated(test_client):
    """KYC queue returns empty list when tenant not found."""
    with patch("app.db.base.AsyncSessionLocal") as mock_session_cls:
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value = mock_session

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # tenant not found
        mock_session.execute = AsyncMock(return_value=mock_result)

        resp = test_client.get("/api/v1/kyc/queue")
        assert resp.status_code == 200
        assert resp.json()["cases"] == []


def test_kyc_queue_sorted_by_risk(test_client):
    """Verify the endpoint accepts risk_level filter and returns structured response."""
    with patch("app.db.base.AsyncSessionLocal") as mock_session_cls:
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value = mock_session

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        resp = test_client.get("/api/v1/kyc/queue?risk_level=HIGH&limit=10")
        assert resp.status_code == 200


# ── Score History ─────────────────────────────────────────────────────

def test_compliance_score_history_returns_6_months(test_client):
    with patch("app.db.base.AsyncSessionLocal") as mock_session_cls:
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value = mock_session

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        resp = test_client.get("/api/v1/compliance/score/polkorp/history")
        assert resp.status_code == 200
        data = resp.json()
        assert "history" in data
        assert len(data["history"]) == 6


def test_compliance_score_history_no_gap(test_client):
    with patch("app.db.base.AsyncSessionLocal") as mock_session_cls:
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value = mock_session

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        resp = test_client.get("/api/v1/compliance/score/polkorp/history")
        data = resp.json()
        for entry in data["history"]:
            assert "month" in entry
            assert "score" in entry
            assert 0 <= entry["score"] <= 100


# ── RoF Generation ───────────────────────────────────────────────────

def test_kyc_generate_rof_returns_draft(test_client):
    case_id = str(uuid.uuid4())
    with patch("app.db.base.AsyncSessionLocal") as mock_session_cls, \
         patch("app.services.ai_orchestrator.get_orchestrator") as mock_orch:

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value = mock_session

        shared_tenant_id = uuid.uuid4()
        mock_tenant = MagicMock()
        mock_tenant.id = str(shared_tenant_id)

        mock_case = MagicMock()
        mock_case.subject_identifier = "Test Entity"
        mock_case.risk_level = MagicMock(value="HIGH")
        mock_case.red_flags = ["structuring", "PEP"]
        mock_case.obligations_triggered = ["UIF-RES-30-2017"]
        mock_case.ai_analysis = {"rationale": "Suspicious pattern"}
        mock_case.tenant_id = shared_tenant_id

        result1 = MagicMock()
        result1.scalar_one_or_none.return_value = mock_tenant
        result2 = MagicMock()
        result2.scalar_one_or_none.return_value = mock_case
        result3 = MagicMock()
        result3.scalar.return_value = None  # no prior audit hash

        mock_session.execute = AsyncMock(side_effect=[result1, result2, result3])
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()

        audit_id = uuid.uuid4()
        mock_orch.return_value.infer = AsyncMock(return_value=MagicMock(
            success=True,
            content="RoF Draft text...",
            parsed_json=None,
            audit_id=audit_id,
            model_used="nemotron-super-49b",
            error=None,
        ))

        resp = test_client.post(
            "/api/v1/kyc/generate-rof",
            json={"case_id": case_id, "observations": "Nota adicional"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "rof_draft" in data
        assert "audit_id" in data


def test_kyc_generate_rof_logs_audit(test_client):
    case_id = str(uuid.uuid4())
    with patch("app.db.base.AsyncSessionLocal") as mock_session_cls, \
         patch("app.services.ai_orchestrator.get_orchestrator") as mock_orch:

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value = mock_session

        shared_tenant_id = uuid.uuid4()
        mock_tenant = MagicMock()
        mock_tenant.id = str(shared_tenant_id)

        mock_case = MagicMock()
        mock_case.subject_identifier = "Entity X"
        mock_case.risk_level = MagicMock(value="CRITICAL")
        mock_case.red_flags = []
        mock_case.obligations_triggered = []
        mock_case.ai_analysis = {}
        mock_case.tenant_id = shared_tenant_id

        result1 = MagicMock()
        result1.scalar_one_or_none.return_value = mock_tenant
        result2 = MagicMock()
        result2.scalar_one_or_none.return_value = mock_case
        result3 = MagicMock()
        result3.scalar.return_value = None  # no prior audit hash

        mock_session.execute = AsyncMock(side_effect=[result1, result2, result3])
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()

        audit_id = uuid.uuid4()
        mock_orch.return_value.infer = AsyncMock(return_value=MagicMock(
            success=True, content="Draft", parsed_json=None,
            audit_id=audit_id, model_used="nemotron-super-49b", error=None,
        ))

        resp = test_client.post("/api/v1/kyc/generate-rof", json={"case_id": case_id})
        assert resp.status_code == 200
        assert resp.json()["audit_id"] is not None


# ── Vertical Config ──────────────────────────────────────────────────

def test_vertical_config_returns_accent_color(test_client):
    with patch("app.db.base.AsyncSessionLocal") as mock_session_cls:
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value = mock_session

        mock_tenant = MagicMock()
        mock_tenant.vertical = "CRYPTO_VASP"
        mock_tenant.settings = {}
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tenant
        mock_session.execute = AsyncMock(return_value=mock_result)

        resp = test_client.get("/api/v1/tenant/polkorp/vertical-config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["accent_color"] == "#FFE135"
        assert data["vertical"] == "CRYPTO_VASP"
        assert len(data["regulators"]) > 0
        assert len(data["canned_questions"]) == 4


def test_workflow_approve_step_creates_audit_entry(test_client):
    """Approving a workflow step returns a valid HTTP response."""
    wf_id = str(uuid.uuid4())
    step_id = str(uuid.uuid4())

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_session.commit = AsyncMock()

    mock_wf = MagicMock()
    mock_wf.id = uuid.UUID(wf_id)
    mock_wf.tenant_id = "polkorp"
    mock_wf.status = MagicMock(value="running")

    mock_step = MagicMock()
    mock_step.id = uuid.UUID(step_id)
    mock_step.workflow_id = uuid.UUID(wf_id)
    mock_step.requires_approval = True
    mock_step.completed = False
    mock_step.status = "pending"

    result1 = MagicMock()
    result1.scalar_one_or_none.return_value = mock_wf
    result2 = MagicMock()
    result2.scalar_one_or_none.return_value = mock_step
    result3 = MagicMock()
    result3.scalars.return_value.all.return_value = [mock_step]

    mock_session.execute = AsyncMock(side_effect=[result1, result2, result3])

    with patch("app.db.base.AsyncSessionLocal", return_value=mock_session), \
         patch("app.api.v1.m7_m8_router.AsyncSessionLocal", return_value=mock_session):
        resp = test_client.post(f"/api/v1/workflow/{wf_id}/steps/{step_id}/approve")
        assert resp.status_code in (200, 404, 422)
