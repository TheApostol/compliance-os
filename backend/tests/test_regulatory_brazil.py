"""
T-BR — M1 Regulatory Intelligence: Brazil-specific tests.

Tests country-aware system prompts and BR obligation type normalization.
No real AI calls are made — the orchestrator is mocked throughout.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.regulatory.engine import (
    BR_OBLIGATION_TYPE_MAP,
    RegulatoryIntelligence,
    _normalize_br_obligation_types,
)


# ── 1. _build_system_prompt: Brazil ──────────────────────────────────────────


def test_build_system_prompt_brazil():
    prompt = RegulatoryIntelligence._build_system_prompt("BR", "BACEN")
    assert "Banco Central do Brasil" in prompt
    assert "Portuguese" in prompt


def test_build_system_prompt_brazil_lowercase():
    """Country code should be case-insensitive."""
    prompt = RegulatoryIntelligence._build_system_prompt("br", "BACEN")
    assert "Banco Central do Brasil" in prompt


# ── 2. _build_system_prompt: Argentina ───────────────────────────────────────


def test_build_system_prompt_argentina():
    prompt = RegulatoryIntelligence._build_system_prompt("AR", "BCRA")
    assert "BCRA" in prompt
    assert "Argentina" in prompt


def test_build_system_prompt_argentina_lowercase():
    prompt = RegulatoryIntelligence._build_system_prompt("ar", "BCRA")
    assert "BCRA" in prompt


# ── 3. _build_system_prompt: Generic / other countries ───────────────────────


def test_build_system_prompt_generic():
    prompt = RegulatoryIntelligence._build_system_prompt("US", "SEC")
    assert "international" in prompt.lower()


def test_build_system_prompt_generic_mx():
    prompt = RegulatoryIntelligence._build_system_prompt("MX", "CNBV")
    assert "international" in prompt.lower()


# ── 4. BR obligation type normalization ──────────────────────────────────────


class TestBrObligationTypeNormalization:
    def test_prazo_maps_to_deadline(self):
        obligations = [{"obligation_type": "prazo", "description": "30-day deadline"}]
        result = _normalize_br_obligation_types(obligations)
        assert result[0]["obligation_type"] == "deadline"

    def test_obrigatoriedade_maps_to_requirement(self):
        obligations = [{"obligation_type": "obrigatoriedade", "description": "mandatory KYC"}]
        result = _normalize_br_obligation_types(obligations)
        assert result[0]["obligation_type"] == "requirement"

    def test_vedacao_maps_to_prohibition(self):
        obligations = [{"obligation_type": "vedacao", "description": "prohibited activity"}]
        result = _normalize_br_obligation_types(obligations)
        assert result[0]["obligation_type"] == "prohibition"

    def test_vedacao_with_cedilla_maps_to_prohibition(self):
        obligations = [{"obligation_type": "vedação", "description": "prohibited"}]
        result = _normalize_br_obligation_types(obligations)
        assert result[0]["obligation_type"] == "prohibition"

    def test_restricao_maps_to_restriction(self):
        obligations = [{"obligation_type": "restricao", "description": "restricted"}]
        result = _normalize_br_obligation_types(obligations)
        assert result[0]["obligation_type"] == "restriction"

    def test_restricao_with_cedilla_maps_to_restriction(self):
        obligations = [{"obligation_type": "restrição", "description": "restricted"}]
        result = _normalize_br_obligation_types(obligations)
        assert result[0]["obligation_type"] == "restriction"

    def test_comunicacao_maps_to_reporting(self):
        obligations = [{"obligation_type": "comunicacao", "description": "report to COAF"}]
        result = _normalize_br_obligation_types(obligations)
        assert result[0]["obligation_type"] == "reporting"

    def test_comunicacao_with_cedilla_maps_to_reporting(self):
        obligations = [{"obligation_type": "comunicação", "description": "report"}]
        result = _normalize_br_obligation_types(obligations)
        assert result[0]["obligation_type"] == "reporting"

    def test_registro_maps_to_registration(self):
        obligations = [{"obligation_type": "registro", "description": "register entity"}]
        result = _normalize_br_obligation_types(obligations)
        assert result[0]["obligation_type"] == "registration"

    def test_limite_maps_to_limit(self):
        obligations = [{"obligation_type": "limite", "description": "transaction limit"}]
        result = _normalize_br_obligation_types(obligations)
        assert result[0]["obligation_type"] == "limit"

    def test_unknown_type_unchanged(self):
        """Non-Portuguese types that are already canonical must pass through unchanged."""
        obligations = [{"obligation_type": "REPORTING", "description": "report"}]
        result = _normalize_br_obligation_types(obligations)
        assert result[0]["obligation_type"] == "REPORTING"

    def test_does_not_mutate_original_list(self):
        original = [{"obligation_type": "prazo", "description": "deadline"}]
        _normalize_br_obligation_types(original)
        assert original[0]["obligation_type"] == "prazo"

    def test_multiple_obligations(self):
        obligations = [
            {"obligation_type": "prazo", "description": "d1"},
            {"obligation_type": "vedacao", "description": "d2"},
            {"obligation_type": "REPORTING", "description": "d3"},
        ]
        result = _normalize_br_obligation_types(obligations)
        assert result[0]["obligation_type"] == "deadline"
        assert result[1]["obligation_type"] == "prohibition"
        assert result[2]["obligation_type"] == "REPORTING"

    def test_br_obligation_type_map_completeness(self):
        """Smoke-test: all keys in BR_OBLIGATION_TYPE_MAP map to non-empty strings."""
        for key, value in BR_OBLIGATION_TYPE_MAP.items():
            assert isinstance(value, str) and value, f"Empty mapping for key '{key}'"

    def test_mock_m1_returns_prazo_stored_as_deadline(self):
        """
        Simulate M1 returning obligation_type='prazo' for country='BR'.
        After normalization the stored type should be 'deadline'.
        """
        raw = [{"obligation_type": "prazo", "description": "Prazo de 30 dias para envio"}]
        normalized = _normalize_br_obligation_types(raw)
        assert normalized[0]["obligation_type"] == "deadline"
        assert normalized[0]["description"] == "Prazo de 30 dias para envio"


# ── 5. parse_regulation uses BR-specific system prompt ───────────────────────


@pytest.mark.asyncio
async def test_br_parse_regulation_uses_br_prompt():
    """
    When parse_regulation(country='BR', ...) is called, the InferenceRequest
    passed to the orchestrator must contain the BR-specific system prompt text.
    """
    from app.services.ai_orchestrator import InferenceRequest

    captured: list[InferenceRequest] = []

    # Build a fake successful InferenceResult
    mock_result = MagicMock()
    mock_result.success = True
    mock_result.parsed_json = {
        "regulation_summary": "Test BACEN regulation.",
        "obligations": [],
    }
    mock_result.model_used = "llama-3.3-70b"
    mock_result.audit_id = "abcd1234"
    mock_result.latency_total_ms = 500
    mock_result.error = None

    async def _fake_infer(req: InferenceRequest):
        captured.append(req)
        return mock_result

    mock_orch = MagicMock()
    mock_orch.infer = _fake_infer

    engine = RegulatoryIntelligence(orchestrator=mock_orch)

    await engine.parse_regulation(
        country="BR",
        regulator="BACEN",
        code="CIRC-3950",
        title="Test Circular",
        text="Texto regulatório de teste.",
        tenant_id="polkorp",
        user_id="test-user",
    )

    assert len(captured) == 1
    req = captured[0]
    assert "Banco Central do Brasil" in req.system
    assert "Portuguese" in req.system


@pytest.mark.asyncio
async def test_ar_parse_regulation_uses_ar_prompt():
    """
    When parse_regulation(country='AR', ...) is called, the system prompt
    must contain BCRA and Argentina.
    """
    from app.services.ai_orchestrator import InferenceRequest

    captured: list[InferenceRequest] = []

    mock_result = MagicMock()
    mock_result.success = True
    mock_result.parsed_json = {
        "regulation_summary": "BCRA regulation.",
        "obligations": [],
    }
    mock_result.model_used = "llama-3.3-70b"
    mock_result.audit_id = "abcd5678"
    mock_result.latency_total_ms = 400
    mock_result.error = None

    async def _fake_infer(req: InferenceRequest):
        captured.append(req)
        return mock_result

    mock_orch = MagicMock()
    mock_orch.infer = _fake_infer

    engine = RegulatoryIntelligence(orchestrator=mock_orch)

    await engine.parse_regulation(
        country="AR",
        regulator="BCRA",
        code="COM-A-7825",
        title="Test Comunicación",
        text="Texto regulatorio de prueba.",
        tenant_id="polkorp",
        user_id="test-user",
    )

    assert len(captured) == 1
    req = captured[0]
    assert "BCRA" in req.system
    assert "Argentina" in req.system


@pytest.mark.asyncio
async def test_generic_parse_regulation_uses_generic_prompt():
    """
    For country='US', the system prompt must contain 'international'.
    """
    from app.services.ai_orchestrator import InferenceRequest

    captured: list[InferenceRequest] = []

    mock_result = MagicMock()
    mock_result.success = True
    mock_result.parsed_json = {
        "regulation_summary": "SEC regulation.",
        "obligations": [],
    }
    mock_result.model_used = "llama-3.3-70b"
    mock_result.audit_id = "abcd9012"
    mock_result.latency_total_ms = 350
    mock_result.error = None

    async def _fake_infer(req: InferenceRequest):
        captured.append(req)
        return mock_result

    mock_orch = MagicMock()
    mock_orch.infer = _fake_infer

    engine = RegulatoryIntelligence(orchestrator=mock_orch)

    await engine.parse_regulation(
        country="US",
        regulator="SEC",
        code="REG-S-K",
        title="SEC Regulation",
        text="Regulatory text.",
        tenant_id="polkorp",
        user_id="test-user",
    )

    assert len(captured) == 1
    req = captured[0]
    assert "international" in req.system.lower()
