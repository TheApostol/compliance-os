"""
Webhook tests — HMAC signing, delivery, retry logic, dispatch, and CRUD endpoints.

All HTTP and DB calls are mocked; no real network or Docker required.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# 1. HMAC signature format
# ─────────────────────────────────────────────────────────────────────────────


def test_sign_payload():
    """HMAC-SHA256 signature must start with 'sha256='."""
    from app.services.webhook_service import _sign_payload

    sig = _sign_payload("my-secret", b'{"event":"test"}')
    assert sig.startswith("sha256="), f"Expected 'sha256=' prefix, got: {sig[:10]!r}"
    # After the prefix there should be a 64-char hex string
    hex_part = sig[len("sha256="):]
    assert len(hex_part) == 64
    assert all(c in "0123456789abcdef" for c in hex_part)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Successful delivery (HTTP 200)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_deliver_success():
    """Mock httpx returning 200 → deliver() returns True."""
    from app.services.webhook_service import deliver

    mock_response = MagicMock()
    mock_response.status_code = 200

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.webhook_service.httpx.AsyncClient", return_value=mock_client):
        result = await deliver(
            webhook_id="wh-001",
            url="https://example.com/hook",
            secret="s3cr3t",
            event="crawler.complete",
            data={"regulations": 3},
        )

    assert result is True


# ─────────────────────────────────────────────────────────────────────────────
# 3. Retry on 5xx, succeeds on third attempt
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_deliver_retry_on_5xx():
    """Mock httpx returning 500 twice, then 200 → deliver() returns True after retries."""
    from app.services.webhook_service import deliver

    resp_500 = MagicMock()
    resp_500.status_code = 500

    resp_200 = MagicMock()
    resp_200.status_code = 200

    call_count = 0

    async def _post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            return resp_500
        return resp_200

    mock_client = AsyncMock()
    mock_client.post = _post
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.webhook_service.httpx.AsyncClient", return_value=mock_client):
        with patch("app.services.webhook_service.asyncio.sleep", new_callable=AsyncMock):
            result = await deliver(
                webhook_id="wh-002",
                url="https://example.com/hook",
                secret=None,
                event="crawler.complete",
                data={},
            )

    assert result is True
    assert call_count == 3


# ─────────────────────────────────────────────────────────────────────────────
# 4. All retries exhausted → returns False
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_deliver_failure():
    """Mock httpx always returning 500 → deliver() returns False."""
    from app.services.webhook_service import deliver

    resp_500 = MagicMock()
    resp_500.status_code = 500

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=resp_500)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.webhook_service.httpx.AsyncClient", return_value=mock_client):
        with patch("app.services.webhook_service.asyncio.sleep", new_callable=AsyncMock):
            result = await deliver(
                webhook_id="wh-003",
                url="https://example.com/hook",
                secret=None,
                event="crawler.complete",
                data={},
            )

    assert result is False


# ─────────────────────────────────────────────────────────────────────────────
# 5. dispatch_event skips hooks that are not subscribed to the event
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_dispatch_no_matching_hooks():
    """
    Hook is subscribed to 'deadline.alert' only.
    dispatch_event('crawler.complete') must not call deliver().
    """
    from app.services.webhook_service import dispatch_event

    hook = SimpleNamespace(
        id="wh-004",
        tenant_id="polkorp",
        name="Slack alerts",
        url="https://hooks.slack.com/test",
        secret=None,
        is_active=True,
        events=["deadline.alert"],  # different event
    )

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [hook]

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_session_local = MagicMock(return_value=mock_session)

    with patch("app.services.webhook_service.AsyncSessionLocal", mock_session_local):
        with patch("app.services.webhook_service.deliver", new_callable=AsyncMock) as mock_deliver:
            await dispatch_event(tenant_id="polkorp", event="crawler.complete", data={})

    mock_deliver.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# 6. dispatch_event delivers to hooks subscribed to the matching event
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_dispatch_delivers_to_subscribed():
    """
    Hook subscribed to 'crawler.complete' → deliver() is called once.
    """
    from app.services.webhook_service import dispatch_event

    hook = SimpleNamespace(
        id="wh-005",
        tenant_id="polkorp",
        name="CI webhook",
        url="https://example.com/ci",
        secret="s3cr3t",
        is_active=True,
        events=["crawler.complete"],
    )

    # First session: SELECT hooks
    mock_select_result = MagicMock()
    mock_select_result.scalars.return_value.all.return_value = [hook]

    mock_select_session = AsyncMock()
    mock_select_session.execute = AsyncMock(return_value=mock_select_result)
    mock_select_session.__aenter__ = AsyncMock(return_value=mock_select_session)
    mock_select_session.__aexit__ = AsyncMock(return_value=False)

    # Second session: UPDATE last_triggered_at
    mock_update_session = AsyncMock()
    mock_update_session.execute = AsyncMock(return_value=MagicMock())
    mock_update_session.commit = AsyncMock()
    mock_update_session.__aenter__ = AsyncMock(return_value=mock_update_session)
    mock_update_session.__aexit__ = AsyncMock(return_value=False)

    call_count = 0

    def _session_factory():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return mock_select_session
        return mock_update_session

    with patch("app.services.webhook_service.AsyncSessionLocal", side_effect=_session_factory):
        with patch(
            "app.services.webhook_service.deliver",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_deliver:
            await dispatch_event(
                tenant_id="polkorp",
                event="crawler.complete",
                data={"regulations": 2},
            )

    mock_deliver.assert_called_once_with(
        webhook_id="wh-005",
        url="https://example.com/ci",
        secret="s3cr3t",
        event="crawler.complete",
        data={"regulations": 2},
    )


# ─────────────────────────────────────────────────────────────────────────────
# 7. POST /webhooks endpoint — returns webhook with masked secret
# ─────────────────────────────────────────────────────────────────────────────


def test_create_webhook_endpoint():
    """POST /webhooks returns 201 with the webhook record and a masked secret."""
    from app.main import app
    from app.core.auth import CurrentUser, get_current_user
    from fastapi.testclient import TestClient

    def _auth():
        return CurrentUser(user_id="test-user", tenant_id="polkorp", role="analyst")

    created_at = datetime(2026, 5, 20, 10, 0, 0, tzinfo=timezone.utc)

    def _fake_refresh(obj):
        obj.id = "wh-new-001"
        obj.name = "Slack alerts"
        obj.url = "https://hooks.slack.com/abc"
        obj.secret = "mysecret123"
        obj.events = ["crawler.complete"]
        obj.is_active = True
        obj.last_triggered_at = None
        obj.last_status_code = None
        obj.created_at = created_at

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock(side_effect=_fake_refresh)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_session_local = MagicMock(return_value=mock_session)

    @asynccontextmanager
    async def _noop_lifespan(app):
        yield

    app.router.lifespan_context = _noop_lifespan
    app.dependency_overrides[get_current_user] = _auth

    with patch("app.api.v1.router.AsyncSessionLocal", mock_session_local):
        with TestClient(app, raise_server_exceptions=True) as client:
            response = client.post(
                "/api/v1/webhooks",
                json={
                    "name": "Slack alerts",
                    "url": "https://hooks.slack.com/abc",
                    "secret": "mysecret123",
                    "events": ["crawler.complete"],
                },
            )

    app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["id"] == "wh-new-001"
    assert data["name"] == "Slack alerts"
    assert data["url"] == "https://hooks.slack.com/abc"
    # Secret must be masked — never returned in plaintext
    assert data["secret"] != "mysecret123"
    assert data["secret"].startswith("myse")
    assert "****" in data["secret"]
    assert data["events"] == ["crawler.complete"]
    assert data["is_active"] is True
