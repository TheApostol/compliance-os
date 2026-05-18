"""Simple in-process event bus for SSE subscriptions."""
from __future__ import annotations
import asyncio
from collections import defaultdict
from typing import AsyncGenerator

_queues: dict[str, list[asyncio.Queue]] = defaultdict(list)


async def publish(channel: str, data: dict) -> None:
    """Publish an event to all subscribers on a channel."""
    import json
    for q in list(_queues.get(channel, [])):
        await q.put(json.dumps(data))


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
