"""
M1 — Regulatory Intelligence Engine
====================================
Converts regulatory text into structured, machine-readable obligations.
This is the moat: compliance-as-structured-data.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.services.ai_orchestrator import (
    AIOrchestrator, InferenceRequest, TaskType, get_orchestrator
)


PARSE_SYSTEM = """You are a regulatory parser for ComplianceOS. You convert raw regulatory text into
machine-readable obligations following the ComplianceOS schema. You output ONLY valid JSON. No prose."""


PARSE_PROMPT_TEMPLATE = """Source regulation:
- Country: {country}
- Regulator: {regulator}
- Code: {code}
- Title: {title}

Full text:
\"\"\"
{text}
\"\"\"

Extract obligations. Return JSON with this exact schema:
{{
  "regulation_summary": "1-2 sentence summary",
  "sector_affected": ["PSP", "bank", "crypto", "..."],
  "obligations": [
    {{
      "obligation_code": "AR_<REGULATOR>_<SECTOR>_<TOPIC>",
      "obligation_type": "FUND_SEGREGATION|REPORTING|DISCLOSURE|MONITORING|RESTRICTION|LICENSING|RECORD_KEEPING",
      "description": "what the obligated party must do",
      "frequency": "CONTINUOUS|DAILY|WEEKLY|MONTHLY|QUARTERLY|ANNUAL|EVENT_DRIVEN",
      "deadline_rule": "natural language deadline",
      "severity": "LOW|MEDIUM|HIGH|CRITICAL",
      "evidence_required": ["transaction_logs", "..."],
      "controls_required": ["segregated_accounts", "..."],
      "applies_to_sectors": ["PSP", "..."],
      "penalty_range_usd": "estimated penalty if breached",
      "regulatory_authority_contact": "where to report/respond"
    }}
  ]
}}"""


MAP_SYSTEM = """You harmonize regulatory obligations across LATAM jurisdictions.
Output ONLY valid JSON."""


MAP_PROMPT_TEMPLATE = """Map the obligation "{obligation_topic}" across these jurisdictions: {countries}.

For each country, identify:
- regulator
- local name of the obligation
- legal basis (specific law/article)
- threshold amounts in USD
- reporting deadline
- format/channel
- penalties

