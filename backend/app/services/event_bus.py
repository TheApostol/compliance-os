"""Simple in-process event bus for SSE subscriptions."""
from __future__ import annotations
import asyncio
import logging
from collections import defaultdict
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

_queues: dict[str, list[asyncio.Queue]] = defaultdict(list)

try:
    from prometheus_client import Counter
    CRAWLER_ZERO_DOC = Counter(
        "crawler_zero_doc_total",
        "Crawler runs that returned zero documents",
        ["regulator", "tenant_id"],
    )
except Exception:
    CRAWLER_ZERO_DOC = None


async def publish(channel: str, data: dict) -> None:
    """Publish an event to all subscribers on a channel."""
    import json

    # channel format: "crawler:{tenant_id}"
    if ":" in channel:
        channel_type, tenant_id = channel.split(":", 1)
        if channel_type == "crawler" and data.get("crawled") == 0:
            regulator = data.get("regulator", "unknown")
            logger.warning(
                "Crawler zero-doc run: regulator=%s tenant_id=%s", regulator, tenant_id
            )
            if CRAWLER_ZERO_DOC is not None:
                CRAWLER_ZERO_DOC.labels(regulator=regulator, tenant_id=tenant_id).inc()
            data["alert"] = "zero_doc"

    payload = json.dumps(data)
    for q in list(_queues.get(channel, [])):
        await q.put(payload)

    # Also dispatch to webhooks.
    if ":" in channel:
        channel_type, tenant_id = channel.split(":", 1)
        event_name = f"{channel_type}.complete"
        try:
            from app.services.webhook_service import dispatch_event
            asyncio.create_task(dispatch_event(tenant_id=tenant_id, event=event_name, data=data))
        except Exception:
            pass


async def subscribe(channel: str) -> AsyncGenerator[str, None]:
    """Yield JSON strings as they arrive on a channel. Clean up on disconnect."""
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    _queues[channel].append(q)
    try:
        while True:
            data = await asyncio.wait_for(q.get(), timeout=25.0)
            yield data
    except (asyncio.TimeoutError, asyncio.CancelledError):
        pass
    finally:
        try:
            _queues[channel].remove(q)
        except ValueError:
            pass
