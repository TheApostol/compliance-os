"""
API Key tests — generation, validation, and CRUD endpoints.

All DB calls are mocked so no Docker / live database is required.
"""

from __future__ import annotations

import hashlib
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.api_key_service import generate_key


# ─────────────────────────────────────────────────────────────────────────────
# 1. Key format
# ─────────────────────────────────────────────────────────────────────────────


def test_generate_key_format():
    """Key must start with 'csk_', prefix is first 8 chars, hash is SHA-256 hex."""
    full_key, prefix, hashed = generate_key()

    assert full_key.startswith("csk_"), f"Expected 'csk_' prefix, got: {full_key[:8]!r}"
    assert prefix == full_key[:8], "Prefix must be the first 8 characters of the full key"
    assert hashed == hashlib.sha256(full_key.encode()).hexdigest()
    # SHA-256 hex is always 64 lowercase hex characters
    assert len(hashed) == 64
    assert all(c in "0123456789abcdef" for c in hashed)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Key uniqueness
# ─────────────────────────────────────────────────────────────────────────────


def test_generate_key_unique():
    """Two consecutive calls must produce different keys and hashes."""
    key1, prefix1, hash1 = generate_key()
    key2, prefix2, hash2 = generate_key()

    assert key1 != key2
    assert hash1 != hash2


# ─────────────────────────────────────────────────────────────────────────────
# 3. Validate active key
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_validate_key_active():
    """An active, non-expired key returns a dict with tenant_id."""
    full_key, _, hashed = generate_key()

    mock_key_row = SimpleNamespace(
        id="key-uuid-001",
        tenant_id="polkorp",
        scopes=["read", "write"],
        is_active=True,
        expires_at=None,
        hashed_key=hashed,
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_key_row

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_session_local = MagicMock(return_value=mock_session)

    with patch("app.db.base.AsyncSessionLocal", mock_session_local):
        from app.services.api_key_service import validate_key

        result = await validate_key(full_key)

    assert result is not None
    assert result["tenant_id"] == "polkorp"
    assert result["scopes"] == ["read", "write"]
    assert result["key_id"] == "key-uuid-001"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Validate expired key
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_validate_key_expired():
    """A key whose expires_at is in the past returns None."""
    full_key, _, hashed = generate_key()

    mock_key_row = SimpleNamespace(
        id="key-uuid-002",
        tenant_id="polkorp",
        scopes=["read"],
        is_active=True,
        expires_at=datetime.now(tz=timezone.utc) - timedelta(days=1),  # yesterday
        hashed_key=hashed,
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_key_row

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_session_local = MagicMock(return_value=mock_session)

    with patch("app.db.base.AsyncSessionLocal", mock_session_local):
        from app.services.api_key_service import validate_key

        result = await validate_key(full_key)

    assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# 5. Validate inactive key
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_validate_key_inactive():
    """A key with is_active=False is not returned by the DB query (filtered out)."""
    full_key, _, _ = generate_key()

    # The SELECT filters WHERE is_active = True, so an inactive key returns None
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None  # DB returns nothing

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_session_local = MagicMock(return_value=mock_session)

    with patch("app.db.base.AsyncSessionLocal", mock_session_local):
        from app.services.api_key_service import validate_key

        result = await validate_key(full_key)

    assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# 6. Validate unknown key
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_validate_key_not_found():
    """An unrecognised key returns None."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_session_local = MagicMock(return_value=mock_session)

    with patch("app.db.base.AsyncSessionLocal", mock_session_local):
        from app.services.api_key_service import validate_key

        result = await validate_key("csk_totally_unknown_key")

    assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# 7. POST /api-keys endpoint
# ─────────────────────────────────────────────────────────────────────────────


def test_create_key_endpoint():
    """POST /api-keys returns a key starting with 'csk_' and a one-time warning."""
    from app.main import app
    from app.core.auth import CurrentUser, get_current_user
    from fastapi.testclient import TestClient

    def _auth():
        return CurrentUser(user_id="test-user", tenant_id="polkorp", role="analyst")

    # Build a fake APIKey object returned after session.refresh()
    fake_api_key = SimpleNamespace(
        id="new-key-uuid",
        key_prefix="csk_test",
        name="CI pipeline",
        scopes=["read"],
        expires_at=None,
        created_at=datetime(2026, 5, 18, 12, 0, 0, tzinfo=timezone.utc),
    )

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock(side_effect=lambda obj: None)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    # Patch AsyncSessionLocal and make refresh populate the object
    def _fake_refresh(obj):
        obj.id = fake_api_key.id
        obj.key_prefix = fake_api_key.key_prefix
        obj.name = fake_api_key.name
        obj.scopes = fake_api_key.scopes
        obj.expires_at = fake_api_key.expires_at
        obj.created_at = fake_api_key.created_at

    mock_session.refresh = AsyncMock(side_effect=_fake_refresh)

    mock_session_local = MagicMock(return_value=mock_session)

    @asynccontextmanager
    async def _noop_lifespan(app):
        yield

    app.router.lifespan_context = _noop_lifespan
    app.dependency_overrides[get_current_user] = _auth

    with patch("app.db.base.AsyncSessionLocal", mock_session_local):
        with TestClient(app, raise_server_exceptions=True) as client:
            response = client.post(
                "/api/v1/api-keys",
                json={"name": "CI pipeline", "scopes": ["read"]},
            )

    app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["key"].startswith("csk_"), f"Expected key starting with 'csk_', got: {data['key'][:10]!r}"
    assert "warning" in data
    assert "not be shown again" in data["warning"]
    assert data["name"] == "CI pipeline"


# ─────────────────────────────────────────────────────────────────────────────
# 8. DELETE /api-keys/{key_id} — wrong tenant → 404
# ─────────────────────────────────────────────────────────────────────────────


def test_delete_key_wrong_tenant():
    """Attempting to revoke another tenant's key must return 404."""
    from app.main import app
    from app.core.auth import CurrentUser, get_current_user
    from fastapi.testclient import TestClient

    def _auth():
        # This user belongs to "polkorp"
        return CurrentUser(user_id="test-user", tenant_id="polkorp", role="analyst")

    # DB query returns None because the key belongs to "other-tenant", not "polkorp"
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_session_local = MagicMock(return_value=mock_session)

    @asynccontextmanager
    async def _noop_lifespan(app):
        yield

    app.router.lifespan_context = _noop_lifespan
    app.dependency_overrides[get_current_user] = _auth

    with patch("app.db.base.AsyncSessionLocal", mock_session_local):
        with TestClient(app, raise_server_exceptions=True) as client:
            response = client.delete("/api/v1/api-keys/other-tenant-key-uuid")

    app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 404, response.text
    assert "not found" in response.json().get("error", response.json().get("detail", "")).lower()
