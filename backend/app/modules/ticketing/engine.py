"""
ComplianceOS — Ticketing Compliance Risk Scoring Engine (M9)

Deterministic multi-dimensional risk scoring for ticketing events.
Computes scores across 10 risk dimensions and produces a launch decision:
  APPROVED | APPROVED_WITH_CONDITIONS | BLOCKED

BLOCKED is mandatory when any of the defined hard blockers are missing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ═══════════════════════════════════════════════════════════════════
# RISK DIMENSION WEIGHTS  (must sum to 1.0)
# ═══════════════════════════════════════════════════════════════════

DIMENSION_WEIGHTS: dict[str, float] = {
    "consumer_risk":            0.15,
    "refund_risk":              0.15,
    "resale_risk":              0.10,
    "payment_risk":             0.12,
    "data_privacy_risk":        0.10,
    "tax_risk":                 0.08,
    "contractual_risk":         0.12,
    "fraud_aml_risk":           0.08,
    "operational_risk":         0.05,
    "country_enforcement_risk": 0.05,
}

# Country base enforcement risk scores (0-100)
COUNTRY_ENFORCEMENT_RISK: dict[str, int] = {
    "AR": 75,  # High — active AFIP/AAIP enforcement
    "BR": 65,  # High — PROCON/ANPD
    "MX": 55,  # Medium-High — PROFECO
    "CO": 50,  # Medium — SIC
    "CL": 45,  # Medium — SERNAC
    "PE": 60,  # Medium-High — INDECOPI
    "UY": 40,  # Medium — URSEC/AUCAP
    "PY": 35,  # Medium-Low — SEDECO
}


@dataclass
class RiskAssessmentResult:
    overall_score: int
    launch_decision: str  # APPROVED | APPROVED_WITH_CONDITIONS | BLOCKED
    dimensions: dict[str, int] = field(default_factory=dict)
    blocking_reasons: list[str] = field(default_factory=list)
    high_risk_triggers: list[str] = field(default_factory=list)
    missing_controls: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_score": self.overall_score,
            "launch_decision": self.launch_decision,
            "dimensions": self.dimensions,
            "blocking_reasons": self.blocking_reasons,
            "high_risk_triggers": self.high_risk_triggers,
            "missing_controls": self.missing_controls,
            "recommendations": self.recommendations,
        }


class TicketingRiskEngine:
    """
    Deterministic risk scoring for ticketing events.

    Call score_event() with the event configuration dict.
    Returns a RiskAssessmentResult with dimension scores and launch decision.
    """

    # ── Hard blockers: if any of these conditions are True, event is BLOCKED ──

    def _check_blockers(self, event: dict) -> list[str]:
        """Return list of blocking reasons. Non-empty → BLOCKED."""
        blockers: list[str] = []
        country = event.get("country_code", "").upper()

        if not event.get("has_promoter_agreement"):
            blockers.append("Missing promoter agreement — contractual liability unallocated")

        if not event.get("has_refund_policy"):
            blockers.append("Missing refund/cancellation policy — mandatory under consumer protection law")

        if not event.get("has_consumer_terms"):
            blockers.append("Missing consumer terms & conditions before checkout")

        if not event.get("has_payment_processor"):
            blockers.append("No payment processor record — financial liability unverified")

        # Country-specific withdrawal button requirement
        if country in ("AR",) and not event.get("has_withdrawal_button"):
            blockers.append(
                "Botón de arrepentimiento not implemented — mandatory in Argentina (Res. 424/2020, Law 24.240)"
            )

        if event.get("resale_enabled") and not event.get("has_resale_policy"):
            blockers.append("Resale marketplace enabled but no resale policy defined")

        if event.get("crypto_payments_enabled") and not event.get("has_aml_kyc_controls"):
            blockers.append("Crypto payments enabled without AML/KYC controls — regulatory risk")

        return blockers

    # ── High-risk triggers: raise individual dimension scores ─────────────────

    def _detect_triggers(self, event: dict) -> list[str]:
        triggers: list[str] = []

        if event.get("resale_enabled") and event.get("resale_type") == "marketplace":
            triggers.append("Open resale marketplace — secondary market regulatory risk")

        if event.get("wallet_balance_enabled"):
            triggers.append("Stored wallet balances — PSP and AML regulatory obligations apply")

        if event.get("crypto_payments_enabled"):
            triggers.append("Crypto payments enabled — heightened AML/KYC and VASP requirements")

        if not event.get("has_refund_policy") or not event.get("has_withdrawal_button"):
            triggers.append("Refund automation incomplete — chargeback and consumer risk elevated")

        if not event.get("has_privacy_policy"):
            triggers.append("No privacy policy — data protection violation risk")

        if not event.get("has_marketing_consent"):
            triggers.append("No marketing consent mechanism — spam/privacy enforcement risk")

        if not event.get("has_promoter_agreement"):
            triggers.append("No promoter agreement — liability allocation gap")

        if not event.get("has_electronic_invoice"):
            triggers.append("No electronic invoice mapping — tax compliance gap")

        if not event.get("has_chargeback_evidence"):
            triggers.append("No chargeback evidence package — dispute resolution risk")

        if not event.get("has_anti_bot_protection"):
            triggers.append("No anti-bot protection — bulk purchase and scalping risk")

        additional = event.get("additional_countries", [])
        if additional and not event.get("has_consumer_terms"):
            triggers.append(
                f"Event spans {len(additional)+1} countries without country-specific terms"
            )

        return triggers

    # ── Dimension scoring ─────────────────────────────────────────────────────

    def _score_consumer_risk(self, event: dict) -> int:
        score = 0
        if not event.get("has_consumer_terms"):       score += 35
        if not event.get("has_withdrawal_button"):    score += 30
        if not event.get("has_refund_policy"):        score += 25
        if not event.get("has_cancellation_clause"):  score += 10
        return min(score, 100)

    def _score_refund_risk(self, event: dict) -> int:
        score = 0
        if not event.get("has_refund_policy"):        score += 40
        if not event.get("has_cancellation_clause"):  score += 20
        if not event.get("has_postponement_clause"):  score += 15
        sla = event.get("refund_sla_days", 10)
        if sla > 10:                                  score += 15
        if not event.get("has_chargeback_evidence"):  score += 10
        return min(score, 100)

    def _score_resale_risk(self, event: dict) -> int:
        if not event.get("resale_enabled"):
            return 10  # minimal risk when resale disabled

        score = 20  # base for enabling resale
        resale_type = event.get("resale_type", "")
        if resale_type == "marketplace":              score += 40
        elif resale_type == "controlled":             score += 15

        if not event.get("has_resale_policy"):        score += 30
        if not event.get("has_anti_bot_protection"):  score += 10
        return min(score, 100)

    def _score_payment_risk(self, event: dict) -> int:
        score = 0
        if not event.get("has_payment_processor"):    score += 40
        if event.get("crypto_payments_enabled"):      score += 25
        if event.get("wallet_balance_enabled"):       score += 20
        if not event.get("has_chargeback_evidence"):  score += 15
        return min(score, 100)

    def _score_data_privacy_risk(self, event: dict) -> int:
        score = 0
        if not event.get("has_privacy_policy"):       score += 45
        if not event.get("has_marketing_consent"):    score += 30
        if not event.get("has_aaip_registration"):
            country = event.get("country_code", "").upper()
            if country == "AR":                       score += 25
        return min(score, 100)

    def _score_tax_risk(self, event: dict) -> int:
        score = 0
        if not event.get("has_electronic_invoice"):   score += 60
        # service fee transparency
        svc_pct = event.get("service_fee_pct", 0)
        svc_fix = event.get("service_fee_fixed", 0)
        if (svc_pct > 0 or svc_fix > 0) and not event.get("taxes_included"):
            score += 20
        return min(score, 100)

    def _score_contractual_risk(self, event: dict) -> int:
        score = 0
        if not event.get("has_promoter_agreement"):   score += 50
        if not event.get("has_venue_authorization"):  score += 30
        if not event.get("has_event_permit"):         score += 20
        return min(score, 100)

    def _score_fraud_aml_risk(self, event: dict) -> int:
        score = 0
        if event.get("crypto_payments_enabled") and not event.get("has_aml_kyc_controls"):
            score += 50
        if event.get("wallet_balance_enabled"):       score += 25
        if not event.get("has_anti_bot_protection"):  score += 15
        if event.get("resale_enabled") and event.get("resale_type") == "marketplace":
            score += 10
        return min(score, 100)

    def _score_operational_risk(self, event: dict) -> int:
        score = 0
        if not event.get("has_cancellation_clause"):  score += 30
        if not event.get("has_postponement_clause"):  score += 30
        complaint_sla = event.get("complaint_sla_days", 15)
        if complaint_sla > 20:                        score += 20
        if not event.get("has_venue_authorization"):  score += 20
        return min(score, 100)

    def _score_country_enforcement_risk(self, event: dict) -> int:
        country = event.get("country_code", "").upper()
        base = COUNTRY_ENFORCEMENT_RISK.get(country, 50)

        # Reduce by implemented controls
        implemented = 0
        for flag in [
            "has_consumer_terms", "has_refund_policy", "has_withdrawal_button",
            "has_privacy_policy", "has_electronic_invoice",
        ]:
            if event.get(flag):
                implemented += 1

        reduction = implemented * 5
        return max(base - reduction, 10)

    # ── Missing controls ──────────────────────────────────────────────────────

    def _find_missing_controls(self, event: dict) -> list[str]:
        missing: list[str] = []
        checks = [
            ("has_consumer_terms",      "Consumer T&C before checkout"),
            ("has_refund_policy",       "Visible refund policy"),
            ("has_withdrawal_button",   "Botón de arrepentimiento / purchase withdrawal"),
            ("has_cancellation_clause", "Event cancellation clause"),
            ("has_postponement_clause", "Event postponement clause"),
            ("has_privacy_policy",      "Privacy policy / LPDP notice"),
            ("has_marketing_consent",   "Separate marketing consent"),
            ("has_promoter_agreement",  "Promoter compliance agreement"),
            ("has_venue_authorization", "Venue authorization"),
            ("has_event_permit",        "Event/public safety permit"),
            ("has_payment_processor",   "Payment processor documentation"),
            ("has_electronic_invoice",  "Electronic invoice / receipt issuance"),
            ("has_anti_bot_protection", "Anti-bot / bulk purchase protection"),
            ("has_chargeback_evidence", "Chargeback evidence package"),
        ]
        if event.get("country_code", "").upper() == "AR":
            checks.append(("has_aaip_registration", "AAIP database controller registration"))

        if event.get("resale_enabled"):
            checks.append(("has_resale_policy", "Ticket resale policy"))

        if event.get("crypto_payments_enabled"):
            checks.append(("has_aml_kyc_controls", "AML/KYC controls for crypto"))

        for flag, label in checks:
            if not event.get(flag):
                missing.append(label)

        return missing

    # ── Recommendations ───────────────────────────────────────────────────────

    def _build_recommendations(
        self,
        blocking_reasons: list[str],
        missing_controls: list[str],
        triggers: list[str],
        event: dict,
    ) -> list[str]:
        recs: list[str] = []

        if blocking_reasons:
            recs.append("URGENT: Resolve all blocking issues before proceeding with event launch")

        if not event.get("has_consumer_terms"):
            recs.append("Draft and publish consumer T&C compliant with Law 24.240 (AR) before checkout flow")

        if not event.get("has_withdrawal_button") and event.get("country_code", "").upper() == "AR":
            recs.append(
                "Implement visible Botón de Arrepentimiento on homepage and post-purchase page (Res. 424/2020)"
            )

        if not event.get("has_refund_policy"):
            recs.append("Define refund policy covering cancellation, postponement, and consumer withdrawal scenarios")

        if not event.get("has_promoter_agreement"):
            recs.append("Execute compliance schedule with promoter before event goes live")

        if not event.get("has_electronic_invoice"):
            recs.append("Configure AFIP/ARCA electronic invoice issuance for all ticket sales")

        if not event.get("has_privacy_policy"):
            recs.append("Publish privacy policy aligned with LPDP 25.326 and AAIP guidelines")

        if event.get("crypto_payments_enabled") and not event.get("has_aml_kyc_controls"):
            recs.append("Implement KYC/AML controls before enabling crypto payment gateway")

        if event.get("resale_enabled") and not event.get("has_resale_policy"):
            recs.append("Define resale policy covering price caps, transfer controls, and anti-scalping measures")

        if not event.get("has_anti_bot_protection"):
            recs.append("Deploy CAPTCHA, purchase rate limiting, and purchase quantity caps")

        return recs

    # ── Main scoring entry point ──────────────────────────────────────────────

    def score_event(self, event: dict) -> RiskAssessmentResult:
        """
        Score a ticketing event configuration and return a RiskAssessmentResult.

        Args:
            event: dict with compliance flags and event configuration.
                   Expected keys mirror TicketingEvent model columns.
        """
        blockers = self._check_blockers(event)
        triggers = self._detect_triggers(event)
        missing  = self._find_missing_controls(event)

        dimensions = {
            "consumer_risk":            self._score_consumer_risk(event),
            "refund_risk":              self._score_refund_risk(event),
            "resale_risk":              self._score_resale_risk(event),
            "payment_risk":             self._score_payment_risk(event),
            "data_privacy_risk":        self._score_data_privacy_risk(event),
            "tax_risk":                 self._score_tax_risk(event),
            "contractual_risk":         self._score_contractual_risk(event),
            "fraud_aml_risk":           self._score_fraud_aml_risk(event),
            "operational_risk":         self._score_operational_risk(event),
            "country_enforcement_risk": self._score_country_enforcement_risk(event),
        }

        # Weighted overall score
        overall = sum(
            dimensions[dim] * weight
            for dim, weight in DIMENSION_WEIGHTS.items()
        )
        overall_score = min(int(round(overall)), 100)

        # Launch decision
        if blockers:
            decision = "BLOCKED"
        elif overall_score >= 60:
            decision = "APPROVED_WITH_CONDITIONS"
        else:
            decision = "APPROVED"

        recommendations = self._build_recommendations(blockers, missing, triggers, event)

        return RiskAssessmentResult(
            overall_score=overall_score,
            launch_decision=decision,
            dimensions=dimensions,
            blocking_reasons=blockers,
            high_risk_triggers=triggers,
            missing_controls=missing,
            recommendations=recommendations,
        )


# Singleton
_engine_instance: TicketingRiskEngine | None = None


def get_risk_engine() -> TicketingRiskEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = TicketingRiskEngine()
    return _engine_instance
