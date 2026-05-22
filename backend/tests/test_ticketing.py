"""
Tests for M9 Ticketing Compliance Module

Covers:
- Risk scoring engine: all 10 dimensions
- BLOCKED launch logic: hard blockers
- APPROVED_WITH_CONDITIONS logic
- Country-specific rules (Argentina botón de arrepentimiento)
- High-risk feature triggers (crypto, resale, wallets)
"""

from __future__ import annotations

import pytest

from app.modules.ticketing.engine import TicketingRiskEngine, get_risk_engine, DIMENSION_WEIGHTS


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def engine() -> TicketingRiskEngine:
    return TicketingRiskEngine()


def _fully_compliant_event(country: str = "AR") -> dict:
    """A fully-compliant event — should be APPROVED with low risk score."""
    return {
        "country_code": country,
        "has_promoter_agreement": True,
        "has_refund_policy": True,
        "has_consumer_terms": True,
        "has_payment_processor": True,
        "has_privacy_policy": True,
        "has_withdrawal_button": True,
        "has_cancellation_clause": True,
        "has_postponement_clause": True,
        "has_marketing_consent": True,
        "has_anti_bot_protection": True,
        "has_electronic_invoice": True,
        "has_aaip_registration": True,
        "has_venue_authorization": True,
        "has_event_permit": True,
        "has_chargeback_evidence": True,
        "resale_enabled": False,
        "has_resale_policy": False,
        "crypto_payments_enabled": False,
        "has_aml_kyc_controls": False,
        "wallet_balance_enabled": False,
        "service_fee_pct": 10.0,
        "service_fee_fixed": 0.0,
        "taxes_included": True,
        "refund_sla_days": 10,
        "complaint_sla_days": 15,
        "additional_countries": [],
    }


def _bare_minimum_event(country: str = "AR") -> dict:
    """An event with NO compliance controls — worst case."""
    return {
        "country_code": country,
        "has_promoter_agreement": False,
        "has_refund_policy": False,
        "has_consumer_terms": False,
        "has_payment_processor": False,
        "has_privacy_policy": False,
        "has_withdrawal_button": False,
        "has_cancellation_clause": False,
        "has_postponement_clause": False,
        "has_marketing_consent": False,
        "has_anti_bot_protection": False,
        "has_electronic_invoice": False,
        "has_aaip_registration": False,
        "has_venue_authorization": False,
        "has_event_permit": False,
        "has_chargeback_evidence": False,
        "resale_enabled": False,
        "has_resale_policy": False,
        "crypto_payments_enabled": False,
        "has_aml_kyc_controls": False,
        "wallet_balance_enabled": False,
        "service_fee_pct": 0.0,
        "service_fee_fixed": 0.0,
        "taxes_included": True,
        "refund_sla_days": 10,
        "complaint_sla_days": 15,
        "additional_countries": [],
    }


# ─── Dimension weight validation ──────────────────────────────────────────────

def test_dimension_weights_sum_to_one():
    total = sum(DIMENSION_WEIGHTS.values())
    assert abs(total - 1.0) < 1e-9, f"Weights sum to {total}, expected 1.0"


def test_all_ten_dimensions_present():
    expected = {
        "consumer_risk", "refund_risk", "resale_risk", "payment_risk",
        "data_privacy_risk", "tax_risk", "contractual_risk",
        "fraud_aml_risk", "operational_risk", "country_enforcement_risk",
    }
    assert set(DIMENSION_WEIGHTS.keys()) == expected


# ─── BLOCKED logic ────────────────────────────────────────────────────────────

def test_blocked_no_promoter_agreement(engine):
    event = _fully_compliant_event()
    event["has_promoter_agreement"] = False
    result = engine.score_event(event)
    assert result.launch_decision == "BLOCKED"
    assert any("promoter" in r.lower() for r in result.blocking_reasons)


def test_blocked_no_refund_policy(engine):
    event = _fully_compliant_event()
    event["has_refund_policy"] = False
    result = engine.score_event(event)
    assert result.launch_decision == "BLOCKED"
    assert any("refund" in r.lower() or "cancel" in r.lower() for r in result.blocking_reasons)


