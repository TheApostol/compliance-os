"""
Deadline checker: scan obligations for approaching deadlines and create DeadlineAlert rows.
Runs daily via APScheduler.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

import structlog

logger = logging.getLogger(__name__)
log = structlog.get_logger(__name__)

THRESHOLDS = [
    (1,  "critical"),
    (7,  "high"),
    (30, "medium"),
    (90, "low"),
]


async def check_deadlines(tenant_id: str = "polkorp") -> dict:
    """
    Scan all obligations with a deadline field, create/update DeadlineAlert rows
    for obligations within 90 days. Returns summary dict.
    """
    from app.db.base import AsyncSessionLocal
    from app.db.models import Obligation, DeadlineAlert, AlertSeverity, Regulation
    from sqlalchemy import select, update

    now = datetime.now(tz=timezone.utc)
    cutoff = now + timedelta(days=90)

    created = 0
    updated = 0
    total_checked = 0

    try:
        async with AsyncSessionLocal() as session:
            # Get regulations for this tenant
            regs = (await session.execute(
                select(Regulation).where(Regulation.tenant_id == tenant_id)
            )).scalars().all()
            reg_map = {str(r.id): r for r in regs}

            # Get all obligations for tenant's regulations
            reg_ids = list(reg_map.keys())
            if not reg_ids:
                return {"created": 0, "updated": 0, "total_checked": 0}

            obligations = (await session.execute(
                select(Obligation).where(Obligation.regulation_id.in_(reg_ids))
            )).scalars().all()

            for ob in obligations:
                total_checked += 1
                # Parse deadline from obligation — stored in description or a deadline field
                # Obligations have a 'description' field; look for a deadline date in properties
                deadline_dt = _extract_deadline(ob)
                if not deadline_dt:
                    continue
                if deadline_dt > cutoff or deadline_dt < now:
                    continue  # too far out or already past

                days_remaining = (deadline_dt - now).days
                severity = _severity_for_days(days_remaining)
                reg = reg_map.get(str(ob.regulation_id))
                if not reg:
                    continue

                # Upsert: update severity+days if alert exists, else create
                existing = (await session.execute(
                    select(DeadlineAlert).where(
                        DeadlineAlert.tenant_id == tenant_id,
                        DeadlineAlert.obligation_id == str(ob.id),
                    )
                )).scalar_one_or_none()

                if existing:
                    await session.execute(
                        update(DeadlineAlert)
                        .where(DeadlineAlert.id == existing.id)
                        .values(days_remaining=days_remaining, severity=severity)
                    )
                    updated += 1
                else:
                    obligation_title = ob.description[:200] if ob.description else "Unnamed obligation"
                    alert = DeadlineAlert(
                        tenant_id=tenant_id,
                        obligation_id=str(ob.id),
                        regulation_code=reg.code,
                        regulator=reg.regulator,
                        country=reg.country,
                        title=obligation_title,
                        deadline=deadline_dt,
                        days_remaining=days_remaining,
                        severity=severity,
                    )
                    session.add(alert)
                    await session.flush()  # flush to get alert.id before commit
                    created += 1

                    # Auto-trigger a remediation workflow for new critical/high alerts
                    if severity in (AlertSeverity.CRITICAL.value, AlertSeverity.HIGH.value):
                        try:
                            # local import to avoid circular dependency
                            from app.modules.workflows.engine import get_workflow_engine
                            await get_workflow_engine().create_remediation_workflow(
                                tenant_id=tenant_id,
                                title=f"Remediation: deadline alert — {obligation_title}",
                                trigger_source=f"deadline_alert:{str(alert.id)}",
                                severity=severity,
                            )
                            log.info(
                                "workflow_auto_created",
                                alert_id=str(alert.id),
                                severity=severity,
                                tenant_id=tenant_id,
                            )
                        except Exception as exc:
                            log.warning("workflow_auto_create_failed", error=str(exc))

            await session.commit()
    except Exception as e:
        logger.error("check_deadlines failed: %s", e)

    return {"created": created, "updated": updated, "total_checked": total_checked}


def _extract_deadline(ob) -> datetime | None:
    """Extract deadline datetime from obligation. Check properties dict first, then description."""
    import re
    # Check properties for an explicit deadline field
    props = ob.properties if hasattr(ob, "properties") and ob.properties else {}
    for key in ("deadline", "due_date", "effective_date", "compliance_date"):
        val = props.get(key)
        if val:
            try:
                if isinstance(val, datetime):
                    return val.replace(tzinfo=timezone.utc) if val.tzinfo is None else val
                # Try ISO format
                return datetime.fromisoformat(str(val).replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

    # Try to find a date in description text
    if ob.description:
        match = re.search(r"(\d{4}-\d{2}-\d{2})", ob.description)
        if match:
            try:
                return datetime.fromisoformat(match.group(1)).replace(tzinfo=timezone.utc)
            except ValueError:
                pass
    return None


def _severity_for_days(days: int) -> str:
    for threshold, severity in THRESHOLDS:
        if days <= threshold:
            return severity
    return "low"
