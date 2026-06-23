"""
ComplianceOS — Immutable Audit Log with Hash Chain

Every AI inference, every compliance decision, every override is logged here
with a cryptographic hash chain. Tamper-evident by design.

Required for: UIF AR (Ley 25.246), BCRA Com. A, BACEN, CMF, CNV.
Retention: 7 years default (configurable per tenant).
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column, String, DateTime, BigInteger, Index
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import Base


GENESIS_HASH = "0" * 64


class AuditLogEntry(Base):
    """INSERT-ONLY table. Enforced by a BEFORE UPDATE/DELETE trigger
    (see alembic/versions/0010_audit_log_insert_only.py) that rejects mutation
    regardless of which role connects — a plain GRANT/REVOKE is insufficient
    since the app connects as the table owner, which bypasses privilege checks.
    """

    __tablename__ = "audit_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    audit_id = Column(String(32), unique=True, nullable=False, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=True)
    event_type = Column(String(64), nullable=False, index=True)
    payload = Column(JSONB, nullable=False)
    prev_hash = Column(String(64), nullable=False)
    entry_hash = Column(String(64), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_audit_tenant_created", "tenant_id", "created_at"),
    )


def compute_entry_hash(prev_hash: str, payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(f"{prev_hash}{canonical}".encode("utf-8")).hexdigest()


async def append_audit(
    session: AsyncSession,
    tenant_id: str,
    event_type: str,
    payload: dict[str, Any],
    user_id: str | None = None,
) -> AuditLogEntry:
    from sqlalchemy import select, desc

    stmt = (
        select(AuditLogEntry.entry_hash)
        .where(AuditLogEntry.tenant_id == tenant_id)
        .order_by(desc(AuditLogEntry.id))
        .limit(1)
    )
    result = await session.execute(stmt)
    last = result.scalar()
    prev = last or GENESIS_HASH

    audit_id = payload.get("audit_id") or hashlib.sha256(
        f"{tenant_id}:{event_type}:{datetime.now(timezone.utc).isoformat()}".encode()
    ).hexdigest()[:16]

    entry_hash = compute_entry_hash(prev, payload)

    entry = AuditLogEntry(
        audit_id=audit_id,
        tenant_id=tenant_id,
        user_id=user_id,
        event_type=event_type,
        payload=payload,
        prev_hash=prev,
        entry_hash=entry_hash,
    )
    session.add(entry)
    await session.flush()
    return entry


async def verify_chain(session: AsyncSession, tenant_id: str) -> dict[str, Any]:
    from sqlalchemy import select

    stmt = (
        select(AuditLogEntry)
        .where(AuditLogEntry.tenant_id == tenant_id)
        .order_by(AuditLogEntry.id)
    )
    result = await session.execute(stmt)
    entries = result.scalars().all()

    if not entries:
        return {"valid": True, "entries": 0, "tampered_at": None}

    expected_prev = GENESIS_HASH
    for entry in entries:
        if entry.prev_hash != expected_prev:
            return {
                "valid": False,
                "entries": len(entries),
                "tampered_at": entry.audit_id,
                "reason": "prev_hash mismatch",
            }
        recomputed = compute_entry_hash(entry.prev_hash, entry.payload)
        if recomputed != entry.entry_hash:
            return {
                "valid": False,
                "entries": len(entries),
                "tampered_at": entry.audit_id,
                "reason": "payload mutated",
            }
        expected_prev = entry.entry_hash

    return {"valid": True, "entries": len(entries), "head_hash": expected_prev}
