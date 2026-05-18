"""
ComplianceOS — API v1
======================
REST endpoints organized by module. Multi-tenant aware.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field

from app.middleware.rate_limit import limiter

from app.modules.regulatory.engine import RegulatoryIntelligence
from app.modules.copilot.copilot import ComplianceCopilot
from app.modules.kyc_aml.engine import KYCAMLEngine
from app.modules.monitoring.engine import MonitoringEngine
from app.modules.governance.engine import AIGovernance
from app.modules.evidence.engine import EvidenceEngine
from app.services.ai_orchestrator import MODELS, ROUTING
from app.core.auth import (
    CurrentUser, get_current_user, require_admin,
    create_access_token, create_refresh_token, decode_refresh_token,
    hash_password, verify_password,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from fastapi import UploadFile, File, Query


router = APIRouter(prefix="/api/v1", tags=["v1"])


# ═══════════════════════════════════════════════════════════════════
# Tenant / user resolver — JWT-first, X-Tenant-Id dev fallback
# ═══════════════════════════════════════════════════════════════════

async def get_tenant_id(user: CurrentUser = Depends(get_current_user)) -> str:
    return user.tenant_id


async def get_user_id(user: CurrentUser = Depends(get_current_user)) -> str | None:
    return user.user_id


# ═══════════════════════════════════════════════════════════════════
# Health & meta
# ═══════════════════════════════════════════════════════════════════

@router.get("/health")
async def health():
    return {"status": "ok", "version": "0.2.0"}


@router.get("/health/detailed")
async def health_detailed():
    """
    Deep health check: verifies connectivity to Postgres, Qdrant, and Redis.
    Returns per-service status. Never raises — always returns 200 with statuses.
    Safe to use as a liveness + readiness probe.
    """
    import time
    checks = {}

    # Postgres
    t = time.perf_counter()
    try:
        from app.db.base import AsyncSessionLocal
        from sqlalchemy import text
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        checks["postgres"] = {"status": "ok", "latency_ms": round((time.perf_counter()-t)*1000,1)}
    except Exception as e:
        checks["postgres"] = {"status": "error", "error": str(e)[:100]}

    # Qdrant
    t = time.perf_counter()
    try:
        from qdrant_client import AsyncQdrantClient
        from app.core.config import get_settings
        client = AsyncQdrantClient(url=get_settings().qdrant_url)
        await client.get_collections()
        checks["qdrant"] = {"status": "ok", "latency_ms": round((time.perf_counter()-t)*1000,1)}
    except Exception as e:
        checks["qdrant"] = {"status": "error", "error": str(e)[:100]}

    # Redis
    t = time.perf_counter()
    try:
        import redis.asyncio as aioredis
        from app.core.config import get_settings
        r = aioredis.from_url(get_settings().redis_url, socket_connect_timeout=3)
        await r.ping()
        await r.aclose()
        checks["redis"] = {"status": "ok", "latency_ms": round((time.perf_counter()-t)*1000,1)}
    except Exception as e:
        checks["redis"] = {"status": "error", "error": str(e)[:100]}

    overall = "ok" if all(v.get("status") == "ok" for v in checks.values()) else "degraded"
    return {"status": overall, "version": "0.2.0", "services": checks}


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
@limiter.limit("30/minute")
async def parse_regulation(
    request: Request,
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
@limiter.limit("30/minute")
async def copilot_ask(
    request: Request,
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
@limiter.limit("20/minute")
async def kyc_screen(
    request: Request,
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
@limiter.limit("20/minute")
async def monitor_transactions(
    request: Request,
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


# ═══════════════════════════════════════════════════════════════════
# AUTH
# ═══════════════════════════════════════════════════════════════════

class RegisterRequest(BaseModel):
    email: str
    password: str = Field(..., min_length=8)
    role: str = "analyst"


@router.post("/auth/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Exchange email + password for a JWT access token."""
    from app.db.base import AsyncSessionLocal
    from app.db.models import User
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.email == form_data.username, User.is_active == True)
        user = (await session.execute(stmt)).scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(
        user_id=str(user.id),
        tenant_id=user.tenant_id,
        role=user.role.value,
    )
    refresh = create_refresh_token(
        user_id=str(user.id),
        tenant_id=user.tenant_id,
        role=user.role.value,
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "refresh_token": refresh,
    }


