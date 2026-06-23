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


ANOMALY_SYSTEM = """You are a transaction monitoring analyst. Detect AML typologies in transaction
patterns: structuring, smurfing, layering, integration, trade-based ML, carding, merchant fraud,
chargebacks abuse, mule networks. Output JSON only."""


DRIFT_SYSTEM = """You are a policy drift detector. Compare expected control behavior vs actual logs.
Identify gaps, root causes, and regulatory exposure. Output JSON only."""


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


class MonitoringEngine:
    def __init__(self, orchestrator: AIOrchestrator | None = None):
        self.orch = orchestrator or get_orchestrator()

    async def analyze_transactions(
        self,
        transaction_summary: dict[str, Any],
        tenant_id: str,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Analyze a transaction pattern summary for AML anomalies."""
        rule_flags, rule_score = _deterministic_anomaly_floor(transaction_summary)
        prompt = (
            f"Transaction pattern (last 30 days):\n"
            f"{self._fmt(transaction_summary)}\n\n"
            f"Deterministic rules already triggered: {rule_flags or 'none'}\n\n"
            f"Analyze for AML anomalies. Return JSON:\n{ANOMALY_SCHEMA}"
        )
        result = await self.orch.infer(InferenceRequest(
            task=TaskType.ANOMALY_DETECTION,
            system=ANOMALY_SYSTEM,
            user_prompt=prompt,
            tenant_id=tenant_id,
            user_id=user_id,
            temperature=0.1,
            max_tokens=1536,
        ))
        return self._result(result, rule_flags, rule_score)

    async def detect_drift(
        self,
        policy_description: str,
        observed_behavior: dict[str, Any],
        tenant_id: str,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Compare expected policy vs observed logs."""
        prompt = (
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
            ai_score = ai_analysis.get("anomaly_score")
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
