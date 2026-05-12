"""
ComplianceOS — API v1
======================
REST endpoints organized by module. Multi-tenant aware.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field

from app.modules.regulatory.engine import RegulatoryIntelligence
from app.modules.copilot.copilot import ComplianceCopilot
from app.modules.kyc_aml.engine import KYCAMLEngine
from app.modules.monitoring.engine import MonitoringEngine
from app.modules.governance.engine import AIGovernance
from app.modules.evidence.engine import EvidenceEngine
from app.services.ai_orchestrator import MODELS, ROUTING
from fastapi import UploadFile, File, Query


router = APIRouter(prefix="/api/v1", tags=["v1"])


# ═══════════════════════════════════════════════════════════════════
# Tenant resolver (header-based for now; JWT in production)
# ═══════════════════════════════════════════════════════════════════

async def get_tenant_id(x_tenant_id: str = Header(default="polkorp")) -> str:
    return x_tenant_id


async def get_user_id(x_user_id: str = Header(default=None)) -> str | None:
    return x_user_id


# ═══════════════════════════════════════════════════════════════════
# Health & meta
# ═══════════════════════════════════════════════════════════════════

@router.get("/health")
async def health():
    return {"status": "ok", "version": "0.2.0"}


@router.get("/meta/models")
async def list_models():
    """Available AI models and their roles."""
    return {
        "models": [
            {
                "key": k,
                "id": m.id,
                "provider": m.provider,
                "free_endpoint": m.free_endpoint,
                "context_window": m.context_window,
                "benchmark_quality": m.benchmark_quality,
                "strengths": list(m.strengths),
                "notes": m.notes,
            }
            for k, m in MODELS.items()
        ],
        "routing": {task.value: chain for task, chain in ROUTING.items()},
    }


# ═══════════════════════════════════════════════════════════════════
# M1 — Regulatory Intelligence
# ═══════════════════════════════════════════════════════════════════

class ParseRegulationRequest(BaseModel):
    country: str = Field(..., examples=["AR"])
    regulator: str = Field(..., examples=["BCRA"])
    code: str = Field(..., examples=["Comunicación A 7825"])
    title: str
    text: str


class MapCrossBorderRequest(BaseModel):
    obligation_topic: str = Field(..., examples=["Suspicious Activity Reporting"])
    countries: list[str] = Field(..., examples=[["AR", "BR", "MX", "CO", "CL"]])


@router.post("/regulatory/parse")
async def parse_regulation(
    req: ParseRegulationRequest,
    tenant_id: str = Depends(get_tenant_id),
    user_id: str | None = Depends(get_user_id),
):
    engine = RegulatoryIntelligence()
    return await engine.parse_regulation(
        country=req.country, regulator=req.regulator,
        code=req.code, title=req.title, text=req.text,
        tenant_id=tenant_id, user_id=user_id,
    )


@router.post("/regulatory/map")
async def map_cross_border(
    req: MapCrossBorderRequest,
    tenant_id: str = Depends(get_tenant_id),
    user_id: str | None = Depends(get_user_id),
):
    engine = RegulatoryIntelligence()
    return await engine.map_cross_border(
        obligation_topic=req.obligation_topic,
        countries=req.countries,
        tenant_id=tenant_id, user_id=user_id,
    )


# ═══════════════════════════════════════════════════════════════════
# M2 — Copilot
# ═══════════════════════════════════════════════════════════════════

class CopilotAskRequest(BaseModel):
    question: str
    context: dict[str, Any] | None = None
    deep_mode: bool = False
    output_schema: dict | None = None


class ExpansionAnalysisRequest(BaseModel):
    from_country: str
    to_country: str
    business_model: str = Field(..., examples=["digital wallet PSP"])


@router.post("/copilot/ask")
async def copilot_ask(
    req: CopilotAskRequest,
    tenant_id: str = Depends(get_tenant_id),
    user_id: str | None = Depends(get_user_id),
):
    copilot = ComplianceCopilot()
    return await copilot.ask(
        question=req.question,
        context=req.context,
        deep_mode=req.deep_mode,
        output_schema=req.output_schema,
        tenant_id=tenant_id, user_id=user_id,
    )


@router.post("/copilot/expansion")
async def expansion_analysis(
    req: ExpansionAnalysisRequest,
    tenant_id: str = Depends(get_tenant_id),
):
    copilot = ComplianceCopilot()
    return await copilot.expansion_analysis(
        from_country=req.from_country,
        to_country=req.to_country,
        business_model=req.business_model,
        tenant_id=tenant_id,
    )


# ═══════════════════════════════════════════════════════════════════
# M3 — KYC/AML
# ═══════════════════════════════════════════════════════════════════

class KYCScreenRequest(BaseModel):
    customer_data: dict[str, Any]


class SanctionsScreenRequest(BaseModel):
    subject_data: dict[str, Any]


@router.post("/kyc/screen")
async def kyc_screen(
    req: KYCScreenRequest,
    tenant_id: str = Depends(get_tenant_id),
    user_id: str | None = Depends(get_user_id),
):
    engine = KYCAMLEngine()
    return await engine.screen_customer(
        customer_data=req.customer_data,
        tenant_id=tenant_id, user_id=user_id,
    )


@router.post("/kyc/sanctions")
async def sanctions_screen(
    req: SanctionsScreenRequest,
    tenant_id: str = Depends(get_tenant_id),
    user_id: str | None = Depends(get_user_id),
):
    engine = KYCAMLEngine()
    return await engine.sanctions_screen(
        subject_data=req.subject_data,
        tenant_id=tenant_id, user_id=user_id,
    )


# ═══════════════════════════════════════════════════════════════════
# M4 — Monitoring
# ═══════════════════════════════════════════════════════════════════

class TransactionAnalysisRequest(BaseModel):
    transaction_summary: dict[str, Any]


class PolicyDriftRequest(BaseModel):
    policy_description: str
    observed_behavior: dict[str, Any]


@router.post("/monitoring/transactions")
async def monitor_transactions(
    req: TransactionAnalysisRequest,
    tenant_id: str = Depends(get_tenant_id),
):
    engine = MonitoringEngine()
    return await engine.analyze_transactions(
        transaction_summary=req.transaction_summary,
        tenant_id=tenant_id,
    )


@router.post("/monitoring/drift")
async def detect_drift(
    req: PolicyDriftRequest,
    tenant_id: str = Depends(get_tenant_id),
):
    engine = MonitoringEngine()
    return await engine.detect_drift(
        policy_description=req.policy_description,
        observed_behavior=req.observed_behavior,
        tenant_id=tenant_id,
    )


# ═══════════════════════════════════════════════════════════════════
# M5 — AI Governance
# ═══════════════════════════════════════════════════════════════════

class AuditRequest(BaseModel):
    original_question: str
    ai_response: str
    factual_context: str


class InjectionCheckRequest(BaseModel):
    text: str


@router.post("/governance/audit")
async def audit_ai_response(
    req: AuditRequest,
    tenant_id: str = Depends(get_tenant_id),
    user_id: str | None = Depends(get_user_id),
):
    governance = AIGovernance()
    return await governance.audit_response(
        original_question=req.original_question,
        ai_response=req.ai_response,
        factual_context=req.factual_context,
        tenant_id=tenant_id, user_id=user_id,
    )


@router.post("/governance/check-injection")
async def check_injection(req: InjectionCheckRequest):
    governance = AIGovernance()
    return governance.detect_prompt_injection(req.text)


# ═══════════════════════════════════════════════════════════════════
# M6 — Evidence Automation
# ═══════════════════════════════════════════════════════════════════

@router.post("/evidence/extract")
async def extract_evidence(
    file: UploadFile = File(..., description="Regulator PDF to extract compliance data from"),
    regulator: str | None = Query(default=None, description="Regulator hint (e.g. BCRA, UIF, BACEN)"),
    country: str | None = Query(default=None, description="2-letter ISO country code"),
    tenant_id: str = Depends(get_tenant_id),
    user_id: str | None = Depends(get_user_id),
):
    """
    Extract structured compliance obligations from a regulator PDF.

    Pipeline: PDF → text extraction (PyMuPDF) → LLM structured parsing → chain of custody.
    Returns extracted obligations, metadata, and a tamper-evident custody hash.
    """
    pdf_bytes = await file.read()
    if not pdf_bytes:
        return {"success": False, "error": "Empty file"}

    context = {}
    if regulator:
        context["regulator"] = regulator
    if country:
        context["country"] = country

    engine = EvidenceEngine()
    return await engine.extract_from_pdf(
        pdf_bytes=pdf_bytes,
        filename=file.filename or "document.pdf",
        tenant_id=tenant_id,
        regulation_context=context or None,
        user_id=user_id,
    )


@router.get("/evidence/documents")
async def list_evidence_documents(
    limit: int = Query(default=20, ge=1, le=100),
    tenant_id: str = Depends(get_tenant_id),
):
    """List evidence documents extracted for this tenant."""
    engine = EvidenceEngine()
    return await engine.list_documents(tenant_id=tenant_id, limit=limit)


@router.get("/evidence/documents/{document_id}")
async def get_evidence_document(
    document_id: str,
    tenant_id: str = Depends(get_tenant_id),
):
    """Retrieve a specific evidence document with full structured data."""
    engine = EvidenceEngine()
    return await engine.get_document(document_id=document_id, tenant_id=tenant_id)
