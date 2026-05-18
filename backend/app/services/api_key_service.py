"""
ComplianceOS — API Key Service
================================
Generate, validate, and track long-lived scoped API keys for programmatic
access (CI/CD pipelines, integrations).

Keys are prefixed with "csk_" (ComplianceOS Secret Key) and stored as
SHA-256 hashes — the plaintext is shown exactly once at creation time.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone


def generate_key() -> tuple[str, str, str]:
    """
    Generate a new API key.

    Returns:
        (full_key, prefix, hashed_key)
        - full_key  — plaintext key, shown ONCE at creation time
        - prefix    — first 8 characters, safe to display in listings
        - hashed_key — SHA-256 hex digest stored in the DB
    """
    full_key = "csk_" + secrets.token_urlsafe(32)
    prefix = full_key[:8]
    hashed = hashlib.sha256(full_key.encode()).hexdigest()
    return full_key, prefix, hashed


async def validate_key(raw_key: str) -> dict | None:
    """
    Validate an API key presented by a caller.

    Looks up the SHA-256 hash in the DB, checks is_active and expiry,
    then records last_used_at on success.

    Returns:
        {"tenant_id": str, "scopes": list, "key_id": str} if valid, else None.
    """
    from app.db.base import AsyncSessionLocal
    from app.db.models import APIKey
    from sqlalchemy import select, update

    hashed = hashlib.sha256(raw_key.encode()).hexdigest()
    async with AsyncSessionLocal() as session:
        stmt = select(APIKey).where(
            APIKey.hashed_key == hashed,
            APIKey.is_active == True,  # noqa: E712
        )
        key_row = (await session.execute(stmt)).scalar_one_or_none()
        if not key_row:
            return None
        if key_row.expires_at and key_row.expires_at < datetime.now(tz=timezone.utc):
            return None
        # Record last used timestamp
        await session.execute(
            update(APIKey)
            .where(APIKey.id == key_row.id)
            .values(last_used_at=datetime.now(tz=timezone.utc))
        )
        await session.commit()
        return {
            "tenant_id": key_row.tenant_id,
            "scopes": key_row.scopes or [],
            "key_id": key_row.id,
        }