JSON schema:
{{
  "obligation_topic": "{obligation_topic}",
  "jurisdictions": [
    {{
      "country": "AR|BR|MX|CL|CO|PE|UY",
      "regulator": str,
      "local_name": str,
      "legal_basis": str,
      "threshold_usd": str,
      "deadline_hours": int,
      "format": str,
      "channel": str,
      "penalties_usd_range": str
    }}
  ],
  "harmonization_score": "0-100, how similar across jurisdictions",
  "compliance_os_unified_workflow": ["step1", "step2", "..."]
}}"""


class RegulatoryIntelligence:
    def __init__(self, orchestrator: AIOrchestrator | None = None):
        self.orch = orchestrator or get_orchestrator()

    async def parse_regulation(
        self,
        country: str,
        regulator: str,
        code: str,
        title: str,
        text: str,
        tenant_id: str,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Convert raw regulatory text into structured obligations."""
        truncated = text[:20000]  # leave room for context window

        result = await self.orch.infer(InferenceRequest(
            task=TaskType.REGULATORY_PARSING,
            system=PARSE_SYSTEM,
            user_prompt=PARSE_PROMPT_TEMPLATE.format(
                country=country, regulator=regulator,
                code=code, title=title, text=truncated,
            ),
            tenant_id=tenant_id,
            user_id=user_id,
            temperature=0.1,
            max_tokens=2048,
            json_mode=True,
        ))

        parsed = result.parsed_json or {}
        obligations_data = parsed.get("obligations", [])

        # Persist to DB — best-effort, never blocks the response
        persisted = 0
        if result.success and obligations_data:
            persisted = await self._persist_obligations(
                country=country, regulator=regulator, code=code,
                title=title, text=text,
                obligations_data=obligations_data,
                model_used=result.model_used,
            )

        return {
            "success": result.success,
            "obligations": obligations_data,
            "obligations_persisted": persisted,
            "summary": parsed.get("regulation_summary"),
            "audit_id": result.audit_id,
            "model_used": result.model_used,
            "latency_ms": result.latency_total_ms,
            "error": result.error,
        }

    @staticmethod
    async def _persist_obligations(
        country: str,
        regulator: str,
        code: str,
        title: str,
        text: str,
        obligations_data: list[dict],
        model_used: str,
    ) -> int:
        """Upsert regulation + insert obligations. Returns count persisted."""
        from app.db.base import AsyncSessionLocal
        from app.db.models import (
            Regulation, Obligation,
            ObligationFrequency, ObligationSeverity,
        )
        from sqlalchemy import select, delete

        VALID_FREQ = {e.value for e in ObligationFrequency}
        VALID_SEV  = {e.value for e in ObligationSeverity}

        try:
            async with AsyncSessionLocal() as session:
                # Find or create regulation
                stmt = select(Regulation).where(
                    Regulation.country == country,
                    Regulation.regulator == regulator,
                    Regulation.code == code,
                )
                reg = (await session.execute(stmt)).scalar_one_or_none()

                if reg is None:
                    reg = Regulation(
                        id=uuid.uuid4(),
                        country=country,
                        regulator=regulator,
                        code=code,
                        title=title,
                        full_text=text[:50000],
                        embedding_status="pending",
                    )
                    session.add(reg)
                    await session.flush()

                # Remove stale obligations for this regulation
                await session.execute(
                    delete(Obligation).where(Obligation.regulation_id == reg.id)
                )

                # Insert fresh obligations
                count = 0
                for o in obligations_data:
                    freq_raw = str(o.get("frequency", "EVENT_DRIVEN")).upper()
                    freq = freq_raw if freq_raw in VALID_FREQ else "EVENT_DRIVEN"
                    sev_raw = str(o.get("severity", "MEDIUM")).upper()
                    sev = sev_raw if sev_raw in VALID_SEV else "MEDIUM"

                    ob = Obligation(
                        id=uuid.uuid4(),
                        regulation_id=reg.id,
                        obligation_code=str(o.get("obligation_code", f"OBL_{count}"))[:64],
                        obligation_type=str(o.get("obligation_type", "OTHER"))[:64],
                        description=str(o.get("description", "")),
                        frequency=ObligationFrequency(freq),
                        deadline_rule=str(o.get("deadline_rule") or "")[:255] or None,
                        severity=ObligationSeverity(sev),
                        applies_to_sectors=o.get("applies_to_sectors", []),
                        evidence_required=o.get("evidence_required", []),
                        controls_required=o.get("controls_required", []),
                        penalty_range_usd=str(o.get("penalty_range_usd") or "")[:128] or None,
                        extracted_by_model=model_used[:128],
                        verified_by_human=False,
                    )
                    session.add(ob)
                    count += 1

                await session.commit()
                return count
        except Exception:
            return 0

    async def map_cross_border(
        self,
        obligation_topic: str,
        countries: list[str],
        tenant_id: str,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Harmonize one obligation across multiple jurisdictions."""
        result = await self.orch.infer(InferenceRequest(
            task=TaskType.REGULATORY_MAPPING,
            system=MAP_SYSTEM,
            user_prompt=MAP_PROMPT_TEMPLATE.format(
                obligation_topic=obligation_topic,
                countries=", ".join(countries),
            ),
            tenant_id=tenant_id,
            user_id=user_id,
            temperature=0.2,
            max_tokens=2048,
        ))
        return {
            "success": result.success,
            "mapping": result.parsed_json,
            "audit_id": result.audit_id,
            "model_used": result.model_used,
            "error": result.error,
        }
