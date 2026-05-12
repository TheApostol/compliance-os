"""
M5 — AI Governance Layer
=========================
- Self-auditing of AI outputs (LLM-as-judge)
- Prompt injection detection
- Content safety
- Model registry & approval workflow

This is the moat. Almost nobody in LATAM does this.
"""

from __future__ import annotations

from typing import Any

from app.services.ai_orchestrator import (
    AIOrchestrator, InferenceRequest, TaskType, get_orchestrator,
    detect_injection,
)


AUDITOR_SYSTEM = """You are an AI auditor for ComplianceOS. You evaluate the correctness of previous
AI outputs against the actual factual context. Be rigorous. Be honest. Flag errors that could cause
regulatory exposure. Output JSON only."""


AUDIT_SCHEMA = """{
  "verdict": "CORRECT|PARTIALLY_CORRECT|INCORRECT|DANGEROUSLY_WRONG",
  "errors_identified": ["specific errors"],
  "missing_considerations": ["what the previous response missed"],
  "regulatory_violations_in_advice": ["which norms would be violated by following this advice"],
  "corrected_recommendation": "what the correct answer should have been",
  "confidence_in_audit": 0.0-1.0,
  "should_escalate_to_human": bool,
  "lessons_for_routing": "should we route this task to a different model in future?"
}"""


class AIGovernance:
    def __init__(self, orchestrator: AIOrchestrator | None = None):
        self.orch = orchestrator or get_orchestrator()

    async def audit_response(
        self,
        original_question: str,
        ai_response: str,
        factual_context: str,
        tenant_id: str,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """LLM-as-judge: audit a previous AI response against actual facts."""
        prompt = (
            f"Original question asked to an AI compliance agent:\n{original_question}\n\n"
            f"AI response that was given:\n{ai_response}\n\n"
            f"Actual factual context (ground truth):\n{factual_context}\n\n"
            f"Audit the response. Return JSON:\n{AUDIT_SCHEMA}"
        )
        result = await self.orch.infer(InferenceRequest(
            task=TaskType.SELF_AUDIT,
            system=AUDITOR_SYSTEM,
            user_prompt=prompt,
            tenant_id=tenant_id,
            user_id=user_id,
            temperature=0.1,
            max_tokens=1536,
        ))
        return {
            "success": result.success,
            "audit": result.parsed_json or {},
            "audit_id": result.audit_id,
            "auditor_model": result.model_used,
            "error": result.error,
        }

    def detect_prompt_injection(self, text: str) -> dict[str, Any]:
        """Fast rule-based detection. Returns immediately, no AI call needed."""
        injected, patterns = detect_injection(text)
        return {
            "injection_detected": injected,
            "patterns_matched": patterns,
            "severity": "HIGH" if injected else "NONE",
            "recommended_action": "BLOCK" if injected else "ALLOW",
        }

    async def verify_chain_of_trust(
        self,
        decision_id: str,
        session,
    ) -> dict[str, Any]:
        """Verify the audit log hash chain for a tenant."""
        from app.core.audit import verify_chain
        tenant_id = decision_id.split(":")[0] if ":" in decision_id else decision_id
        return await verify_chain(session, tenant_id)
