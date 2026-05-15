"""
Attach a unique X-Request-ID to every request and response.
If the client sends X-Request-ID, use it (trust the upstream); otherwise generate one.
Also binds request_id and tenant_id to structlog contextvars for log correlation.
"""
import uuid
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = structlog.get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        tenant_id  = request.headers.get("X-Tenant-Id", "unknown")

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            tenant_id=tenant_id,
            path=request.url.path,
            method=request.method,
        )

        import time
        t0 = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - t0) * 1000, 1)

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = str(duration_ms)

        logger.info("request", status=response.status_code, duration_ms=duration_ms)
        return response
