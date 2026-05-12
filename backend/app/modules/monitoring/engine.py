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
        prompt = (
            f"Transaction pattern (last 30 days):\n"
            f"{self._fmt(transaction_summary)}\n\n"
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
        return self._result(result)

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
        return self._result(result)

    @staticmethod
    def _fmt(d: dict) -> str:
        return "\n".join(f"- {k}: {v}" for k, v in d.items())

    @staticmethod
    def _result(r) -> dict[str, Any]:
        return {
            "success": r.success,
            "analysis": r.parsed_json or {},
            "audit_id": r.audit_id,
            "model_used": r.model_used,
            "latency_ms": r.latency_total_ms,
            "error": r.error,
        }
