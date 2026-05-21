"""
Shared pytest fixtures for ComplianceOS backend tests.

Sets up environment variables before any module-level imports call get_settings(),
and provides a reusable TestClient with auth overridden.
"""

from __future__ import annotations

import os

# ── Patch env BEFORE any module that calls get_settings() at import time ──────
#
# pydantic-settings reads from os.environ when Settings() is instantiated.
# We need to set these before importing app.core.config so that the lru_cache
# singleton sees test values, not Docker-internal hostnames.
#
_TEST_ENV = {
    "APP_ENV": "development",
    "APP_SECRET_KEY": "test-secret-key-for-pytest-32bytes!!",
    "DATABASE_URL": "postgresql+asyncpg://complianceos:complianceos@localhost:5432/complianceos",
    "QDRANT_URL": "http://localhost:6333",
    "REDIS_URL": "redis://localhost:6379/0",
    "NVIDIA_API_KEY": "",
    "NVIDIA_BASE_URL": "https://integrate.api.nvidia.com/v1",
    "NVIDIA_RATE_LIMIT_RPM": "40",
    "DEFAULT_TENANT_ID": "polkorp",
    "CRAWLER_ENABLED": "false",
}

for _k, _v in _TEST_ENV.items():
    os.environ.setdefault(_k, _v)

# ── Now safe to import app modules ────────────────────────────────────────────

import pytest
from fastapi.testclient import TestClient

from app.core.auth import CurrentUser, get_current_user


# ── Auth override — bypass JWT for all integration tests ─────────────────────

def _override_auth() -> CurrentUser:
    return CurrentUser(user_id="test-user", tenant_id="polkorp", role="analyst")


def _override_auth_admin() -> CurrentUser:
    return CurrentUser(user_id="admin-user", tenant_id="polkorp", role="admin")


@pytest.fixture(scope="session")
def test_client() -> TestClient:
    """
    FastAPI TestClient with:
    - auth dependency overridden (no real JWT / DB needed)
    - lifespan events disabled (no real DB / Qdrant / scheduler)
    """
    from contextlib import asynccontextmanager
    from app.main import app

    @asynccontextmanager
    async def _noop_lifespan(app):
        yield

    app.router.lifespan_context = _noop_lifespan
    app.dependency_overrides[get_current_user] = _override_auth

    with TestClient(app, raise_server_exceptions=True) as client:
        yield client

    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture()
def analyst_client() -> TestClient:
    """TestClient that authenticates as a non-admin analyst for tenant 'acme'."""
    from app.main import app

    def _acme_analyst() -> CurrentUser:
        return CurrentUser(user_id="acme-analyst", tenant_id="acme", role="analyst")

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _noop_lifespan(app):
        yield

    app.router.lifespan_context = _noop_lifespan
    app.dependency_overrides[get_current_user] = _acme_analyst
    with TestClient(app, raise_server_exceptions=True) as client:
        yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture()
def admin_client() -> TestClient:
    """TestClient that authenticates as an admin user."""
    from app.main import app

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _noop_lifespan(app):
        yield

    app.router.lifespan_context = _noop_lifespan
    app.dependency_overrides[get_current_user] = _override_auth_admin
    with TestClient(app, raise_server_exceptions=True) as client:
        yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture()
def analyst_user() -> CurrentUser:
    return CurrentUser(user_id="test-user", tenant_id="polkorp", role="analyst")


@pytest.fixture()
def admin_user() -> CurrentUser:
    return CurrentUser(user_id="admin-user", tenant_id="polkorp", role="admin")
