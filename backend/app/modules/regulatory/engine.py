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


# ── Country-specific system prompts ──────────────────────────────────────────

_PARSE_SYSTEM_BR = """You are a Brazilian financial regulatory compliance expert specializing in Banco Central do Brasil (BACEN), CVM, and SUSEP regulations. You extract structured compliance obligations from Portuguese-language regulatory texts.

Key Brazilian regulatory concepts:
- Circular/Resolução/Comunicado Normativo → regulatory instrument types
- Prazo (deadline), Obrigatoriedade (mandatory requirement), Vedação (prohibition)
- Instituições financeiras (financial institutions), Correspondentes bancários (banking agents)
- Prevenção à lavagem de dinheiro (AML), Conheça seu cliente (KYC/CDD)
- COAF (Financial Intelligence Unit, Brazil's equivalent of UIF)
- SPB (Brazilian Payment System), PIX, TED, DOC
- Patrimônio de referência (regulatory capital), Basileia III

Extract all obligations, deadlines, and prohibitions. Translate obligation descriptions to English for the structured output, but preserve original Portuguese article references (e.g. "Art. 3º, §2º").

You output ONLY valid JSON. No prose."""

_PARSE_SYSTEM_AR = """You are an Argentine financial regulatory compliance expert specializing in BCRA (Banco Central de la República Argentina) and UIF (Unidad de Información Financiera) regulations.

Key Argentine regulatory concepts:
- Comunicación (Communication), Resolución (Resolution), Circular (Circular)
- Prevención de lavado de activos (AML), Conozca a su cliente (KYC)
- Entidades financieras (financial institutions), Cambiarias (FX entities)
- UIF, BCRA, CNV (securities regulator)
- SIDA, CENDEU (information systems)

You output ONLY valid JSON. No prose."""

_PARSE_SYSTEM_GENERIC = """You are an international financial regulatory compliance expert. Extract structured compliance obligations from the provided regulatory text.

You output ONLY valid JSON. No prose."""

# Mapping of Portuguese obligation type terms to canonical English types
BR_OBLIGATION_TYPE_MAP: dict[str, str] = {
    "prazo": "deadline",
    "obrigatoriedade": "requirement",
    "vedação": "prohibition",
    "vedacao": "prohibition",
    "restrição": "restriction",
    "restricao": "restriction",
    "comunicação": "reporting",
    "comunicacao": "reporting",
    "registro": "registration",
    "limite": "limit",
}


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


def _normalize_br_obligation_types(obligations: list[dict]) -> list[dict]:
    """Normalize Portuguese obligation type terms to canonical English values."""
    normalized = []
    for ob in obligations:
        ob = dict(ob)  # shallow copy to avoid mutating caller's data
        raw_type = str(ob.get("obligation_type", "")).lower().strip()
        if raw_type in BR_OBLIGATION_TYPE_MAP:
            ob["obligation_type"] = BR_OBLIGATION_TYPE_MAP[raw_type]
        normalized.append(ob)
    return normalized


class RegulatoryIntelligence:
    def __init__(self, orchestrator: AIOrchestrator | None = None):
        self.orch = orchestrator or get_orchestrator()

    @staticmethod
    def _build_system_prompt(country: str, regulator: str) -> str:
        """Return a country-aware system prompt for M1 regulatory parsing."""
        country_upper = country.upper()
        if country_upper == "BR":
            return _PARSE_SYSTEM_BR
        if country_upper == "AR":
            return _PARSE_SYSTEM_AR
        return _PARSE_SYSTEM_GENERIC

    async def parse_regulation(
        self,
        country: str,
        regulator: str,
        code: str,
        title: str,
        text: str,
        tenant_id: str,
        user_id: str | None = None,
        persist_as_global: bool = False,
    ) -> dict[str, Any]:
        """Convert raw regulatory text into structured obligations.

        persist_as_global=True stores the Regulation as shared reference data
        (tenant_id=NULL) instead of private to the calling tenant — use this
        for crawler-ingested regulator publications (BCRA, UIF, etc.).
        """
        truncated = text[:20000]  # leave room for context window

        system_prompt = self._build_system_prompt(country, regulator)

        result = await self.orch.infer(InferenceRequest(
            task=TaskType.REGULATORY_PARSING,
            system=system_prompt,
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
        reg_id = None
        if result.success and obligations_data:
            # Apply BR obligation type normalization before persisting
            if country.upper() == "BR":
                obligations_data = _normalize_br_obligation_types(obligations_data)
            persisted, reg_id = await self._persist_obligations(
                country=country, regulator=regulator, code=code,
                title=title, text=text,
                obligations_data=obligations_data,
                model_used=result.model_used,
                tenant_id=tenant_id,
                persist_as_global=persist_as_global,
            )

        # Index in Qdrant for RAG — best-effort, non-blocking
        if result.success and reg_id:
            try:
                from app.services.rag import get_rag
                await get_rag().index_regulation(
                    regulation_id=reg_id,
                    country=country,
                    regulator=regulator,
                    code=code,
                    title=title,
                    text=text,
                    tenant_id=tenant_id,
                )
            except Exception:
                pass

        # Add to compliance graph — best-effort, non-blocking
        if result.success and reg_id and obligations_data:
            try:
                from app.services.graph_service import get_graph
                await get_graph().add_regulation(
                    regulation_id=reg_id,
                    country=country,
                    regulator=regulator,
                    code=code,
                    title=title,
                    obligations=obligations_data,
                )
                # Wire sector APPLIES_TO edges after vertices are created
                await get_graph().link_obligation_to_sectors(
                    regulation_id=reg_id,
                    obligations_data=obligations_data,
                )
            except Exception:
                pass

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
        tenant_id: str | None = None,
        persist_as_global: bool = False,
    ) -> tuple[int, str | None]:
        """Upsert regulation + insert obligations. Returns (count, regulation_id).

        Regulation rows are tenant-scoped by default (tenant_id == caller's tenant);
        pass persist_as_global=True for crawler-ingested regulator publications that
        are shared reference data across all tenants (tenant_id = NULL).
        """
        from app.db.base import AsyncSessionLocal
        from app.db.models import (
            Regulation, Obligation,
            ObligationFrequency, ObligationSeverity,
        )
        from sqlalchemy import select, delete

        VALID_FREQ = {e.value for e in ObligationFrequency}
        VALID_SEV  = {e.value for e in ObligationSeverity}

        effective_tenant_id = None if persist_as_global else tenant_id

        try:
            async with AsyncSessionLocal() as session:
                # Find or create regulation — scoped to this tenant (or NULL for global)
                stmt = select(Regulation).where(
                    Regulation.country == country,
                    Regulation.regulator == regulator,
                    Regulation.code == code,
                    Regulation.tenant_id.is_(None) if effective_tenant_id is None
                    else Regulation.tenant_id == effective_tenant_id,
                )
                reg = (await session.execute(stmt)).scalar_one_or_none()

                if reg is None:
                    reg = Regulation(
                        id=uuid.uuid4(),
                        tenant_id=effective_tenant_id,
                        country=country,
                        regulator=regulator,
                        code=code,
                        title=title,
                        full_text=text[:50000] if text else None,
                        embedding_status="pending",
                    )
                    session.add(reg)
                    await session.flush()
                else:
                    # Refresh title and full_text on re-parse
                    reg.title = title
                    reg.full_text = text[:50000] if text else None

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
                return count, str(reg.id)
        except Exception:
            return 0, None

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
