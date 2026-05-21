"""Tests for health endpoints and middleware."""
from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.auth import CurrentUser, get_current_user


# ── Helpers ────────────────────────────────────────────────────────────────────


def _analyst_user() -> CurrentUser:
    return CurrentUser(user_id="test-user", tenant_id="polkorp", role="analyst")


def _make_test_client() -> TestClient:
    from app.main import app

    @asynccontextmanager
    async def _noop_lifespan(app):
        yield

    app.router.lifespan_context = _noop_lifespan
    app.dependency_overrides[get_current_user] = _analyst_user
    return TestClient(app, raise_server_exceptions=True)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def client() -> TestClient:
    with _make_test_client() as c:
        yield c


# ── Basic health tests ────────────────────────────────────────────────────────


def test_health_basic(client):
    """Basic health check always returns ok."""
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_request_id_generated(client):
    """X-Request-ID header is present on every response."""
    resp = client.get("/api/v1/health")
    assert "X-Request-ID" in resp.headers


def test_request_id_echoed(client):
    """If client sends X-Request-ID, it is echoed back."""
    resp = client.get("/api/v1/health", headers={"X-Request-ID": "my-id-123"})
    assert resp.headers.get("X-Request-ID") == "my-id-123"


def test_response_time_header(client):
    """X-Response-Time-Ms header is numeric."""
    resp = client.get("/api/v1/health")
    assert float(resp.headers["X-Response-Time-Ms"]) >= 0


# ── Detailed health test ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_health_detailed_shape():
    """health/detailed returns services dict with postgres/qdrant/redis keys."""
    # Mock all three service checks to return ok
    with patch("app.db.base.AsyncSessionLocal") as mock_db, \
         patch("qdrant_client.AsyncQdrantClient") as mock_qdrant, \
         patch("redis.asyncio.from_url") as mock_redis:

        # Setup mocks
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.execute = AsyncMock()
        mock_db.return_value = mock_session

        mock_qdrant_inst = AsyncMock()
        mock_qdrant_inst.get_collections = AsyncMock(return_value=AsyncMock(collections=[]))
        mock_qdrant.return_value = mock_qdrant_inst

        mock_redis_inst = AsyncMock()
        mock_redis_inst.ping = AsyncMock()
        mock_redis_inst.aclose = AsyncMock()
        mock_redis.return_value = mock_redis_inst

        from app.api.v1.router import health_detailed
        result = await health_detailed()
        assert "services" in result
        assert "postgres" in result["services"]
        assert "qdrant" in result["services"]
        assert "redis" in result["services"]
