"""Tests for Sprint 5 multi-vertical support."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch


# ── Accent colors ─────────────────────────────────────────────────────

def test_accent_color_correct_per_vertical(test_client):
    """Each vertical has the correct accent color."""
    expected = {
        "FINTECH":         "#4A9FD4",
        "CRYPTO_VASP":     "#FFE135",
        "INSURANCE":       "#10B981",
        "HEALTH_PHARMA":   "#EF4444",
        "GAMING":          "#8B5CF6",
        "CAPITAL_MARKETS": "#F59E0B",
        "TELECOM":         "#06B6D4",
    }
    for vertical, color in expected.items():
        with patch("app.db.base.AsyncSessionLocal") as mock_session_cls:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_session_cls.return_value = mock_session

            mock_tenant = MagicMock()
            mock_tenant.vertical = vertical
            mock_tenant.settings = {}
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_tenant
            mock_session.execute = AsyncMock(return_value=mock_result)

            resp = test_client.get("/api/v1/tenant/polkorp/vertical-config")
            assert resp.status_code == 200
            assert resp.json()["accent_color"] == color, f"Wrong color for {vertical}"


def test_canned_questions_differ_per_vertical(test_client):
    """Each vertical returns different canned questions."""
    verticals = ["FINTECH", "CRYPTO_VASP", "INSURANCE", "HEALTH_PHARMA"]
    question_sets = []
    for v in verticals:
        resp = test_client.get(f"/api/v1/copilot/canned-questions?vertical={v}")
        question_sets.append(tuple(resp.json()["questions"]))
    assert len(set(question_sets)) == len(verticals)


def test_copilot_system_prompt_changes_per_vertical():
    """VERTICAL_SYSTEM_PROMPTS contains all 7 verticals with non-trivial prompts."""
    from app.services.ai_orchestrator import VERTICAL_SYSTEM_PROMPTS
    expected = {"FINTECH", "CRYPTO_VASP", "INSURANCE", "HEALTH_PHARMA", "GAMING", "CAPITAL_MARKETS", "TELECOM"}
    assert set(VERTICAL_SYSTEM_PROMPTS.keys()) == expected
    for v, prompt in VERTICAL_SYSTEM_PROMPTS.items():
        assert len(prompt) > 100, f"Prompt for {v} is too short"


def test_vertical_column_exists_in_model():
    """Tenant model has vertical column."""
    from app.db.models import Tenant
    from sqlalchemy import inspect as sa_inspect
    cols = {c.key for c in sa_inspect(Tenant).mapper.column_attrs}
    assert "vertical" in cols


def test_vertical_obligation_types_model_exists():
    """VerticalObligationType model is importable and correctly named."""
    from app.db.models import VerticalObligationType
    assert VerticalObligationType.__tablename__ == "vertical_obligation_types"


def test_vertical_regulators_model_exists():
    """VerticalRegulator model is importable and correctly named."""
    from app.db.models import VerticalRegulator
    assert VerticalRegulator.__tablename__ == "vertical_regulators"
