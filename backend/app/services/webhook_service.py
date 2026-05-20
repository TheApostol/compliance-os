"""Webhook delivery: POST signed JSON payloads to tenant-configured URLs."""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

WEBHOOK_TIMEOUT = 10.0
MAX_RETRIES = 3


def _sign_payload(secret: str, payload: bytes) -> str:
    """Return HMAC-SHA256 hex digest for payload verification."""
    return "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


async def deliver(
    webhook_id: str,
    url: str,
    secret: str | None,
    event: str,
    data: dict,
) -> bool:
    """
    POST event payload to url. Returns True on 2xx, False otherwise.
    Retries up to MAX_RETRIES on network errors or 5xx with exponential backoff.
    """
    payload_dict = {
        "event": event,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "webhook_id": webhook_id,
        "data": data,
    }
    payload_bytes = json.dumps(payload_dict, default=str).encode()

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "ComplianceOS-Webhook/1.0",
        "X-ComplianceOS-Event": event,
        "X-ComplianceOS-Delivery": webhook_id,
    }
    if secret:
        headers["X-ComplianceOS-Signature"] = _sign_payload(secret, payload_bytes)

    for attempt in range(MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT) as client:
                resp = await client.post(url, content=payload_bytes, headers=headers)
                if resp.status_code < 500:
                    return resp.status_code < 400
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            logger.warning("Webhook delivery attempt %d failed: %s", attempt + 1, e)
        if attempt < MAX_RETRIES - 1:
            await asyncio.sleep(2 ** attempt * 2)

    return False


async def dispatch_event(tenant_id: str, event: str, data: dict) -> None:
    """
    Find all active webhooks subscribed to `event` for `tenant_id` and deliver concurrently.
    Updates last_triggered_at and last_status_code on each webhook.
    """
    from app.db.base import AsyncSessionLocal
    from app.db.models import WebhookConfig
    from sqlalchemy import select, update

    try:
        async with AsyncSessionLocal() as session:
            hooks = (
                await session.execute(
                    select(WebhookConfig).where(
                        WebhookConfig.tenant_id == tenant_id,
                        WebhookConfig.is_active == True,  # noqa: E712
                    )
                )
            ).scalars().all()
    except Exception as e:
        logger.error("dispatch_event DB error: %s", e)
        return

    subscribed = [h for h in hooks if event in (h.events or [])]
    if not subscribed:
        return

    async def _deliver_and_update(hook: WebhookConfig) -> None:
        success = await deliver(
            webhook_id=hook.id,
            url=hook.url,
            secret=hook.secret,
            event=event,
            data=data,
        )
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(
                    update(WebhookConfig)
                    .where(WebhookConfig.id == hook.id)
                    .values(
                        last_triggered_at=datetime.now(tz=timezone.utc),
                        last_status_code=200 if success else 0,
                    )
                )
                await session.commit()
        except Exception:
            pass
        logger.info(
            "Webhook %s (%s) → %s", hook.name, event, "ok" if success else "failed"
        )

    await asyncio.gather(
        *[_deliver_and_update(h) for h in subscribed], return_exceptions=True
    )
