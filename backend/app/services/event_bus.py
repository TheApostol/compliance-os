"""Simple in-process event bus for SSE subscriptions."""
from __future__ import annotations
import asyncio
from collections import defaultdict
from typing import AsyncGenerator

_queues: dict[str, list[asyncio.Queue]] = defaultdict(list)


async def publish(channel: str, data: dict) -> None:
    """Publish an event to all subscribers on a channel."""
    import json
    payload = json.dumps(data)
    for q in list(_queues.get(channel, [])):
        await q.put(payload)

    # Also dispatch to webhooks.
    # channel format: "crawler:{tenant_id}"
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