@router.post("/auth/register", status_code=201)
async def register_user(
    req: RegisterRequest,
    admin: CurrentUser = Depends(require_admin),
):
    """Register a new user (admin only)."""
    from app.db.base import AsyncSessionLocal
    from app.db.models import User, UserRole
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        existing = (await session.execute(select(User).where(User.email == req.email))).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=409, detail="Email already registered")

        try:
            role = UserRole(req.role)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid role: {req.role}")

        new_user = User(
            tenant_id=admin.tenant_id,
            email=req.email,
            hashed_password=hash_password(req.password),
            role=role,
        )
        session.add(new_user)
        await session.commit()
        return {"success": True, "user_id": str(new_user.id), "email": new_user.email, "role": role.value}


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/auth/refresh")
async def refresh_access_token(req: RefreshRequest):
    """Exchange a valid refresh token for a new access token."""
    claims = decode_refresh_token(req.refresh_token)
    token = create_access_token(
        user_id=claims["sub"],
        tenant_id=claims["tenant_id"],
        role=claims.get("role", "analyst"),
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


# ═══════════════════════════════════════════════════════════════════
# RAG
# ═══════════════════════════════════════════════════════════════════

@router.get("/rag/status")
async def rag_status():
    """Qdrant collection info and document count."""
    from app.services.rag import get_rag, COLLECTION
    try:
        client = get_rag()._get_qdrant()
        info = await client.get_collection(COLLECTION)
        return {
            "collection": COLLECTION,
            "vector_count": info.vectors_count,
            "indexed_vectors": info.indexed_vectors_count,
            "status": info.status,
        }
    except Exception as e:
        return {"error": str(e)}


@router.post("/rag/reindex")
async def rag_reindex(
    tenant_id: str = Depends(get_tenant_id),
    admin: CurrentUser = Depends(require_admin),
):
    """Re-embed all regulations from DB into Qdrant (admin only)."""
    from app.services.rag import get_rag
    return await get_rag().index_all_regulations(tenant_id=tenant_id)


# ═══════════════════════════════════════════════════════════════════
# CRAWLER
# ═══════════════════════════════════════════════════════════════════

@router.get("/crawler/status")
async def crawler_status():
    """Crawler schedule and last-run stats."""
    from app.core.config import get_settings
    s = get_settings()
    return {
        "enabled": s.crawler_enabled,
        "bcra_url": s.crawler_bcra_url,
        "uif_url": s.crawler_uif_url,
        "schedule": {"bcra_interval_hours": 6, "uif_interval_hours": 12, "bacen_interval_hours": 8},
        "jobs": {
            "bcra": {"interval_hours": 6, "country": "AR"},
            "uif": {"interval_hours": 12, "country": "AR"},
            "bacen": {"interval_hours": 8, "country": "BR"},
        },
    }


@router.post("/crawler/run-now")
@limiter.limit("5/minute")
async def crawler_run_now(
    request: Request,
    regulator: str | None = Query(default=None, description="bcra | uif | all"),
    tenant_id: str = Depends(get_tenant_id),
    admin: CurrentUser = Depends(require_admin),
):
    """Trigger an immediate crawler run (admin only)."""
    from app.modules.crawler.scheduler import run_bcra, run_uif, run_bacen, run_all
    reg = (regulator or "all").lower()
    if reg == "bcra":
        return await run_bcra(tenant_id=tenant_id)
    elif reg == "uif":
        return await run_uif(tenant_id=tenant_id)
    elif reg == "bacen":
        return await run_bacen(tenant_id=tenant_id)
    else:
        return await run_all(tenant_id=tenant_id)


# ═══════════════════════════════════════════════════════════════════
# COMPLIANCE GRAPH
# ═══════════════════════════════════════════════════════════════════

@router.get("/graph/stats")
async def graph_stats():
    """High-level compliance graph statistics (vertex + edge counts by type)."""
    from app.services.graph_service import get_graph
    return await get_graph().graph_stats()


@router.get("/graph/regulation/{regulation_id}")
async def graph_regulation_subgraph(regulation_id: str):
    """Return the compliance subgraph rooted at a regulation (BFS depth 3)."""
    from app.services.graph_service import get_graph
    return await get_graph().get_regulation_subgraph(regulation_id=regulation_id)


@router.get("/graph/entity/{entity_id}/obligations")
async def graph_entity_obligations(entity_id: str):
    """Return all obligations that apply to a given entity in the graph."""
    from app.services.graph_service import get_graph
    return await get_graph().get_obligations_for_entity(entity_id=entity_id)


class RegisterEntityRequest(BaseModel):
    name: str = Field(..., examples=["Acme PSP S.A."])
    entity_type: str = Field(..., examples=["company"])
    sectors: list[str] = Field(default_factory=list, examples=[["PSP", "bank"]])
    properties: dict[str, Any] = Field(default_factory=dict)


@router.post("/graph/entities", status_code=201)
async def register_entity(
    req: RegisterEntityRequest,
    tenant_id: str = Depends(get_tenant_id),
    _user: CurrentUser = Depends(get_current_user),
):
    """
    Register a company or individual as a compliance entity and auto-link it
    to all obligations that apply to its declared sectors via APPLIES_TO edges.
    """
    from app.services.graph_service import get_graph
    return await get_graph().register_entity(
        tenant_id=tenant_id,
        name=req.name,
        entity_type=req.entity_type,
        sectors=req.sectors,
        properties=req.properties,
    )


@router.get("/graph/entities")
async def list_entities(
    tenant_id: str = Depends(get_tenant_id),
    _user: CurrentUser = Depends(get_current_user),
):
    """List all compliance entities registered for this tenant."""
    from app.db.base import AsyncSessionLocal
    from app.db.models import ComplianceEntity
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        stmt = select(ComplianceEntity).where(ComplianceEntity.tenant_id == tenant_id)
        entities = (await session.execute(stmt)).scalars().all()

    return [
        {
            "entity_id": str(e.id),
            "name": e.name,
            "entity_type": e.entity_type.value,
            "sectors": e.sectors or [],
        }
        for e in entities
    ]


# ═══════════════════════════════════════════════════════════════════
# TENANT MANAGEMENT
# ═══════════════════════════════════════════════════════════════════

class TenantCreate(BaseModel):
    name: str
    slug: str
    data_residency_policy: str = "global"


class TenantUpdate(BaseModel):
    name: str | None = None
    data_residency_policy: str | None = None
    is_active: bool | None = None


@router.post("/tenants", status_code=201)
async def create_tenant(
    req: TenantCreate,
    admin: CurrentUser = Depends(require_admin),
):
    """Create a new tenant (admin only)."""
    from app.db.base import AsyncSessionLocal
    from app.db.models import Tenant
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        existing = (
            await session.execute(select(Tenant).where(Tenant.slug == req.slug))
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=409, detail="Slug already exists")

        tenant = Tenant(
            name=req.name,
            slug=req.slug,
            data_residency_policy=req.data_residency_policy,
        )
        session.add(tenant)
        await session.commit()
        await session.refresh(tenant)
        return {
            "id": tenant.id,
            "name": tenant.name,
            "slug": tenant.slug,
            "data_residency_policy": tenant.data_residency_policy,
            "is_active": tenant.is_active,
            "created_at": tenant.created_at,
        }


@router.get("/tenants")
async def list_tenants(
    admin: CurrentUser = Depends(require_admin),
):
    """List all tenants (admin only)."""
    from app.db.base import AsyncSessionLocal
    from app.db.models import Tenant
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        tenants = (await session.execute(select(Tenant))).scalars().all()

    return [
        {
            "id": t.id,
            "name": t.name,
            "slug": t.slug,
            "data_residency_policy": t.data_residency_policy,
            "is_active": t.is_active,
            "created_at": t.created_at,
        }
        for t in tenants
    ]


@router.get("/tenants/{slug}")
async def get_tenant(
    slug: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Get tenant by slug.
    Non-admin users may only retrieve their own tenant.
    """
    if not current_user.is_admin and current_user.tenant_id != slug:
        raise HTTPException(status_code=403, detail="Access denied: not your tenant")

    from app.db.base import AsyncSessionLocal
    from app.db.models import Tenant
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        tenant = (
            await session.execute(select(Tenant).where(Tenant.slug == slug))
        ).scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    return {
        "id": tenant.id,
        "name": tenant.name,
        "slug": tenant.slug,
        "data_residency_policy": tenant.data_residency_policy,
        "is_active": tenant.is_active,
        "created_at": tenant.created_at,
    }


@router.patch("/tenants/{slug}")
async def update_tenant(
    slug: str,
    req: TenantUpdate,
    admin: CurrentUser = Depends(require_admin),
):
    """Partial update of a tenant (admin only)."""
    from app.db.base import AsyncSessionLocal
    from app.db.models import Tenant
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        tenant = (
            await session.execute(select(Tenant).where(Tenant.slug == slug))
        ).scalar_one_or_none()

        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        if req.name is not None:
            tenant.name = req.name
        if req.data_residency_policy is not None:
            tenant.data_residency_policy = req.data_residency_policy
        if req.is_active is not None:
            tenant.is_active = req.is_active

        await session.commit()
        await session.refresh(tenant)
        return {
            "id": tenant.id,
            "name": tenant.name,
            "slug": tenant.slug,
            "data_residency_policy": tenant.data_residency_policy,
            "is_active": tenant.is_active,
            "created_at": tenant.created_at,
        }
