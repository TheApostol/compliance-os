"""
ComplianceOS — FastAPI Application Entry Point
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.errors import http_exception_handler, unhandled_exception_handler
from app.api.v1.router import router as v1_router
from app.api.v1.m7_m8_router import router as m7_m8_router
from app.db.base import Base, engine
from app.middleware.rate_limit import limiter
from app.middleware.metrics import setup_metrics

configure_logging()

logger = logging.getLogger(__name__)
settings = get_settings()


async def _background_init():
    """Run DB and Qdrant init after the server is already accepting requests."""
    await asyncio.sleep(2)  # let the server fully start first

    # DB schema
    import app.db.models  # noqa: F401
    import app.core.audit  # noqa: F401
    import app.modules.workflows.models  # noqa: F401
    for attempt in range(5):
        try:
            async with asyncio.timeout(20):
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)
            logger.info("DB schema verified")
            break
        except Exception as e:
            wait = 5 * (attempt + 1)
            logger.warning("DB init attempt %d failed (%s) — retrying in %ds", attempt + 1, e, wait)
            await asyncio.sleep(wait)
    else:
        logger.error("DB schema init failed after 5 attempts — DB-dependent endpoints will error")

    # Qdrant RAG collection
    try:
        async with asyncio.timeout(15):
            from app.services.rag import get_rag
            await get_rag().ensure_collection()
        logger.info("Qdrant RAG collection ready")
    except Exception as e:
        logger.warning("Qdrant not available at startup: %s", e)

    # Create default admin user if none exists
    try:
        import os
        from app.db.base import AsyncSessionLocal
        from app.db.models import User, Tenant, UserRole
        from app.core.auth import hash_password
        from sqlalchemy import select

        admin_email = os.environ.get("ADMIN_EMAIL", "admin@complianceos.io")
        admin_password = os.environ.get("ADMIN_PASSWORD", "ComplianceOS2026!")

        async with AsyncSessionLocal() as session:
            existing = (await session.execute(select(User).limit(1))).scalar_one_or_none()
            if not existing:
                tenant = (await session.execute(
                    select(Tenant).where(Tenant.slug == settings.default_tenant_id)
                )).scalar_one_or_none()
                if not tenant:
                    tenant = Tenant(
                        slug=settings.default_tenant_id,
                        name=settings.default_tenant_name,
                        sector="multi",
                        jurisdictions=["AR", "BR", "MX"],
                        data_residency_policy={"ai_providers_allowed": ["nvidia", "anthropic"]},
                    )
                    session.add(tenant)
                    await session.flush()

                user = User(
                    email=admin_email,
                    hashed_password=hash_password(admin_password),
                    role=UserRole.ADMIN,
                    tenant_id=tenant.slug,
                    is_active=True,
                )
                session.add(user)
                await session.commit()
                logger.info("Default admin user created: %s", admin_email)
    except Exception as e:
        logger.warning("Could not create default admin user: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Wire audit log into AI orchestrator (no I/O — always safe)
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

    # Start crawler scheduler
    _scheduler = None
    if settings.crawler_enabled:
        try:
            from app.modules.crawler.scheduler import start_scheduler
            _scheduler = start_scheduler()
        except Exception as e:
            logger.warning("Crawler scheduler failed to start: %s", e)

    # DB + Qdrant init runs in background — healthcheck passes immediately
    asyncio.create_task(_background_init())

    logger.info(f"Starting {settings.app_name} ({settings.app_env})")
    logger.info(f"NVIDIA configured: {settings.has_nvidia}")

    yield

    if _scheduler:
        _scheduler.shutdown()
    logger.info("Shutting down")


def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=429,
        content={"error": "rate limit exceeded", "request_id": request_id},
    )


app = FastAPI(
    title=settings.app_name,
    description="AI-native Compliance Operating System for LATAM Regulated Industries",
    version="0.3.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Audit-ID"],
)

from app.middleware.request_id import RequestIDMiddleware  # noqa: E402
app.add_middleware(RequestIDMiddleware)

app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

setup_metrics(app)

app.include_router(v1_router)
app.include_router(m7_m8_router)


@app.get("/")
async def root():
    return {
        "service": settings.app_name,
        "version": "0.3.0",
        "environment": settings.app_env,
        "docs": "/docs",
        "api": "/api/v1",
        "modules": ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8"],
    }
