"""
M2 — AI Compliance Copilot
===========================
Multi-jurisdiction Q&A and cross-border analysis.
"""

from __future__ import annotations

from typing import Any

from app.services.ai_orchestrator import (
    AIOrchestrator, InferenceRequest, TaskType, get_orchestrator
)


COPILOT_SYSTEM = """You are ComplianceOS Copilot, an expert regulatory advisor for LATAM fintech, PSP, crypto, and payments.

Rules:
1. Always cite specific norms (law numbers, communications, articles).
2. Distinguish "established law" vs "regulatory grey area".
3. If asked about a jurisdiction you don't have current data on, say so explicitly.
4. Output structured JSON when a schema is requested.
5. Never give binding legal advice — flag when human counsel is needed.
"""


class ComplianceCopilot:
    def __init__(self, orchestrator: AIOrchestrator | None = None):
        self.orch = orchestrator or get_orchestrator()

    async def ask(
        self,
        question: str,
        tenant_id: str,
        user_id: str | None = None,
        context: dict[str, Any] | None = None,
        deep_mode: bool = False,
        output_schema: dict | None = None,
    ) -> dict[str, Any]:
        """Ask the copilot. RAG context injected automatically from Qdrant when available."""
        # Retrieve relevant regulation chunks from Qdrant (best-effort)
        rag_context = ""
        rag_chunks = 0
        try:
            from app.services.rag import get_rag
            rag = get_rag()
            rag_context = await rag.context_for_query(question, tenant_id=tenant_id, top_k=4)
            rag_chunks = rag_context.count("[") if rag_context else 0
        except Exception:
            pass

        prompt = question
        if rag_context:
            prompt = f"{rag_context}\n\nQuestion: {question}"
        if context:
            prompt = f"Context:\n{context}\n\n{prompt}"
        if output_schema:
            prompt += f"\n\nReturn ONLY valid JSON matching this schema:\n{output_schema}"

        result = await self.orch.infer(InferenceRequest(
            task=TaskType.COPILOT_DEEP if deep_mode else TaskType.COPILOT_QA,
            system=COPILOT_SYSTEM,
            user_prompt=prompt,
            tenant_id=tenant_id,
            user_id=user_id,
            temperature=0.3,
            max_tokens=2048,
            json_mode=output_schema is not None,
        ))

        return {
            "success": result.success,
            "answer": result.parsed_json if output_schema else result.response_text,
            "rag_chunks_used": rag_chunks,
            "audit_id": result.audit_id,
            "model_used": result.model_used,
            "latency_ms": result.latency_total_ms,
            "cost_usd": result.estimated_cost_usd,
            "error": result.error,
        }

    async def expansion_analysis(
        self,
        from_country: str,
        to_country: str,
        business_model: str,
        tenant_id: str,
    ) -> dict[str, Any]:
        """Common ComplianceOS use case: 'what changes if I expand from X to Y?'"""
        schema = {
            "regulatory_authority": "str",
            "license_required": "str",
            "timeline_months": "int",
            "minimum_capital_usd": "str",
            "key_differences": ["list"],
            "aml_obligations_diff": ["list"],
            "tax_implications": ["list"],
            "estimated_compliance_cost_y1_usd": "str",
            "blockers": ["list"],
            "go_no_go": "GO|CONDITIONAL_GO|NO_GO",
            "rationale": "str",
            "actionable_next_steps": ["list"]
        }
        question = (
            f"Our business operates in {from_country} as a {business_model}. "
            f"Analyze regulatory requirements to expand to {to_country} with the same model."
        )
        return await self.ask(
            question=question,
            tenant_id=tenant_id,
            deep_mode=True,
            output_schema=schema,
        )
