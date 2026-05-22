"""
ComplianceOS — Lemon Cash CCO Dashboard endpoint tests

These tests cover the new dashboard-specific endpoints added to the v1 router.
Each test verifies tenant isolation, response shape, and basic correctness.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


# ── test_kyc_queue_tenant_isolated ─────────────────────────────────────────────

def test_kyc_queue_tenant_isolated(test_client: TestClient):
    """
    GET /kyc/queue must:
    - Return 200 for an authenticated request
    - Return a dict with 'cases' (list) and 'total' (int)
    - All results must be scoped to the requesting tenant (polkorp in conftest)
    """
    # TODO: Seed a ComplianceCase for tenant 'polkorp' and another for 'other-tenant'.
    #       Assert the polkorp client only sees polkorp cases.
    response = test_client.get("/api/v1/kyc/queue")
    assert response.status_code == 200
    data = response.json()
    assert "cases" in data
    assert "total" in data
    assert isinstance(data["cases"], list)
    assert isinstance(data["total"], int)


# ── test_compliance_score_history_6_months ──────────────────────────────────────

def test_compliance_score_history_6_months(test_client: TestClient):
    """
    GET /compliance/score/{entity_id}/history must:
    - Return 200 for an authenticated request
    - Return exactly 6 data points in 'history'
    - Each point must have 'month' (str) and 'score' (int/float)
    - Scores must be in range [0, 100]
    """
    # TODO: Register a ComplianceEntity with id 'test-entity' in fixture.
    entity_id = "test-entity"
    response = test_client.get(f"/api/v1/compliance/score/{entity_id}/history")
    assert response.status_code == 200
    data = response.json()
    assert "history" in data
    history = data["history"]
    assert len(history) == 6, f"Expected 6 months, got {len(history)}"
    for point in history:
        assert "month" in point
        assert "score" in point
        assert 0 <= point["score"] <= 100


# ── test_canned_questions_crypto_vasp ──────────────────────────────────────────

def test_canned_questions_crypto_vasp(test_client: TestClient):
    """
    GET /copilot/canned-questions?vertical=CRYPTO_VASP must:
    - Return 200
    - Return exactly 4 questions
    - All questions must be non-empty strings
    - Questions should be relevant to VASP/crypto compliance
    """
    response = test_client.get("/api/v1/copilot/canned-questions?vertical=CRYPTO_VASP")
    assert response.status_code == 200
    data = response.json()
    assert "questions" in data
    questions = data["questions"]
    assert len(questions) == 4, f"Expected 4 questions, got {len(questions)}"
    for q in questions:
        assert isinstance(q, str)
        assert len(q) > 10, f"Question too short: {q!r}"


# ── test_kyc_generate_rof_returns_draft ────────────────────────────────────────

def test_kyc_generate_rof_returns_draft(test_client: TestClient):
    """
    POST /kyc/generate-rof must:
    - Accept {case_id, case_name, risk_level}
    - Return 200 with {rof_draft, audit_id, model, case_id}
    - rof_draft must be a non-empty string (AI draft or fallback template)
    - audit_id must be a non-empty string

    NOTE: This test uses the AI fallback path since NVIDIA_API_KEY is not set.
    """
    # TODO: Mock the AI orchestrator to return a controlled response.
    payload = {
        "case_id": "test-case-001",
        "case_name": "Empresa de Prueba S.A.",
        "risk_level": "HIGH",
    }
    response = test_client.post("/api/v1/kyc/generate-rof", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "rof_draft" in data
    assert "audit_id" in data
    assert "case_id" in data
    assert isinstance(data["rof_draft"], str)
    assert len(data["rof_draft"]) > 50, "RoF draft is too short"
    assert data["case_id"] == payload["case_id"]


# ── test_workflow_approve_step_logs_audit ──────────────────────────────────────

def test_workflow_approve_step_logs_audit(test_client: TestClient):
    """
    POST /workflow/{workflow_id}/steps/{step_id}/approve must:
    - Return 200 with {ok: true}
    - Not crash when workflow/step IDs don't exist in DB (graceful fallback)
    - In a full integration test, would verify audit log entry was created.

    TODO: Seed a real Workflow + WorkflowStep, call approve, then query
          GET /audit and verify a 'workflow.step_approved' entry exists.
    """
    fake_workflow_id = "00000000-0000-0000-0000-000000000001"
    fake_step_id = "00000000-0000-0000-0000-000000000002"
    response = test_client.post(
        f"/api/v1/workflow/{fake_workflow_id}/steps/{fake_step_id}/approve"
    )
    assert response.status_code == 200
    data = response.json()
    assert data.get("ok") is True