def test_blocked_no_consumer_terms(engine):
    event = _fully_compliant_event()
    event["has_consumer_terms"] = False
    result = engine.score_event(event)
    assert result.launch_decision == "BLOCKED"
    assert any("terms" in r.lower() or "consumer" in r.lower() for r in result.blocking_reasons)


def test_blocked_no_payment_processor(engine):
    event = _fully_compliant_event()
    event["has_payment_processor"] = False
    result = engine.score_event(event)
    assert result.launch_decision == "BLOCKED"
    assert any("payment" in r.lower() for r in result.blocking_reasons)


def test_blocked_argentina_no_boton_arrepentimiento(engine):
    """Argentina-specific: missing withdrawal button must BLOCK."""
    event = _fully_compliant_event(country="AR")
    event["has_withdrawal_button"] = False
    result = engine.score_event(event)
    assert result.launch_decision == "BLOCKED"
    assert any("arrepentimiento" in r.lower() or "withdrawal" in r.lower() for r in result.blocking_reasons)


def test_not_blocked_non_ar_no_withdrawal_button(engine):
    """Brazil does not mandate botón de arrepentimiento — no block."""
    event = _fully_compliant_event(country="BR")
    event["has_withdrawal_button"] = False
    result = engine.score_event(event)
    # Should NOT be blocked just for missing withdrawal button in BR
    withdrawal_blocks = [r for r in result.blocking_reasons if "arrepentimiento" in r.lower()]
    assert len(withdrawal_blocks) == 0, "BR should not be blocked for missing withdrawal button"


def test_blocked_resale_enabled_no_resale_policy(engine):
    event = _fully_compliant_event()
    event["resale_enabled"] = True
    event["has_resale_policy"] = False
    result = engine.score_event(event)
    assert result.launch_decision == "BLOCKED"
    assert any("resale" in r.lower() for r in result.blocking_reasons)


def test_blocked_crypto_no_aml_controls(engine):
    event = _fully_compliant_event()
    event["crypto_payments_enabled"] = True
    event["has_aml_kyc_controls"] = False
    result = engine.score_event(event)
    assert result.launch_decision == "BLOCKED"
    assert any("crypto" in r.lower() or "aml" in r.lower() for r in result.blocking_reasons)


def test_bare_minimum_event_is_blocked(engine):
    """An event with no compliance controls must be BLOCKED."""
    event = _bare_minimum_event()
    result = engine.score_event(event)
    assert result.launch_decision == "BLOCKED"
    assert len(result.blocking_reasons) >= 4, "Expected at least 4 blockers for bare minimum event"


# ─── APPROVED logic ───────────────────────────────────────────────────────────

def test_fully_compliant_event_approved(engine):
    """A fully-compliant event should be APPROVED."""
    event = _fully_compliant_event()
    result = engine.score_event(event)
    assert result.launch_decision == "APPROVED", (
        f"Expected APPROVED, got {result.launch_decision}. Score: {result.overall_score}. "
        f"Blockers: {result.blocking_reasons}"
    )
    assert result.overall_score < 60, (
        f"Risk score {result.overall_score} too high for fully-compliant event"
    )


def test_approved_no_blockers(engine):
    """APPROVED requires zero blocking reasons."""
    event = _fully_compliant_event()
    result = engine.score_event(event)
    assert result.blocking_reasons == [], f"Unexpected blockers: {result.blocking_reasons}"


# ─── Risk score ranges ────────────────────────────────────────────────────────

def test_overall_score_in_range(engine):
    for event in [_fully_compliant_event(), _bare_minimum_event()]:
        result = engine.score_event(event)
        assert 0 <= result.overall_score <= 100, f"Score {result.overall_score} out of range"


def test_dimension_scores_in_range(engine):
    for event in [_fully_compliant_event(), _bare_minimum_event()]:
        result = engine.score_event(event)
        for dim, score in result.dimensions.items():
            assert 0 <= score <= 100, f"Dimension {dim} score {score} out of range"


def test_all_dimensions_present_in_result(engine):
    result = engine.score_event(_fully_compliant_event())
    expected_dims = set(DIMENSION_WEIGHTS.keys())
    assert set(result.dimensions.keys()) == expected_dims


# ─── High-risk triggers ───────────────────────────────────────────────────────

