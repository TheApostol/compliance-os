from __future__ import annotations


class PredictiveEngine:

    async def jurisdiction_risk_scores(self):
        return {
            'AR': {
                'regulatory_velocity': 82,
                'aml_strictness': 88,
                'innovation_friendliness': 54,
            },
            'BR': {
                'regulatory_velocity': 91,
                'aml_strictness': 84,
                'innovation_friendliness': 73,
            },
            'MX': {
                'regulatory_velocity': 75,
                'aml_strictness': 79,
                'innovation_friendliness': 61,
            },
        }

    async def simulate_market_entry(self, business_model: str, countries: list[str]):
        return {
            'business_model': business_model,
            'countries': countries,
            'estimated_regulatory_complexity': 'high',
            'estimated_licensing_timeline_months': 9,
            'predicted_risk_level': 'medium-high',
            'key_requirements': [
                'AML program',
                'KYC onboarding',
                'Suspicious activity reporting',
                'Data residency review',
            ]
        }


_engine = PredictiveEngine()


def get_predictive_engine():
    return _engine
