"""
M4 — Continuous Monitoring
===========================
Transaction anomaly detection + policy drift detection.
"""

from __future__ import annotations

from typing import Any

from app.services.ai_orchestrator import (
    AIOrchestrator, InferenceRequest, TaskType, get_orchestrator
)


ANOMALY_SYSTEM = """You are a transaction monitoring analyst for a LATAM financial entity regulated by
BCRA, UIF, BACEN, and CMF. Detect AML typologies in transaction patterns: structuring, smurfing,
layering, integration, trade-based ML, carding, merchant fraud, chargebacks abuse, mule networks.
Output JSON only."""

INSURANCE_ANOMALY_SYSTEM = """You are a solvency and market-conduct monitoring analyst for a LATAM
insurer regulated by SSN (Argentina), SUSEP (Brazil), CMF (Chile), and CNSF (Mexico). Detect
anomalies in claims, underwriting, and reserve patterns: claims fraud indicators, reserve adequacy
drift, solvency ratio deterioration, and mis-selling patterns. Output JSON only."""

CORPORATE_ANOMALY_SYSTEM = """You are a general compliance monitoring analyst for a LATAM corporate
entity, covering labor, environmental, tax, and data-privacy (LGPD/PDPA) obligations. Detect
anomalies in operational compliance patterns: policy violations, unauthorized data processing,
environmental reporting gaps, and labor compliance deviations. Output JSON only."""

PV_SYSTEM = """You are a pharmacovigilance and product-safety analyst for a LATAM healthcare/pharma
entity regulated by ANMAT (Argentina), ANVISA (Brazil), and COFEPRIS (Mexico), with data-privacy
obligations under LGPD/PDPA. Detect safety signals in adverse-event and quality-deviation data:
adverse-event clustering, signal disproportionality, device malfunctions, counterfeit/diversion
indicators, off-label use patterns, and quality deviations. Never reference FDA, MedWatch, EMA, or
other non-LATAM regulators. Output JSON only."""


DRIFT_SYSTEM = """You are a policy drift detector. Compare expected control behavior vs actual logs.
Identify gaps, root causes, and regulatory exposure. Output JSON only."""

DRIFT_INDUSTRY_CONTEXT: dict[str, str] = {
    "financial": "This entity operates under LATAM financial AML/CFT regulations (BCRA, UIF, BACEN, CMF).",
    "insurance": "This entity operates under LATAM insurance solvency and market-conduct regulations (SSN, SUSEP, CMF, CNSF).",
    "healthcare": "This entity operates under LATAM pharmacovigilance and health-product regulations (ANMAT, ANVISA, COFEPRIS) and data-privacy law (LGPD/PDPA).",
    "corporate": "This entity operates under LATAM labor, environmental, and data-privacy regulations (LGPD/PDPA).",
}


ANOMALY_SCHEMA = """{
  "anomaly_score": 1-100,
  "patterns_detected": ["technical AML typology names"],
  "likely_typologies": ["typology1", "typology2"],
  "evidence": ["specific data points supporting the assessment"],
  "merchant_account_action": "FREEZE|RESTRICT|MONITOR|NO_ACTION",
  "rof_sar_required": bool,
  "investigation_priority": "LOW|MEDIUM|HIGH|CRITICAL",
  "evidence_to_preserve": ["log_types"],
  "recommended_next_steps": ["actionable steps"]
}"""

INSURANCE_ANOMALY_SCHEMA = """{
  "anomaly_score": 1-100,
  "patterns_detected": ["claims_fraud", "reserve_drift", "solvency_deterioration", "mis_selling"],
  "evidence": ["specific data points supporting the assessment"],
  "regulatory_filing_required": bool,
  "investigation_priority": "LOW|MEDIUM|HIGH|CRITICAL",
  "evidence_to_preserve": ["log_types"],
  "recommended_next_steps": ["actionable steps"]
}"""

CORPORATE_ANOMALY_SCHEMA = """{
  "anomaly_score": 1-100,
  "patterns_detected": ["policy_violation", "data_privacy_gap", "environmental_reporting_gap", "labor_compliance_deviation"],
  "evidence": ["specific data points supporting the assessment"],
  "regulatory_filing_required": bool,
  "investigation_priority": "LOW|MEDIUM|HIGH|CRITICAL",
  "evidence_to_preserve": ["log_types"],
  "recommended_next_steps": ["actionable steps"]
}"""

