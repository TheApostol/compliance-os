"""
M3 — AML/KYC Orchestration
===========================
Red flag detection, OFAC/sanctions screening, EDD recommendations.
"""

from __future__ import annotations

from typing import Any

from app.services.ai_orchestrator import (
    AIOrchestrator, InferenceRequest, TaskType, get_orchestrator
)


KYC_SYSTEM = """You are an AML/KYC senior analyst for ComplianceOS, expert in LATAM and global AML
frameworks (FATF, UIF AR, COAF BR, UIAF CO, UAF CL, CNBV MX, OFAC, FinCEN, EU AMLD).

Always:
- Identify specific typologies (smurfing, layering, structuring, trade-based ML, etc.)
- Cite applicable norms (Ley 25.246, FATF Rec, etc.)
- Recommend explicit next actions
- Flag if RoF/SAR reporting is required
- Output ONLY valid JSON."""


SCREENING_SYSTEM = """You are a sanctions screening analyst. Evaluate exposure to OFAC SDN, UN, EU,
HMT, FATF high-risk jurisdictions. Output ONLY valid JSON."""


KYC_SCHEMA = """{
  "risk_score": 1-100,
  "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
  "red_flags": ["list of specific red flags"],
  "typologies_detected": ["specific AML typology names"],
  "rof_sar_required": bool,
  "applicable_norms": ["specific laws/articles"],
  "edd_requirements": ["enhanced due diligence steps"],
  "recommended_action": "ACCEPT|EDD|REJECT|ESCALATE",
  "rationale": "1-3 sentences",
  "obligations_triggered": ["obligation_codes from ComplianceOS"]
}"""


SCREENING_SCHEMA = """{
  "ofac_risk": "LOW|MEDIUM|HIGH|CRITICAL",
  "lists_to_check": ["OFAC SDN", "UN", "EU", "HMT", "FATF high-risk"],
  "fatf_concerns": ["specific concerns"],
  "geographic_risk": ["high-risk jurisdictions involved"],
  "recommendation": "ACCEPT|REJECT|EDD|ESCALATE",
  "additional_controls": ["specific controls to apply"],
  "rationale": "str"
}"""


class KYCAMLEngine:
    def __init__(self, orchestrator: AIOrchestrator | None = None):
        self.orch = orchestrator or get_orchestrator()

    async def screen_customer(
        self,
        customer_data: dict[str, Any],
        tenant_id: str,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Run a full KYC risk assessment."""
        prompt = (
            f"Customer profile:\n{self._format_dict(customer_data)}\n\n"
            f"Perform comprehensive KYC/AML risk assessment.\n\n"
            f"Return JSON:\n{KYC_SCHEMA}"
        )
        result = await self.orch.infer(InferenceRequest(
            task=TaskType.KYC_SCREENING,
            system=KYC_SYSTEM,
            user_prompt=prompt,
            tenant_id=tenant_id,
            user_id=user_id,
            temperature=0.1,
            max_tokens=2048,
        ))
        return self._format_result(result)

    async def sanctions_screen(
        self,
        subject_data: dict[str, Any],
        tenant_id: str,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Sanctions and PEP screening."""
        prompt = (
            f"Subject:\n{self._format_dict(subject_data)}\n\n"
            f"Screen for OFAC SDN, UN, EU, FATF exposure.\n\n"
            f"Return JSON:\n{SCREENING_SCHEMA}"
        )
        result = await self.orch.infer(InferenceRequest(
            task=TaskType.SANCTIONS_SCREENING,
            system=SCREENING_SYSTEM,
            user_prompt=prompt,
            tenant_id=tenant_id,
            user_id=user_id,
            temperature=0.1,
            max_tokens=1536,
        ))
        return self._format_result(result)

    @staticmethod
    def _format_dict(d: dict) -> str:
        return "\n".join(f"- {k}: {v}" for k, v in d.items())

    @staticmethod
    def _format_result(result) -> dict[str, Any]:
        return {
            "success": result.success,
            "analysis": result.parsed_json or {},
            "audit_id": result.audit_id,
            "model_used": result.model_used,
            "latency_ms": result.latency_total_ms,
            "cost_usd": result.estimated_cost_usd,
            "error": result.error,
        }
