"""
Global exception handlers — consistent JSON error shape for all unhandled errors.
Shape: {"error": str, "detail": str | None, "request_id": str | None}
"""
import structlog
from fastapi import Request
from fastapi.responses import JSONResponse

logger = structlog.get_logger(__name__)


async def http_exception_handler(request: Request, exc) -> JSONResponse:
    from fastapi.exceptions import HTTPException
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "request_id": request.headers.get("X-Request-ID"),
        },
        headers=getattr(exc, "headers", None) or {},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled_exception", exc_type=type(exc).__name__, exc=str(exc)[:200])
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "request_id": request.headers.get("X-Request-ID"),
        },
    )
