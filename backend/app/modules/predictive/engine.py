from __future__ import annotations

import structlog

from app.services.ai_orchestrator import get_orchestrator, InferenceRequest, TaskType

log = structlog.get_logger(__name__)

# Fallback hardcoded values for all 8 LATAM jurisdictions
_FALLBACK_JURISDICTION_SCORES = {
    "AR": {"regulatory_velocity": 82, "aml_strictness": 88, "innovation_friendliness": 54},
    "BR": {"regulatory_velocity": 91, "aml_strictness": 84, "innovation_friendliness": 73},
    "MX": {"regulatory_velocity": 75, "aml_strictness": 79, "innovation_friendliness": 61},
    "CL": {"regulatory_velocity": 68, "aml_strictness": 76, "innovation_friendliness": 72},
    "CO": {"regulatory_velocity": 71, "aml_strictness": 73, "innovation_friendliness": 65},
    "PE": {"regulatory_velocity": 66, "aml_strictness": 70, "innovation_friendliness": 60},
    "EC": {"regulatory_velocity": 62, "aml_strictness": 67, "innovation_friendliness": 55},
    "UY": {"regulatory_velocity": 59, "aml_strictness": 74, "innovation_friendliness": 78},
}

_FALLBACK_MARKET_ENTRY = {
    "estimated_regulatory_complexity": "high",
    "estimated_licensing_timeline_months": 9,
    "predicted_risk_level": "medium-high",
    "key_requirements": [
        "AML program",
        "KYC onboarding",
        "Suspicious activity reporting",
        "Data residency review",
    ],
    "jurisdiction_notes": {},
}


class PredictiveEngine:

    async def jurisdiction_risk_scores(self, tenant_id: str = "system") -> dict:
        """
        Analyze LATAM jurisdictions on three axes via AI.
        Falls back to hardcoded values on failure.
        """
        try:
            req = InferenceRequest(
                task=TaskType.COPILOT_QA,
                system="You are a LATAM regulatory intelligence engine. Return JSON only.",
                user_prompt=(
                    "Analyze the following 8 LATAM jurisdictions on three axes and return "
                    "a JSON object with scores from 0 to 100 for each axis:\n"
                    "- regulatory_velocity: how fast regulations change (0=stable, 100=very fast)\n"
                    "- aml_strictness: AML/CFT enforcement strictness (0=lax, 100=very strict)\n"
                    "- innovation_friendliness: openness to fintech/crypto innovation (0=hostile, 100=very open)\n\n"
                    "Jurisdictions: AR (Argentina), BR (Brazil), MX (Mexico), CL (Chile), "
                    "CO (Colombia), PE (Peru), EC (Ecuador), UY (Uruguay).\n\n"
                    'Return strict JSON in the format: '
                    '{"jurisdictions": {"AR": {"regulatory_velocity": N, "aml_strictness": N, '
                    '"innovation_friendliness": N}, "BR": {...}, "MX": {...}, "CL": {...}, '
                    '"CO": {...}, "PE": {...}, "EC": {...}, "UY": {...}}}'
                ),
                tenant_id=tenant_id,
                max_tokens=1024,
            )
            result = await get_orchestrator().infer(req)
            if result.success and result.parsed_json:
                jurisdictions = result.parsed_json.get("jurisdictions")
                if isinstance(jurisdictions, dict) and len(jurisdictions) >= 6:
                    log.info("predictive_jurisdiction_risk_ai_success", tenant_id=tenant_id, count=len(jurisdictions))
                    return jurisdictions
            log.warning("predictive_jurisdiction_risk_ai_empty", tenant_id=tenant_id, success=result.success)
        except Exception as exc:
            log.warning("predictive_jurisdiction_risk_ai_error", tenant_id=tenant_id, error=str(exc))

        log.info("predictive_jurisdiction_risk_fallback", tenant_id=tenant_id)
        return _FALLBACK_JURISDICTION_SCORES

    async def simulate_market_entry(
        self,
        business_model: str,
        countries: list[str],
        tenant_id: str = "system",
    ) -> dict:
        """
        Simulate market entry for a business model in target countries via AI.
        Falls back to static response on failure.
        """
        countries_str = ", ".join(countries) if countries else "unspecified"
        try:
            req = InferenceRequest(
                task=TaskType.COPILOT_DEEP,
                system=(
                    "You are a LATAM regulatory intelligence engine specializing in market entry "
                    "analysis. Return JSON only."
                ),
                user_prompt=(
                    f"Analyze market entry feasibility for the following business model in "
                    f"the specified LATAM countries.\n\n"
                    f"Business Model: {business_model}\n"
                    f"Target Countries: {countries_str}\n\n"
                    "Return strict JSON with the following structure:\n"
                    "{\n"
                    f'  "business_model": "{business_model}",\n'
                    f'  "countries": {countries},\n'
                    '  "estimated_regulatory_complexity": "low" | "medium" | "high",\n'
                    '  "estimated_licensing_timeline_months": <integer>,\n'
                    '  "predicted_risk_level": "low" | "medium" | "medium-high" | "high" | "critical",\n'
                    '  "key_requirements": ["<requirement1>", "<requirement2>", ...],\n'
                    '  "jurisdiction_notes": {"<country_code>": "<specific notes>", ...}\n'
                    "}"
                ),
                tenant_id=tenant_id,
                max_tokens=1024,
            )
            result = await get_orchestrator().infer(req)
            if result.success and result.parsed_json:
                data = result.parsed_json
                # Validate expected keys are present
                if "predicted_risk_level" in data and "key_requirements" in data:
                    # Ensure business_model and countries are always present
                    data.setdefault("business_model", business_model)
                    data.setdefault("countries", countries)
                    log.info("predictive_market_entry_ai_success", tenant_id=tenant_id, countries=countries_str)
                    return data
            log.warning("predictive_market_entry_ai_empty", tenant_id=tenant_id, success=result.success)
        except Exception as exc:
            log.warning("predictive_market_entry_ai_error", tenant_id=tenant_id, error=str(exc))

        log.info("predictive_market_entry_fallback", tenant_id=tenant_id)
        return {
            "business_model": business_model,
            "countries": countries,
            **_FALLBACK_MARKET_ENTRY,
        }


_engine = PredictiveEngine()


def get_predictive_engine():
    return _engine
