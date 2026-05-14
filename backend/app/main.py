"""
ComplianceOS — FastAPI Application Entry Point
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api.v1.router import router as v1_router
from app.db.base import Base, engine


logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure all tables exist (idempotent — safe to run on every startup)
    import app.db.models  # noqa: F401 — registers all domain models with Base.metadata
    import app.core.audit  # noqa: F401 — registers AuditLogEntry with Base.metadata
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("DB schema verified")

    # Wire the immutable audit log into the AI orchestrator
    from app.core.audit import append_audit
    from app.db.base import AsyncSessionLocal
    from app.services.ai_orchestrator import get_orchestrator

    async def _audit_callback(payload: dict):
        async with AsyncSessionLocal() as session:
            await append_audit(
                session=session,
                tenant_id=payload.get("tenant_id", "unknown"),
                event_type=f"ai_inference:{payload.get('task', 'unknown')}",
                payload=payload,
                user_id=payload.get("user_id"),
            )

    get_orchestrator().set_audit_callback(_audit_callback)
    logger.info("Audit log wired to AI orchestrator")

    # Ensure Qdrant RAG collection exists (idempotent)
    try:
        from app.services.rag import get_rag
        await get_rag().ensure_collection()
        logger.info("Qdrant RAG collection ready")
    except Exception as e:
        logger.warning("Qdrant not available at startup: %s", e)

    logger.info(f"Starting {settings.app_name} ({settings.app_env})")
    logger.info(f"NVIDIA configured: {settings.has_nvidia}")
    if not settings.has_nvidia:
        logger.warning(
            "NVIDIA_API_KEY not set — AI endpoints will return 'missing key' errors. "
            "Get a key at https://build.nvidia.com and add it to .env"
        )

    # Start regulatory crawler scheduler (BCRA every 6h, UIF every 12h)
    _scheduler = None
    if settings.crawler_enabled:
        from app.modules.crawler.scheduler import start_scheduler
        _scheduler = start_scheduler()

    yield

    if _scheduler:
        _scheduler.shutdown()
    logger.info("Shutting down")


app = FastAPI(
    title=settings.app_name,
    description="AI-native Compliance Operating System for LATAM Regulated Industries",
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Audit-ID"],
)


app.include_router(v1_router)


@app.get("/")
async def root():
    return {
        "service": settings.app_name,
        "version": "0.2.0",
        "environment": settings.app_env,
        "docs": "/docs",
        "api": "/api/v1",
    }