def test_open_resale_marketplace_elevates_resale_risk(engine):
    compliant = _fully_compliant_event()
    compliant["resale_enabled"] = True
    compliant["resale_type"] = "marketplace"
    compliant["has_resale_policy"] = True

    baseline = engine.score_event(_fully_compliant_event())
    with_resale = engine.score_event(compliant)

    assert with_resale.dimensions["resale_risk"] > baseline.dimensions["resale_risk"]


def test_wallet_balance_elevates_payment_risk(engine):
    event = _fully_compliant_event()
    event["wallet_balance_enabled"] = True

    baseline = engine.score_event(_fully_compliant_event())
    with_wallet = engine.score_event(event)

    assert with_wallet.dimensions["payment_risk"] >= baseline.dimensions["payment_risk"]


def test_crypto_payments_elevates_fraud_risk(engine):
    event = _fully_compliant_event()
    event["crypto_payments_enabled"] = True
    event["has_aml_kyc_controls"] = True  # avoid blocker

    baseline = engine.score_event(_fully_compliant_event())
    with_crypto = engine.score_event(event)

    assert with_crypto.dimensions["fraud_aml_risk"] > baseline.dimensions["fraud_aml_risk"]


def test_no_privacy_policy_elevates_data_privacy_risk(engine):
    event = _fully_compliant_event()
    event["has_privacy_policy"] = False

    baseline = engine.score_event(_fully_compliant_event())
    no_privacy = engine.score_event(event)

    assert no_privacy.dimensions["data_privacy_risk"] > baseline.dimensions["data_privacy_risk"]


# ─── Missing controls ─────────────────────────────────────────────────────────

def test_missing_controls_listed_for_bare_minimum(engine):
    result = engine.score_event(_bare_minimum_event())
    assert len(result.missing_controls) > 5, "Expected many missing controls for bare minimum event"


def test_no_missing_controls_for_compliant_event(engine):
    result = engine.score_event(_fully_compliant_event())
    # A fully-compliant event should have no or very few missing controls
    assert len(result.missing_controls) <= 2, (
        f"Unexpected missing controls: {result.missing_controls}"
    )


# ─── Recommendations ──────────────────────────────────────────────────────────

def test_recommendations_present_for_blocked_event(engine):
    event = _bare_minimum_event()
    result = engine.score_event(event)
    assert len(result.recommendations) > 0


def test_to_dict_structure(engine):
    result = engine.score_event(_fully_compliant_event())
    d = result.to_dict()
    assert "overall_score" in d
    assert "launch_decision" in d
    assert "dimensions" in d
    assert "blocking_reasons" in d
    assert "high_risk_triggers" in d
    assert "missing_controls" in d
    assert "recommendations" in d


# ─── Singleton ───────────────────────────────────────────────────────────────

def test_get_risk_engine_singleton():
    e1 = get_risk_engine()
    e2 = get_risk_engine()
    assert e1 is e2


# ─── Country enforcement risk ─────────────────────────────────────────────────

def test_argentina_higher_enforcement_than_paraguay(engine):
    ar = _fully_compliant_event(country="AR")
    py = _fully_compliant_event(country="PY")
    # Both fully compliant, but AR should have higher country enforcement risk
    ar_result = engine.score_event(ar)
    py_result = engine.score_event(py)
    assert ar_result.dimensions["country_enforcement_risk"] > py_result.dimensions["country_enforcement_risk"]


# ─── Multiple blockers ────────────────────────────────────────────────────────

def test_multiple_blockers_all_listed(engine):
    event = _bare_minimum_event(country="AR")
    result = engine.score_event(event)
    # AR bare minimum should have: no promoter, no refund, no terms, no payment, no withdrawal
    assert len(result.blocking_reasons) >= 5


def test_resale_without_policy_and_crypto_without_aml(engine):
    """Two independent blockers should both appear."""
    event = _fully_compliant_event()
    event["resale_enabled"] = True
    event["has_resale_policy"] = False
    event["crypto_payments_enabled"] = True
    event["has_aml_kyc_controls"] = False
    result = engine.score_event(event)
    assert result.launch_decision == "BLOCKED"
    assert len(result.blocking_reasons) >= 2
