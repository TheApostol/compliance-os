"""
Deadline checker: scan obligations for approaching deadlines and create DeadlineAlert rows.
Runs daily via APScheduler.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
import pytz

logger = logging.getLogger(__name__)

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
    Deadlines are evaluated in the tenant's local timezone for accurate day counting.
    """
    from app.db.base import AsyncSessionLocal
    from app.db.models import Obligation, DeadlineAlert, AlertSeverity, Regulation, Tenant
    from sqlalchemy import select, update

    created = 0
    updated = 0
    total_checked = 0

    try:
        async with AsyncSessionLocal() as session:
            # Get tenant to access timezone configuration
            tenant = (await session.execute(
                select(Tenant).where(Tenant.id == tenant_id)
            )).scalar_one_or_none()

            if not tenant:
                logger.warning("Tenant %s not found for deadline check", tenant_id)
                return {"created": 0, "updated": 0, "total_checked": 0}

            # Get current time in tenant's timezone
            tz = _get_tenant_timezone(tenant_id, tenant.timezone_iana)
            now_utc = datetime.now(tz=timezone.utc)
            now_local = now_utc.astimezone(tz)
            cutoff_local = now_local + timedelta(days=90)
            cutoff_utc = cutoff_local.astimezone(timezone.utc)

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
                if deadline_dt > cutoff_utc or deadline_dt < now_utc:
                    continue  # too far out or already past

                # Convert deadline to tenant's timezone to calculate days accurately
                deadline_local = deadline_dt.astimezone(tz)
                days_remaining = (deadline_local.date() - now_local.date()).days
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
                    alert = DeadlineAlert(
                        tenant_id=tenant_id,
                        obligation_id=str(ob.id),
                        regulation_code=reg.code,
                        regulator=reg.regulator,
                        country=reg.country,
                        title=ob.description[:200] if ob.description else "Unnamed obligation",
                        deadline=deadline_dt,
                        days_remaining=days_remaining,
                        severity=severity,
                    )
                    session.add(alert)
                    created += 1

            await session.commit()
    except Exception as e:
        logger.error("check_deadlines failed: %s", e)

    return {"created": created, "updated": updated, "total_checked": total_checked}


def _get_tenant_timezone(tenant_id: str, timezone_iana: str) -> pytz.timezone:
    """Get tenant's timezone object with fallback to UTC if timezone is invalid."""
    try:
        return pytz.timezone(timezone_iana)
    except pytz.exceptions.UnknownTimeZoneError:
        logger.warning("Invalid timezone %s for tenant %s, falling back to UTC", timezone_iana, tenant_id)
        return pytz.UTC


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
