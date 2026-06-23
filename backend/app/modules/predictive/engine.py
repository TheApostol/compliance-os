"""
M8 — Predictive Risk
=====================
Jurisdiction risk scoring and market-entry simulation, grounded in real
regulatory data (regulation cadence, obligation density) and synthesized
via the AI Orchestrator — never hardcoded, never a direct model call.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select

from app.db.base import AsyncSessionLocal
from app.db.models import Obligation, Regulation
from app.services.ai_orchestrator import (
    AIOrchestrator, InferenceRequest, TaskType, get_orchestrator
)

LATAM_COUNTRIES = ["AR", "BR", "MX", "CO", "CL", "PE", "UY", "PY", "BO"]
VELOCITY_WINDOW_DAYS = 180

JURISDICTION_SYSTEM = """You are a LATAM regulatory risk analyst for ComplianceOS. You will be given
real regulatory data points (regulation publication counts, sectors covered) per country. Use them to
ground your scoring — do not invent figures, reason from the data and your domain knowledge of FATF,
AML frameworks, and central bank posture in each jurisdiction. Output ONLY valid JSON."""

JURISDICTION_SCHEMA = """{
  "<country_code>": {
    "aml_strictness": 1-100,
    "innovation_friendliness": 1-100,
    "rationale": "1-2 sentences grounded in the data provided"
  }, ...
}"""

MARKET_ENTRY_SYSTEM = """You are a market-entry compliance strategist for ComplianceOS, expert in
LATAM fintech licensing (BCRA, UIF, BACEN, CMF, CNBV, SBS). You will be given the actual count of
applicable obligations on file for the target countries/sector. Ground your timeline and complexity
estimate in that count plus FATF/AML norms. Output ONLY valid JSON."""

MARKET_ENTRY_SCHEMA = """{
  "estimated_regulatory_complexity": "low|medium|high|very_high",
  "estimated_licensing_timeline_months": int,
  "predicted_risk_level": "low|medium|medium-high|high",
  "key_requirements": ["specific requirements"],
  "rationale": "grounded in obligation counts and sector norms"
}"""


class PredictiveEngine:
    def __init__(self, orchestrator: AIOrchestrator | None = None):
        self.orch = orchestrator or get_orchestrator()

    async def jurisdiction_risk_scores(
        self, tenant_id: str, user_id: str | None = None
    ) -> dict[str, Any]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=VELOCITY_WINDOW_DAYS)

        async with AsyncSessionLocal() as session:
            stmt = (
                select(Regulation.country, func.count(Regulation.id))
                .where(
                    Regulation.published_at >= cutoff,
                    (Regulation.tenant_id == tenant_id) | (Regulation.tenant_id.is_(None)),
                )
                .group_by(Regulation.country)
            )
            result = await session.execute(stmt)
            counts = dict(result.all())

        max_count = max(counts.values(), default=0)
        data_points = {
            country: {
                "regulations_published_last_180d": counts.get(country, 0),
                "regulatory_velocity": (
                    round((counts.get(country, 0) / max_count) * 100) if max_count else 0
                ),
            }
            for country in LATAM_COUNTRIES
        }

        prompt = (
            f"Real regulation publication counts (trailing {VELOCITY_WINDOW_DAYS} days):\n"
            + "\n".join(f"- {c}: {v['regulations_published_last_180d']} regulations" for c, v in data_points.items())
            + f"\n\nFor each of {LATAM_COUNTRIES}, score aml_strictness and innovation_friendliness.\n\n"
            f"Return JSON:\n{JURISDICTION_SCHEMA}"
        )
        ai_result = await self.orch.infer(InferenceRequest(
            task=TaskType.JURISDICTION_RISK,
            system=JURISDICTION_SYSTEM,
            user_prompt=prompt,
            tenant_id=tenant_id,
            user_id=user_id,
            temperature=0.1,
            max_tokens=2048,
        ))
        ai_scores = ai_result.parsed_json or {}

        scores: dict[str, Any] = {}
        for country, dp in data_points.items():
            ai_for_country = ai_scores.get(country, {})
            scores[country] = {
                "regulatory_velocity": dp["regulatory_velocity"],
                "regulations_published_last_180d": dp["regulations_published_last_180d"],
                "aml_strictness": ai_for_country.get("aml_strictness"),
                "innovation_friendliness": ai_for_country.get("innovation_friendliness"),
                "rationale": ai_for_country.get("rationale"),
            }

        return {
            "success": ai_result.success,
            "jurisdictions": scores,
            "audit_id": ai_result.audit_id,
            "model_used": ai_result.model_used,
            "latency_ms": ai_result.latency_total_ms,
            "cost_usd": ai_result.estimated_cost_usd,
            "error": ai_result.error,
        }

    async def simulate_market_entry(
        self, business_model: str, countries: list[str], tenant_id: str, user_id: str | None = None
    ) -> dict[str, Any]:
        async with AsyncSessionLocal() as session:
            stmt = (
                select(Regulation.country, func.count(Obligation.id))
                .join(Obligation, Obligation.regulation_id == Regulation.id)
                .where(
                    Regulation.country.in_(countries),
                    (Regulation.tenant_id == tenant_id) | (Regulation.tenant_id.is_(None)),
                )
                .group_by(Regulation.country)
            )
            result = await session.execute(stmt)
            obligation_counts = dict(result.all())

        total_obligations = sum(obligation_counts.values())

        prompt = (
            f"Business model: {business_model}\n"
            f"Target countries: {countries}\n"
            f"Obligations currently on file per country: {obligation_counts or 'none ingested yet'}\n"
            f"Total applicable obligations found: {total_obligations}\n\n"
            f"Estimate regulatory complexity and licensing timeline for this market entry.\n\n"
            f"Return JSON:\n{MARKET_ENTRY_SCHEMA}"
        )
        ai_result = await self.orch.infer(InferenceRequest(
            task=TaskType.MARKET_ENTRY_SIM,
            system=MARKET_ENTRY_SYSTEM,
            user_prompt=prompt,
            tenant_id=tenant_id,
            user_id=user_id,
            temperature=0.1,
            max_tokens=1536,
        ))
        analysis = ai_result.parsed_json or {}

        return {
            "success": ai_result.success,
            "business_model": business_model,
            "countries": countries,
            "obligations_on_file": obligation_counts,
            "estimated_regulatory_complexity": analysis.get("estimated_regulatory_complexity"),
            "estimated_licensing_timeline_months": analysis.get("estimated_licensing_timeline_months"),
            "predicted_risk_level": analysis.get("predicted_risk_level"),
            "key_requirements": analysis.get("key_requirements", []),
            "rationale": analysis.get("rationale"),
            "audit_id": ai_result.audit_id,
            "model_used": ai_result.model_used,
            "latency_ms": ai_result.latency_total_ms,
            "cost_usd": ai_result.estimated_cost_usd,
            "error": ai_result.error,
        }


_engine = PredictiveEngine()


def get_predictive_engine() -> PredictiveEngine:
    return _engine