PV_SCHEMA = """{
  "signal_score": 1-100,
  "signal_type": ["adverse_event_cluster", "device_malfunction", "quality_deviation", "off_label_use", "counterfeit_suspected"],
  "seriousness": "NON_SERIOUS|SERIOUS|FATAL",
  "evidence": ["specific data points supporting the assessment"],
  "regulatory_action": "REPORT_ANMAT|REPORT_ANVISA|REPORT_COFEPRIS|RECALL_REVIEW|MONITOR|NO_ACTION",
  "expedited_report_required": bool,
  "investigation_priority": "LOW|MEDIUM|HIGH|CRITICAL",
  "evidence_to_preserve": ["log_types"],
  "recommended_next_steps": ["actionable steps"]
}"""


DRIFT_SCHEMA = """{
  "drift_detected": bool,
  "drift_severity": "LOW|MEDIUM|HIGH|CRITICAL",
  "policy_violation_rate": 0.0-1.0,
  "affected_operations_count": int,
  "regulatory_exposure": ["specific norms violated"],
  "root_cause_hypotheses": ["hypothesis1", "hypothesis2"],
  "immediate_actions": ["actions"],
  "remediation_plan": ["medium-term remediation steps"]
}"""

VELOCITY_MAX_COUNT = 5
VELOCITY_MAX_SUM = 15000
CTR_THRESHOLD = 10000

PV_CLUSTER_THRESHOLD = 3  # 3+ similar serious events = signal cluster

_AML_SYSTEM_BY_INDUSTRY: dict[str, str] = {
    "financial": ANOMALY_SYSTEM,
    "insurance": INSURANCE_ANOMALY_SYSTEM,
    "corporate": CORPORATE_ANOMALY_SYSTEM,
}
_AML_SCHEMA_BY_INDUSTRY: dict[str, str] = {
    "financial": ANOMALY_SCHEMA,
    "insurance": INSURANCE_ANOMALY_SCHEMA,
    "corporate": CORPORATE_ANOMALY_SCHEMA,
}


def _deterministic_anomaly_floor(summary: dict[str, Any]) -> tuple[list[str], int]:
    """Rule-based floor over an aggregate transaction summary — keeps anomaly
    detection from failing open ("no anomalies") if the AI call fails."""
    flags: list[str] = []
    score = 0

    count = summary.get("transaction_count") or summary.get("count") or 0
    total = summary.get("total_amount") or summary.get("total") or 0
    try:
        count, total = int(count), float(total)
    except (TypeError, ValueError):
        count, total = 0, 0.0

    if count >= VELOCITY_MAX_COUNT or total >= VELOCITY_MAX_SUM:
        flags.append("velocity_threshold")
        score += 30

    max_single = summary.get("max_single_amount") or 0
    try:
        if float(max_single) >= CTR_THRESHOLD:
            flags.append("ctr_threshold")
            score += 30
    except (TypeError, ValueError):
        pass

    if summary.get("high_risk_geography_flag") or summary.get("high_risk_countries"):
        flags.append("high_risk_geography")
        score += 25

    return flags, min(score, 100)


def _deterministic_pv_floor(summary: dict[str, Any]) -> tuple[list[str], int]:
    """Rule-based floor for pharmacovigilance signal data — keeps safety-signal
    detection from failing open if the AI call fails."""
    flags: list[str] = []
    score = 0

    def _as_int(*keys: str) -> int:
        for k in keys:
            if k in summary:
                try:
                    return int(summary[k])
                except (TypeError, ValueError):
                    return 0
        return 0

    death_count = _as_int("death_count", "fatal_outcome_count")
    serious_event_count = _as_int("serious_event_count", "serious_adverse_event_count")

    if death_count >= 1:
        flags.append("fatal_outcome_reported")
        score += 50

    if serious_event_count >= PV_CLUSTER_THRESHOLD:
        flags.append("serious_event_cluster")
        score += 35

    if summary.get("device_malfunction_flag") or _as_int("device_malfunction_count") >= 1:
        flags.append("device_malfunction")
        score += 25

    if summary.get("counterfeit_suspected") or summary.get("diversion_suspected"):
        flags.append("counterfeit_or_diversion_suspected")
        score += 30

    return flags, min(score, 100)


class MonitoringEngine:
    def __init__(self, orchestrator: AIOrchestrator | None = None):
        self.orch = orchestrator or get_orchestrator()

    async def analyze_transactions(
        self,
        transaction_summary: dict[str, Any],
        tenant_id: str,
        user_id: str | None = None,
        industry: str = "financial",
    ) -> dict[str, Any]:
        """Analyze an aggregate signal summary for anomalies, routed by industry:
        AML typologies (financial/insurance/corporate) or pharmacovigilance safety
        signals (healthcare)."""
        if industry == "healthcare":
            return await self._analyze_pharmacovigilance(transaction_summary, tenant_id, user_id)
        return await self._analyze_aml(transaction_summary, tenant_id, user_id, industry)

    async def _analyze_aml(
        self,
        transaction_summary: dict[str, Any],
        tenant_id: str,
        user_id: str | None,
        industry: str,
    ) -> dict[str, Any]:
        system = _AML_SYSTEM_BY_INDUSTRY.get(industry, ANOMALY_SYSTEM)
        schema = _AML_SCHEMA_BY_INDUSTRY.get(industry, ANOMALY_SCHEMA)
        rule_flags, rule_score = _deterministic_anomaly_floor(transaction_summary)
        prompt = (
            f"Transaction pattern (last 30 days):\n"
            f"{self._fmt(transaction_summary)}\n\n"
            f"Deterministic rules already triggered: {rule_flags or 'none'}\n\n"
            f"Analyze for anomalies. Return JSON:\n{schema}"
        )
        result = await self.orch.infer(InferenceRequest(
            task=TaskType.ANOMALY_DETECTION,
            system=system,
            user_prompt=prompt,
            tenant_id=tenant_id,
            user_id=user_id,
            temperature=0.1,
            max_tokens=1536,
        ))
        return self._result(result, rule_flags, rule_score)

    async def _analyze_pharmacovigilance(
        self,
        signal_summary: dict[str, Any],
        tenant_id: str,
        user_id: str | None,
    ) -> dict[str, Any]:
        rule_flags, rule_score = _deterministic_pv_floor(signal_summary)
        prompt = (
            f"Safety signal data (current reporting period):\n"
            f"{self._fmt(signal_summary)}\n\n"
            f"Deterministic rules already triggered: {rule_flags or 'none'}\n\n"
            f"Analyze for pharmacovigilance safety signals. Return JSON:\n{PV_SCHEMA}"
        )
        result = await self.orch.infer(InferenceRequest(
            task=TaskType.ANOMALY_DETECTION,
            system=PV_SYSTEM,
            user_prompt=prompt,
            tenant_id=tenant_id,
            user_id=user_id,
            temperature=0.1,
            max_tokens=1536,
        ))
        return self._result(result, rule_flags, rule_score, score_field="signal_score")

    async def detect_drift(
        self,
        policy_description: str,
        observed_behavior: dict[str, Any],
        tenant_id: str,
        user_id: str | None = None,
        industry: str = "financial",
    ) -> dict[str, Any]:
        """Compare expected policy vs observed logs."""
        industry_context = DRIFT_INDUSTRY_CONTEXT.get(industry, DRIFT_INDUSTRY_CONTEXT["financial"])
        prompt = (
            f"Regulatory context: {industry_context}\n\n"
            f"Expected policy:\n{policy_description}\n\n"
            f"Observed behavior:\n{self._fmt(observed_behavior)}\n\n"
            f"Return JSON:\n{DRIFT_SCHEMA}"
        )
        result = await self.orch.infer(InferenceRequest(
            task=TaskType.POLICY_DRIFT,
            system=DRIFT_SYSTEM,
            user_prompt=prompt,
            tenant_id=tenant_id,
            user_id=user_id,
            temperature=0.1,
            max_tokens=1536,
        ))
        analysis = result.parsed_json or {}
        if not result.success:
            # Never fail open: if the AI couldn't run, we have no basis to claim
            # "no drift" — flag it as unknown/high severity for human review.
            analysis = {
                "drift_detected": True,
                "drift_severity": "UNKNOWN_AI_UNAVAILABLE",
                "remediation_plan": ["Manual policy-vs-logs review required — AI analysis unavailable"],
            }
        return self._result(result, analysis=analysis)

    @staticmethod
    def _fmt(d: dict) -> str:
        return "\n".join(f"- {k}: {v}" for k, v in d.items())

    @staticmethod
    def _result(
        r,
        rule_flags: list[str] | None = None,
        rule_score: int | None = None,
        analysis: dict[str, Any] | None = None,
        score_field: str = "anomaly_score",
    ) -> dict[str, Any]:
        ai_analysis = analysis if analysis is not None else (r.parsed_json or {})
        out: dict[str, Any] = {
            "success": r.success,
            "analysis": ai_analysis,
            "audit_id": r.audit_id,
            "model_used": r.model_used,
            "latency_ms": r.latency_total_ms,
            "error": r.error,
        }
        if rule_flags is not None:
            ai_score = ai_analysis.get(score_field)
            if r.success and isinstance(ai_score, (int, float)):
                final_score = round(0.4 * rule_score + 0.6 * ai_score)
            else:
                # AI unavailable or returned no score — fall back to the
                # deterministic floor instead of an empty analysis.
                final_score = rule_score
            out["rule_flags"] = rule_flags
            out["anomaly_score"] = final_score
            if not r.success:
                out["investigation_priority"] = "HIGH" if (rule_flags or final_score >= 35) else "MEDIUM"
        return out
