"""
ComplianceOS — M9 Ticketing Compliance API Router

Routes:
  GET  /api/v1/ticketing/dashboard
  GET  /api/v1/ticketing/countries
  GET  /api/v1/ticketing/obligations
  GET  /api/v1/ticketing/controls
  POST /api/v1/ticketing/events
  GET  /api/v1/ticketing/events
  GET  /api/v1/ticketing/events/{id}
  PUT  /api/v1/ticketing/events/{id}
  POST /api/v1/ticketing/events/{id}/risk-assessment
  POST /api/v1/ticketing/events/{id}/generate-checklist
  POST /api/v1/ticketing/events/{id}/generate-document
  POST /api/v1/ticketing/ai/ask
  POST /api/v1/ticketing/evidence/upload                # M6 EvidenceEngine pipeline
  GET  /api/v1/ticketing/reports/{event_id}
  POST /api/v1/ticketing/promoters                      # M3 KYC screening on creation
  GET  /api/v1/ticketing/promoters/{id}
  POST /api/v1/ticketing/seed                           # admin: load seed data
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File
from pydantic import BaseModel, Field

from app.core.audit import append_audit
from app.core.auth import CurrentUser, get_current_user, require_admin
from app.db.base import AsyncSessionLocal
from app.db.ticketing_models import (
    TicketingCountry, TicketingObligation, TicketingControl,
    TicketingEvent, TicketingEventChecklist, TicketingDocument,
    TicketingRiskScore, TicketingEvidence, TicketingAIAssessment,
    TicketingPromoter, TicketingVenue, TicketingClaim, TicketingRefundCase,
    TicketingChargeback,
    TicketingImplementationStatus, TicketingEventStatus, TicketingLaunchDecision,
    TicketingObligationCategory,
)
from app.modules.ticketing.engine import get_risk_engine
from app.modules.ticketing.copilot import TicketingCopilot

router = APIRouter(prefix="/api/v1/ticketing", tags=["M9 Ticketing Compliance"])


# ═══════════════════════════════════════════════════════════════════
# Pydantic request/response schemas
# ═══════════════════════════════════════════════════════════════════

class EventCreate(BaseModel):
    name: str
    description: str | None = None
    country_code: str = Field(..., min_length=2, max_length=2)
    city: str | None = None
    event_date: datetime | None = None
    end_date: datetime | None = None
    expected_attendance: int | None = None
    promoter_id: str | None = None
    venue_id: str | None = None

    ticket_categories: list[dict] = Field(default_factory=list)
    max_tickets_per_buyer: int | None = None
    service_fee_pct: float = 0.0
    service_fee_fixed: float = 0.0
    taxes_included: bool = True

    has_promoter_agreement: bool = False
    has_refund_policy: bool = False
    has_consumer_terms: bool = False
    has_payment_processor: bool = False
    has_privacy_policy: bool = False
    has_withdrawal_button: bool = False
    has_cancellation_clause: bool = False
    has_postponement_clause: bool = False
    has_marketing_consent: bool = False
    has_anti_bot_protection: bool = False
    has_electronic_invoice: bool = False
    has_aaip_registration: bool = False
    has_venue_authorization: bool = False
    has_event_permit: bool = False
    has_chargeback_evidence: bool = False

    resale_enabled: bool = False
    resale_type: str | None = None
    has_resale_policy: bool = False
    crypto_payments_enabled: bool = False
    has_aml_kyc_controls: bool = False
    wallet_balance_enabled: bool = False

    refund_sla_days: int = 10
    complaint_sla_days: int = 15
    additional_countries: list[str] = Field(default_factory=list)


class EventUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    city: str | None = None
    event_date: datetime | None = None
    end_date: datetime | None = None
    expected_attendance: int | None = None
    promoter_id: str | None = None
    venue_id: str | None = None

    ticket_categories: list[dict] | None = None
    max_tickets_per_buyer: int | None = None
    service_fee_pct: float | None = None
    service_fee_fixed: float | None = None
    taxes_included: bool | None = None

    has_promoter_agreement: bool | None = None
    has_refund_policy: bool | None = None
    has_consumer_terms: bool | None = None
    has_payment_processor: bool | None = None
    has_privacy_policy: bool | None = None
    has_withdrawal_button: bool | None = None
    has_cancellation_clause: bool | None = None
    has_postponement_clause: bool | None = None
    has_marketing_consent: bool | None = None
    has_anti_bot_protection: bool | None = None
    has_electronic_invoice: bool | None = None
    has_aaip_registration: bool | None = None
    has_venue_authorization: bool | None = None
    has_event_permit: bool | None = None
    has_chargeback_evidence: bool | None = None

    resale_enabled: bool | None = None
    resale_type: str | None = None
    has_resale_policy: bool | None = None
    crypto_payments_enabled: bool | None = None
    has_aml_kyc_controls: bool | None = None
    wallet_balance_enabled: bool | None = None

    refund_sla_days: int | None = None
    complaint_sla_days: int | None = None
    additional_countries: list[str] | None = None
    status: str | None = None


class AICopilotRequest(BaseModel):
    question: str
    event_id: str | None = None
    country: str | None = None
    deep_mode: bool = False
    event_context: dict[str, Any] | None = None


class GenerateDocumentRequest(BaseModel):
    document_type: str
    country: str | None = None
    language: str = "es"


# ═══════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════

def _event_to_dict(ev: TicketingEvent) -> dict:
    return {
        "id": str(ev.id),
        "tenant_id": ev.tenant_id,
        "name": ev.name,
        "description": ev.description,
        "country_code": ev.country_code,
        "city": ev.city,
        "event_date": ev.event_date.isoformat() if ev.event_date else None,
        "end_date": ev.end_date.isoformat() if ev.end_date else None,
        "expected_attendance": ev.expected_attendance,
        "status": ev.status.value if ev.status else None,
        "launch_decision": ev.launch_decision.value if ev.launch_decision else None,
        "promoter_id": str(ev.promoter_id) if ev.promoter_id else None,
        "venue_id": str(ev.venue_id) if ev.venue_id else None,
        "ticket_categories": ev.ticket_categories or [],
        "max_tickets_per_buyer": ev.max_tickets_per_buyer,
        "service_fee_pct": ev.service_fee_pct,
        "service_fee_fixed": ev.service_fee_fixed,
        "taxes_included": ev.taxes_included,
        "has_promoter_agreement": ev.has_promoter_agreement,
        "has_refund_policy": ev.has_refund_policy,
        "has_consumer_terms": ev.has_consumer_terms,
        "has_payment_processor": ev.has_payment_processor,
        "has_privacy_policy": ev.has_privacy_policy,
        "has_withdrawal_button": ev.has_withdrawal_button,
        "has_cancellation_clause": ev.has_cancellation_clause,
        "has_postponement_clause": ev.has_postponement_clause,
        "has_marketing_consent": ev.has_marketing_consent,
        "has_anti_bot_protection": ev.has_anti_bot_protection,
        "has_electronic_invoice": ev.has_electronic_invoice,
        "has_aaip_registration": ev.has_aaip_registration,
        "has_venue_authorization": ev.has_venue_authorization,
        "has_event_permit": ev.has_event_permit,
        "has_chargeback_evidence": ev.has_chargeback_evidence,
        "resale_enabled": ev.resale_enabled,
        "resale_type": ev.resale_type,
        "has_resale_policy": ev.has_resale_policy,
        "crypto_payments_enabled": ev.crypto_payments_enabled,
        "has_aml_kyc_controls": ev.has_aml_kyc_controls,
        "wallet_balance_enabled": ev.wallet_balance_enabled,
        "refund_sla_days": ev.refund_sla_days,
        "complaint_sla_days": ev.complaint_sla_days,
        "risk_score_overall": ev.risk_score_overall,
        "risk_breakdown": ev.risk_breakdown or {},
        "blocking_reasons": ev.blocking_reasons or [],
        "compliance_gaps": ev.compliance_gaps or [],
        "additional_countries": ev.additional_countries or [],
        "created_at": ev.created_at.isoformat() if ev.created_at else None,
        "updated_at": ev.updated_at.isoformat() if ev.updated_at else None,
    }


async def _get_event(event_id: str, tenant_id: str) -> TicketingEvent:
    from sqlalchemy import select
    async with AsyncSessionLocal() as session:
        ev = (await session.execute(
            select(TicketingEvent).where(
                TicketingEvent.id == event_id,
                TicketingEvent.tenant_id == tenant_id,
            )
        )).scalar_one_or_none()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    return ev


# ═══════════════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════════════

@router.get("/dashboard")
async def get_dashboard(current_user: CurrentUser = Depends(get_current_user)):
    """Overall ticketing compliance dashboard metrics."""
    from sqlalchemy import select, func as sa_func
    tenant_id = current_user.tenant_id

    async with AsyncSessionLocal() as session:
        # Event counts by status
        events = (await session.execute(
            select(TicketingEvent).where(TicketingEvent.tenant_id == tenant_id)
        )).scalars().all()

        claims = (await session.execute(
            select(TicketingClaim).where(TicketingClaim.tenant_id == tenant_id)
        )).scalars().all()

        refunds = (await session.execute(
            select(TicketingRefundCase).where(TicketingRefundCase.tenant_id == tenant_id)
        )).scalars().all()

        chargebacks = (await session.execute(
            select(TicketingChargeback).where(TicketingChargeback.tenant_id == tenant_id)
        )).scalars().all()

    total_events = len(events)
    active_events = sum(1 for e in events if e.status and e.status.value == "live")
    blocked_events = sum(1 for e in events if e.launch_decision and e.launch_decision.value == "BLOCKED")

    avg_risk = (
        sum(e.risk_score_overall for e in events) / total_events
        if total_events else 0
    )
    compliance_score = max(0, 100 - int(avg_risk))

    open_claims = sum(1 for c in claims if c.status and c.status.value in ("open", "under_review"))
    open_chargebacks = sum(1 for cb in chargebacks if cb.status and cb.status.value in ("received", "under_review"))
    chargeback_exposure = sum(cb.amount_usd or 0 for cb in chargebacks if cb.status and cb.status.value in ("received", "under_review"))

    critical_alerts = []
    if blocked_events > 0:
        critical_alerts.append(f"{blocked_events} event(s) BLOCKED — missing required compliance controls")
    if open_chargebacks > 0:
        critical_alerts.append(f"{open_chargebacks} open chargeback(s) — USD {chargeback_exposure:,.0f} exposure")
    for ev in events:
        if ev.blocking_reasons:
            critical_alerts.append(f"Event '{ev.name}': {ev.blocking_reasons[0]}")

    return {
        "compliance_score": compliance_score,
        "risk_score": int(avg_risk),
        "total_events": total_events,
        "active_events": active_events,
        "blocked_events": blocked_events,
        "open_claims": open_claims,
        "open_chargebacks": open_chargebacks,
        "chargeback_exposure_usd": round(chargeback_exposure, 2),
        "refund_sla_ok": all(
            (r.sla_deadline is None or r.sla_deadline > datetime.now(timezone.utc))
            for r in refunds
            if r.status and r.status.value == "pending"
        ),
        "critical_alerts": critical_alerts[:10],
        "events_by_status": {
            status: sum(1 for e in events if e.status and e.status.value == status)
            for status in ["draft", "under_review", "approved", "blocked", "live", "completed", "cancelled"]
        },
    }


# ═══════════════════════════════════════════════════════════════════
# COUNTRIES
# ═══════════════════════════════════════════════════════════════════

@router.get("/countries")
async def list_countries(current_user: CurrentUser = Depends(get_current_user)):
    """List country risk profiles for ticketing compliance."""
    from sqlalchemy import select
    async with AsyncSessionLocal() as session:
        countries = (await session.execute(
            select(TicketingCountry).where(TicketingCountry.tenant_id == current_user.tenant_id)
        )).scalars().all()

    return {
        "countries": [
            {
                "id": str(c.id),
                "country_code": c.country_code,
                "country_name": c.country_name,
                "risk_level": c.risk_level.value if c.risk_level else None,
                "risk_score": c.risk_score,
                "requires_boton_arrepentimiento": c.requires_boton_arrepentimiento,
                "requires_aaip_registration": c.requires_aaip_registration,
                "requires_electronic_invoice": c.requires_electronic_invoice,
                "requires_anti_resale_controls": c.requires_anti_resale_controls,
                "requires_promoter_permit": c.requires_promoter_permit,
                "withdrawal_period_days": c.withdrawal_period_days,
                "currency": c.currency,
                "regulator_consumer": c.regulator_consumer,
                "regulator_data_privacy": c.regulator_data_privacy,
                "regulator_payments": c.regulator_payments,
                "regulator_tax": c.regulator_tax,
                "notes": c.notes,
            }
            for c in countries
        ],
        "count": len(countries),
    }


# ═══════════════════════════════════════════════════════════════════
# OBLIGATIONS
# ═══════════════════════════════════════════════════════════════════

@router.get("/obligations")
async def list_obligations(
    country: str | None = Query(default=None),
    category: str | None = Query(default=None),
    risk_level: str | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
):
    """List ticketing regulatory obligations, optionally filtered."""
    from sqlalchemy import select, or_
    async with AsyncSessionLocal() as session:
        stmt = select(TicketingObligation).where(
            or_(
                TicketingObligation.tenant_id == current_user.tenant_id,
                TicketingObligation.tenant_id.is_(None),
            )
        )
        if country:
            stmt = stmt.where(TicketingObligation.country_code == country.upper())
        if category:
            stmt = stmt.where(TicketingObligation.legal_area == category)
        if risk_level:
            stmt = stmt.where(TicketingObligation.risk_level == risk_level.upper())

        obligations = (await session.execute(stmt)).scalars().all()

    return {
        "obligations": [
            {
                "id": str(o.id),
                "country_code": o.country_code,
                "legal_area": o.legal_area.value if o.legal_area else None,
                "title": o.title,
                "description": o.description,
                "legal_basis": o.legal_basis,
                "owner_role": o.owner_role,
                "risk_level": o.risk_level.value if o.risk_level else None,
                "implementation_status": o.implementation_status.value if o.implementation_status else None,
                "required_evidence": o.required_evidence or [],
                "controls": o.controls or [],
                "deadline_frequency": o.deadline_frequency,
                "penalties_summary": o.penalties_summary,
                "ai_explanation": o.ai_explanation,
                "recommended_action": o.recommended_action,
                "is_blocker": o.is_blocker,
            }
            for o in obligations
        ],
        "count": len(obligations),
    }


# ═══════════════════════════════════════════════════════════════════
# CONTROLS
# ═══════════════════════════════════════════════════════════════════

@router.get("/controls")
async def list_controls(
    category: str | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
):
    """List the ticketing controls library."""
    from sqlalchemy import select, or_
    async with AsyncSessionLocal() as session:
        stmt = select(TicketingControl).where(
            or_(
                TicketingControl.tenant_id == current_user.tenant_id,
                TicketingControl.tenant_id.is_(None),
            )
        )
        if category:
            stmt = stmt.where(TicketingControl.category == category)
        controls = (await session.execute(stmt)).scalars().all()

    return {
        "controls": [
            {
                "id": str(c.id),
                "control_code": c.control_code,
                "name": c.name,
                "description": c.description,
                "category": c.category.value if c.category else None,
                "risk_dimensions": c.risk_dimensions or [],
                "applies_to_countries": c.applies_to_countries or [],
                "implementation_guide": c.implementation_guide,
                "evidence_required": c.evidence_required or [],
                "is_mandatory": c.is_mandatory,
                "is_implemented": c.is_implemented,
            }
            for c in controls
        ],
        "count": len(controls),
    }


# ═══════════════════════════════════════════════════════════════════
# EVENTS — CRUD
# ═══════════════════════════════════════════════════════════════════

@router.get("/events")
async def list_events(
    status: str | None = Query(default=None),
    country: str | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
):
    """List ticketing events for the tenant."""
    from sqlalchemy import select
    async with AsyncSessionLocal() as session:
        stmt = select(TicketingEvent).where(TicketingEvent.tenant_id == current_user.tenant_id)
        if status:
            stmt = stmt.where(TicketingEvent.status == status)
        if country:
            stmt = stmt.where(TicketingEvent.country_code == country.upper())
        events = (await session.execute(stmt.order_by(TicketingEvent.created_at.desc()))).scalars().all()

    return {"events": [_event_to_dict(e) for e in events], "count": len(events)}


@router.post("/events", status_code=201)
async def create_event(
    req: EventCreate,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Create a new ticketing event and run initial risk assessment."""
    async with AsyncSessionLocal() as session:
        event = TicketingEvent(
            tenant_id=current_user.tenant_id,
            **req.model_dump(exclude={"promoter_id", "venue_id"}),
        )
        if req.promoter_id:
            event.promoter_id = uuid.UUID(req.promoter_id)
        if req.venue_id:
            event.venue_id = uuid.UUID(req.venue_id)

        session.add(event)
        await session.flush()

        # Run initial risk assessment
        engine = get_risk_engine()
        result = engine.score_event(req.model_dump())

        event.risk_score_overall = result.overall_score
        event.risk_breakdown = result.dimensions
        event.blocking_reasons = result.blocking_reasons
        event.compliance_gaps = result.missing_controls
        event.launch_decision = TicketingLaunchDecision(result.launch_decision)

        if result.launch_decision == "BLOCKED":
            event.status = TicketingEventStatus.BLOCKED

        await append_audit(session, current_user.tenant_id, "ticketing:event_created", {
            "event_id": str(event.id),
            "event_name": event.name,
            "country_code": event.country_code,
            "launch_decision": result.launch_decision,
            "risk_score": result.overall_score,
            "blocking_reasons": result.blocking_reasons,
        }, user_id=current_user.user_id)
        await session.commit()
        await session.refresh(event)

    return {"success": True, "event": _event_to_dict(event)}


@router.get("/events/{event_id}")
async def get_event(
    event_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get a specific ticketing event."""
    event = await _get_event(event_id, current_user.tenant_id)
    return _event_to_dict(event)


@router.put("/events/{event_id}")
async def update_event(
    event_id: str,
    req: EventUpdate,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Update a ticketing event and re-run risk assessment."""
    from sqlalchemy import select
    async with AsyncSessionLocal() as session:
        ev = (await session.execute(
            select(TicketingEvent).where(
                TicketingEvent.id == event_id,
                TicketingEvent.tenant_id == current_user.tenant_id,
            )
        )).scalar_one_or_none()
        if not ev:
            raise HTTPException(status_code=404, detail="Event not found")

        update_data = req.model_dump(exclude_none=True)
        for key, value in update_data.items():
            if key == "promoter_id" and value:
                ev.promoter_id = uuid.UUID(value)
            elif key == "venue_id" and value:
                ev.venue_id = uuid.UUID(value)
            elif key == "status":
                ev.status = TicketingEventStatus(value)
            else:
                setattr(ev, key, value)

        # Re-score
        event_dict = _event_to_dict(ev)
        engine = get_risk_engine()
        result = engine.score_event(event_dict)
        ev.risk_score_overall = result.overall_score
        ev.risk_breakdown = result.dimensions
        ev.blocking_reasons = result.blocking_reasons
        ev.compliance_gaps = result.missing_controls
        ev.launch_decision = TicketingLaunchDecision(result.launch_decision)

        if result.launch_decision == "BLOCKED" and ev.status not in (
            TicketingEventStatus.LIVE, TicketingEventStatus.COMPLETED, TicketingEventStatus.CANCELLED
        ):
            ev.status = TicketingEventStatus.BLOCKED

        await append_audit(session, current_user.tenant_id, "ticketing:event_updated", {
            "event_id": str(ev.id),
            "launch_decision": result.launch_decision,
            "risk_score": result.overall_score,
            "blocking_reasons": result.blocking_reasons,
        }, user_id=current_user.user_id)
        await session.commit()
        await session.refresh(ev)

    return {"success": True, "event": _event_to_dict(ev)}


# ═══════════════════════════════════════════════════════════════════
# RISK ASSESSMENT
# ═══════════════════════════════════════════════════════════════════

@router.post("/events/{event_id}/risk-assessment")
async def run_risk_assessment(
    event_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Run a full risk assessment for a ticketing event and persist the results."""
    from sqlalchemy import select
    async with AsyncSessionLocal() as session:
        ev = (await session.execute(
            select(TicketingEvent).where(
                TicketingEvent.id == event_id,
                TicketingEvent.tenant_id == current_user.tenant_id,
            )
        )).scalar_one_or_none()
        if not ev:
            raise HTTPException(status_code=404, detail="Event not found")

        event_dict = _event_to_dict(ev)
        engine = get_risk_engine()
        result = engine.score_event(event_dict)

        # Update event
        ev.risk_score_overall = result.overall_score
        ev.risk_breakdown = result.dimensions
        ev.blocking_reasons = result.blocking_reasons
        ev.compliance_gaps = result.missing_controls
        ev.launch_decision = TicketingLaunchDecision(result.launch_decision)

        # Persist risk score record
        score = TicketingRiskScore(
            event_id=ev.id,
            tenant_id=current_user.tenant_id,
            overall_score=result.overall_score,
            launch_decision=TicketingLaunchDecision(result.launch_decision),
            consumer_risk=result.dimensions.get("consumer_risk", 0),
            refund_risk=result.dimensions.get("refund_risk", 0),
            resale_risk=result.dimensions.get("resale_risk", 0),
            payment_risk=result.dimensions.get("payment_risk", 0),
            data_privacy_risk=result.dimensions.get("data_privacy_risk", 0),
            tax_risk=result.dimensions.get("tax_risk", 0),
            contractual_risk=result.dimensions.get("contractual_risk", 0),
            fraud_aml_risk=result.dimensions.get("fraud_aml_risk", 0),
            operational_risk=result.dimensions.get("operational_risk", 0),
            country_enforcement_risk=result.dimensions.get("country_enforcement_risk", 0),
            blocking_reasons=result.blocking_reasons,
            high_risk_triggers=result.high_risk_triggers,
            missing_controls=result.missing_controls,
            recommendations=result.recommendations,
        )
        session.add(score)
        await append_audit(session, current_user.tenant_id, "ticketing:risk_assessed", {
            "event_id": event_id,
            "score_id": str(score.id),
            "launch_decision": result.launch_decision,
            "overall_score": result.overall_score,
            "blocking_reasons": result.blocking_reasons,
            "missing_controls": result.missing_controls,
        }, user_id=current_user.user_id)
        await session.commit()
        await session.refresh(score)

    return {
        "success": True,
        "event_id": event_id,
        "assessment": result.to_dict(),
        "score_id": str(score.id),
    }


# ═══════════════════════════════════════════════════════════════════
# CHECKLIST GENERATION
# ═══════════════════════════════════════════════════════════════════

@router.post("/events/{event_id}/generate-checklist")
async def generate_checklist(
    event_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Generate a compliance checklist for the event based on its country and configuration."""
    from sqlalchemy import select, delete, or_
    async with AsyncSessionLocal() as session:
        ev = (await session.execute(
            select(TicketingEvent).where(
                TicketingEvent.id == event_id,
                TicketingEvent.tenant_id == current_user.tenant_id,
            )
        )).scalar_one_or_none()
        if not ev:
            raise HTTPException(status_code=404, detail="Event not found")

        # Fetch applicable controls
        stmt = select(TicketingControl).where(
            or_(
                TicketingControl.tenant_id == current_user.tenant_id,
                TicketingControl.tenant_id.is_(None),
            )
        )
        controls = (await session.execute(stmt)).scalars().all()

        # Clear existing checklist
        await session.execute(
            delete(TicketingEventChecklist).where(TicketingEventChecklist.event_id == ev.id)
        )

        checklist_items = []
        for ctrl in controls:
            # Skip country-specific controls that don't apply
            applies_to = ctrl.applies_to_countries or []
            if applies_to and ev.country_code.upper() not in applies_to:
                continue

            # Skip resale controls if resale not enabled
            if ctrl.control_code in ("TCK-C12", "TCK-C13", "TCK-C14") and not ev.resale_enabled:
                continue

            item = TicketingEventChecklist(
                event_id=ev.id,
                control_code=ctrl.control_code,
                category=ctrl.category,
                title=ctrl.name,
                description=ctrl.description,
                is_required=ctrl.is_mandatory,
                is_completed=False,
            )
            session.add(item)
            checklist_items.append(item)

        await session.commit()

    return {
        "success": True,
        "event_id": event_id,
        "items_generated": len(checklist_items),
        "checklist": [
            {
                "id": str(item.id),
                "control_code": item.control_code,
                "title": item.title,
                "category": item.category.value if item.category else None,
                "is_required": item.is_required,
                "is_completed": item.is_completed,
            }
            for item in checklist_items
        ],
    }


@router.get("/events/{event_id}/checklist")
async def get_checklist(
    event_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get the compliance checklist for an event."""
    from sqlalchemy import select
    async with AsyncSessionLocal() as session:
        items = (await session.execute(
            select(TicketingEventChecklist).where(
                TicketingEventChecklist.event_id == event_id
            ).order_by(TicketingEventChecklist.is_required.desc())
        )).scalars().all()

    return {
        "event_id": event_id,
        "items": [
            {
                "id": str(item.id),
                "control_code": item.control_code,
                "title": item.title,
                "description": item.description,
                "category": item.category.value if item.category else None,
                "is_required": item.is_required,
                "is_completed": item.is_completed,
                "completed_by": item.completed_by,
                "completed_at": item.completed_at.isoformat() if item.completed_at else None,
                "evidence_url": item.evidence_url,
                "notes": item.notes,
            }
            for item in items
        ],
        "total": len(items),
        "completed": sum(1 for i in items if i.is_completed),
        "required_total": sum(1 for i in items if i.is_required),
        "required_completed": sum(1 for i in items if i.is_required and i.is_completed),
    }


# ═══════════════════════════════════════════════════════════════════
# DOCUMENT GENERATION
# ═══════════════════════════════════════════════════════════════════

@router.post("/events/{event_id}/generate-document")
async def generate_event_document(
    event_id: str,
    req: GenerateDocumentRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Generate a compliance document for a specific event."""
    from sqlalchemy import select
    async with AsyncSessionLocal() as session:
        ev = (await session.execute(
            select(TicketingEvent).where(
                TicketingEvent.id == event_id,
                TicketingEvent.tenant_id == current_user.tenant_id,
            )
        )).scalar_one_or_none()
        if not ev:
            raise HTTPException(status_code=404, detail="Event not found")

        country = req.country or ev.country_code
        copilot = TicketingCopilot()
        result = await copilot.generate_document(
            document_type=req.document_type,
            event_context={
                "event_name": ev.name,
                "country": country,
                "city": ev.city,
                "event_date": ev.event_date.isoformat() if ev.event_date else None,
                "resale_enabled": ev.resale_enabled,
                "crypto_payments_enabled": ev.crypto_payments_enabled,
            },
            country=country,
            tenant_id=current_user.tenant_id,
            user_id=current_user.user_id,
        )

        if result.get("success"):
            from app.db.ticketing_models import TicketingDocumentType
            try:
                doc_type = TicketingDocumentType(req.document_type)
            except ValueError:
                doc_type = None

            if doc_type:
                doc = TicketingDocument(
                    tenant_id=current_user.tenant_id,
                    event_id=ev.id,
                    document_type=doc_type,
                    title=f"{req.document_type.replace('_', ' ').title()} — {ev.name}",
                    content=result.get("content", ""),
                    country_code=country,
                    language=req.language,
                    generated_by_model=result.get("model_used", ""),
                )
                session.add(doc)
                await session.commit()
                await session.refresh(doc)
                result["document_id"] = str(doc.id)

    return result


@router.get("/documents")
async def list_documents(
    event_id: str | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
):
    """List generated compliance documents."""
    from sqlalchemy import select
    async with AsyncSessionLocal() as session:
        stmt = select(TicketingDocument).where(TicketingDocument.tenant_id == current_user.tenant_id)
        if event_id:
            stmt = stmt.where(TicketingDocument.event_id == event_id)
        docs = (await session.execute(stmt.order_by(TicketingDocument.created_at.desc()))).scalars().all()

    return {
        "documents": [
            {
                "id": str(d.id),
                "event_id": str(d.event_id) if d.event_id else None,
                "document_type": d.document_type.value if d.document_type else None,
                "title": d.title,
                "country_code": d.country_code,
                "language": d.language,
                "version": d.version,
                "is_approved": d.is_approved,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in docs
        ],
        "count": len(docs),
    }


@router.get("/documents/{document_id}")
async def get_document(
    document_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get the full content of a generated document."""
    from sqlalchemy import select
    async with AsyncSessionLocal() as session:
        doc = (await session.execute(
            select(TicketingDocument).where(
                TicketingDocument.id == document_id,
                TicketingDocument.tenant_id == current_user.tenant_id,
            )
        )).scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "id": str(doc.id),
        "event_id": str(doc.event_id) if doc.event_id else None,
        "document_type": doc.document_type.value if doc.document_type else None,
        "title": doc.title,
        "content": doc.content,
        "country_code": doc.country_code,
        "language": doc.language,
        "version": doc.version,
        "generated_by_model": doc.generated_by_model,
        "is_approved": doc.is_approved,
        "approved_by": doc.approved_by,
        "approved_at": doc.approved_at.isoformat() if doc.approved_at else None,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
    }


# ═══════════════════════════════════════════════════════════════════
# AI COPILOT
# ═══════════════════════════════════════════════════════════════════

@router.post("/ai/ask")
async def ticketing_copilot_ask(
    req: AICopilotRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Ask the Ticketing Compliance AI Copilot a question."""
    from sqlalchemy import select

    event_context = req.event_context
    if req.event_id and not event_context:
        async with AsyncSessionLocal() as session:
            ev = (await session.execute(
                select(TicketingEvent).where(
                    TicketingEvent.id == req.event_id,
                    TicketingEvent.tenant_id == current_user.tenant_id,
                )
            )).scalar_one_or_none()
            if ev:
                event_context = _event_to_dict(ev)

    copilot = TicketingCopilot()
    result = await copilot.ask(
        question=req.question,
        event_context=event_context,
        country=req.country,
        deep_mode=req.deep_mode,
        tenant_id=current_user.tenant_id,
        user_id=current_user.user_id,
    )

    # Persist assessment
    async with AsyncSessionLocal() as session:
        assessment = TicketingAIAssessment(
            tenant_id=current_user.tenant_id,
            event_id=uuid.UUID(req.event_id) if req.event_id else None,
            question=req.question,
            context=event_context or {},
            response=result.get("answer", {}),
            model_used=result.get("model_used", ""),
            latency_ms=result.get("latency_ms", 0),
        )
        session.add(assessment)
        await session.commit()

    return result


# ═══════════════════════════════════════════════════════════════════
# EVIDENCE UPLOAD
# ═══════════════════════════════════════════════════════════════════

@router.post("/evidence/upload")
async def upload_evidence(
    file: UploadFile = File(...),
    event_id: str | None = Query(default=None),
    evidence_type: str | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Upload a compliance evidence file — routed through M6 EvidenceEngine for AI extraction
    and a proper SHA-256 chain-of-custody record before linking to the ticketing event."""
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    filename = file.filename or "upload"

    # M6 pipeline: extract structured data + build custody hash
    from app.modules.evidence.engine import EvidenceEngine
    engine = EvidenceEngine()
    m6_result = await engine.extract_from_pdf(
        pdf_bytes=content,
        filename=filename,
        tenant_id=current_user.tenant_id,
        regulation_context={"evidence_type": evidence_type, "event_id": event_id},
        user_id=current_user.user_id,
    )

    source_hash = m6_result.get("source_hash") or hashlib.sha256(content).hexdigest()
    custody_hash = m6_result.get("custody_hash") or hashlib.sha256(
        f"{source_hash}{datetime.now(timezone.utc).isoformat()}".encode()
    ).hexdigest()
    m6_document_id = m6_result.get("document_id")

    async with AsyncSessionLocal() as session:
        evidence = TicketingEvidence(
            tenant_id=current_user.tenant_id,
            event_id=uuid.UUID(event_id) if event_id else None,
            evidence_type=evidence_type or "document",
            filename=filename,
            source_hash=source_hash,
            custody_hash=custody_hash,
            uploaded_by=current_user.user_id or "system",
            notes=f"m6_document_id:{m6_document_id}" if m6_document_id else None,
        )
        session.add(evidence)
        await append_audit(session, current_user.tenant_id, "ticketing:evidence_uploaded", {
            "evidence_type": evidence_type,
            "event_id": event_id,
            "filename": filename,
            "source_hash": source_hash,
            "custody_hash": custody_hash,
            "m6_document_id": m6_document_id,
            "m6_extraction_success": m6_result.get("success", False),
        }, user_id=current_user.user_id)
        await session.commit()
        await session.refresh(evidence)

    return {
        "success": True,
        "evidence_id": str(evidence.id),
        "filename": evidence.filename,
        "source_hash": source_hash,
        "custody_hash": custody_hash,
        "size_bytes": len(content),
        "m6_document_id": m6_document_id,
        "extracted_data": m6_result.get("structured_data") if m6_result.get("success") else None,
    }


# ═══════════════════════════════════════════════════════════════════
# REPORTS
# ═══════════════════════════════════════════════════════════════════

@router.get("/reports/{event_id}")
async def get_event_compliance_report(
    event_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Generate a Ticketing Event Compliance Report with launch decision."""
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        ev = (await session.execute(
            select(TicketingEvent).where(
                TicketingEvent.id == event_id,
                TicketingEvent.tenant_id == current_user.tenant_id,
            )
        )).scalar_one_or_none()
        if not ev:
            raise HTTPException(status_code=404, detail="Event not found")

        checklist_items = (await session.execute(
            select(TicketingEventChecklist).where(TicketingEventChecklist.event_id == ev.id)
        )).scalars().all()

        # Latest risk score
        latest_score = (await session.execute(
            select(TicketingRiskScore)
            .where(TicketingRiskScore.event_id == ev.id)
            .order_by(TicketingRiskScore.assessed_at.desc())
            .limit(1)
        )).scalar_one_or_none()

        # Country risk profile
        country = (await session.execute(
            select(TicketingCountry).where(
                TicketingCountry.country_code == ev.country_code.upper(),
                TicketingCountry.tenant_id == current_user.tenant_id,
            )
        )).scalar_one_or_none()

    # Re-score if no existing assessment
    if not latest_score:
        engine = get_risk_engine()
        risk_result = engine.score_event(_event_to_dict(ev))
    else:
        from app.modules.ticketing.engine import RiskAssessmentResult
        risk_result = RiskAssessmentResult(
            overall_score=latest_score.overall_score,
            launch_decision=latest_score.launch_decision.value,
            dimensions={
                "consumer_risk": latest_score.consumer_risk,
                "refund_risk": latest_score.refund_risk,
                "resale_risk": latest_score.resale_risk,
                "payment_risk": latest_score.payment_risk,
                "data_privacy_risk": latest_score.data_privacy_risk,
                "tax_risk": latest_score.tax_risk,
                "contractual_risk": latest_score.contractual_risk,
                "fraud_aml_risk": latest_score.fraud_aml_risk,
                "operational_risk": latest_score.operational_risk,
                "country_enforcement_risk": latest_score.country_enforcement_risk,
            },
            blocking_reasons=latest_score.blocking_reasons or [],
            high_risk_triggers=latest_score.high_risk_triggers or [],
            missing_controls=latest_score.missing_controls or [],
            recommendations=latest_score.recommendations or [],
        )

    decision = risk_result.launch_decision
    compliance_score = max(0, 100 - risk_result.overall_score)

    return {
        "report_type": "ticketing_event_compliance",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "executive_summary": (
            f"Event '{ev.name}' in {ev.country_code} has been assessed with a risk score of "
            f"{risk_result.overall_score}/100 and a compliance score of {compliance_score}/100. "
            f"Launch decision: {decision}."
            + (
                f" {len(risk_result.blocking_reasons)} critical blocker(s) must be resolved before launch."
                if risk_result.blocking_reasons else
                " No critical blockers identified."
            )
        ),
        "event": {
            "id": event_id,
            "name": ev.name,
            "country": ev.country_code,
            "city": ev.city,
            "event_date": ev.event_date.isoformat() if ev.event_date else None,
            "status": ev.status.value if ev.status else None,
        },
        "country_risk": {
            "country_code": country.country_code if country else ev.country_code,
            "country_name": country.country_name if country else ev.country_code,
            "risk_level": country.risk_level.value if country else "MEDIUM",
            "risk_score": country.risk_score if country else 50,
        },
        "compliance_score": compliance_score,
        "risk_score": risk_result.overall_score,
        "launch_decision": decision,
        "blocking_reasons": risk_result.blocking_reasons,
        "high_risk_triggers": risk_result.high_risk_triggers,
        "missing_controls": risk_result.missing_controls,
        "risk_dimensions": risk_result.dimensions,
        "recommendations": risk_result.recommendations,
        "checklist_summary": {
            "total": len(checklist_items),
            "completed": sum(1 for i in checklist_items if i.is_completed),
            "required": sum(1 for i in checklist_items if i.is_required),
            "required_completed": sum(1 for i in checklist_items if i.is_required and i.is_completed),
        },
        "legal_disclaimer": (
            "This report is generated by ComplianceOS AI and does not constitute legal advice. "
            "Consult qualified legal counsel before making compliance or launch decisions. "
            "Regulatory requirements may change. Last updated: 2026."
        ),
    }


# ═══════════════════════════════════════════════════════════════════
# PROMOTERS  (M3 KYC/AML screening on creation)
# ═══════════════════════════════════════════════════════════════════

class PromoterCreate(BaseModel):
    name: str
    legal_entity: str | None = None
    tax_id: str | None = None
    country_code: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    notes: str | None = None


@router.post("/promoters", status_code=201)
async def create_promoter(
    req: PromoterCreate,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Create a promoter and screen them through M3 KYC/AML before storing."""
    from app.modules.kyc_aml.engine import KYCAMLEngine
    from app.db.ticketing_models import TicketingRiskLevel

    kyc = KYCAMLEngine()
    kyc_result = await kyc.screen_customer(
        customer_data={
            "name": req.name,
            "legal_entity": req.legal_entity,
            "tax_id": req.tax_id,
            "country": req.country_code,
            "contact_email": req.contact_email,
            "type": "event_promoter",
        },
        tenant_id=current_user.tenant_id,
        user_id=current_user.user_id,
    )

    analysis = kyc_result.get("analysis", {})
    kyc_risk_raw = str(analysis.get("risk_level", "MEDIUM")).upper()
    kyc_risk_map = {"LOW": "low", "MEDIUM": "medium", "HIGH": "high", "CRITICAL": "critical"}
    risk_str = kyc_risk_map.get(kyc_risk_raw, "medium")

    try:
        risk_level = TicketingRiskLevel(risk_str)
    except ValueError:
        risk_level = TicketingRiskLevel.MEDIUM

    kyc_verified = kyc_risk_raw not in ("HIGH", "CRITICAL")

    async with AsyncSessionLocal() as session:
        promoter = TicketingPromoter(
            tenant_id=current_user.tenant_id,
            name=req.name,
            legal_entity=req.legal_entity,
            tax_id=req.tax_id,
            country_code=req.country_code,
            contact_email=req.contact_email,
            contact_phone=req.contact_phone,
            kyc_verified=kyc_verified,
            risk_level=risk_level,
            notes=req.notes,
        )
        session.add(promoter)
        await session.flush()

        await append_audit(session, current_user.tenant_id, "ticketing:promoter_kyc_screened", {
            "promoter_id": str(promoter.id),
            "promoter_name": promoter.name,
            "kyc_risk_level": kyc_risk_raw,
            "kyc_verified": kyc_verified,
            "red_flags": analysis.get("red_flags", []),
            "kyc_audit_id": kyc_result.get("audit_id"),
        }, user_id=current_user.user_id)
        await session.commit()
        await session.refresh(promoter)

    return {
        "success": True,
        "promoter": {
            "id": str(promoter.id),
            "name": promoter.name,
            "legal_entity": promoter.legal_entity,
            "country_code": promoter.country_code,
            "kyc_verified": promoter.kyc_verified,
            "risk_level": promoter.risk_level.value,
            "created_at": promoter.created_at.isoformat(),
        },
        "kyc_screening": {
            "risk_level": kyc_risk_raw,
            "red_flags": analysis.get("red_flags", []),
            "passed": kyc_verified,
            "audit_id": kyc_result.get("audit_id"),
        },
    }


@router.get("/promoters/{promoter_id}")
async def get_promoter(
    promoter_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get promoter details including KYC status."""
    from sqlalchemy import select
    async with AsyncSessionLocal() as session:
        p = (await session.execute(
            select(TicketingPromoter).where(
                TicketingPromoter.id == promoter_id,
                TicketingPromoter.tenant_id == current_user.tenant_id,
            )
        )).scalar_one_or_none()
        if not p:
            raise HTTPException(status_code=404, detail="Promoter not found")
        return {
            "id": str(p.id),
            "name": p.name,
            "legal_entity": p.legal_entity,
            "tax_id": p.tax_id,
            "country_code": p.country_code,
            "contact_email": p.contact_email,
            "contact_phone": p.contact_phone,
            "kyc_verified": p.kyc_verified,
            "risk_level": p.risk_level.value,
            "agreement_signed": p.agreement_signed,
            "notes": p.notes,
            "created_at": p.created_at.isoformat(),
        }


# ═══════════════════════════════════════════════════════════════════
# SEED DATA (admin)
# ═══════════════════════════════════════════════════════════════════

@router.post("/seed")
async def seed_ticketing_data(
    admin: CurrentUser = Depends(require_admin),
):
    """Load seed data: country profiles + Argentina obligations + controls library. Admin only."""
    from sqlalchemy import select
    from app.modules.ticketing.seed_data import (
        COUNTRY_PROFILES, ARGENTINA_OBLIGATIONS, CONTROLS_LIBRARY
    )

    created = {"countries": 0, "obligations": 0, "controls": 0}

    async with AsyncSessionLocal() as session:
        # Countries
        for cp in COUNTRY_PROFILES:
            exists = (await session.execute(
                select(TicketingCountry).where(
                    TicketingCountry.country_code == cp["country_code"],
                    TicketingCountry.tenant_id == admin.tenant_id,
                )
            )).scalar_one_or_none()
            if not exists:
                from app.db.ticketing_models import TicketingCountryRisk
                c = TicketingCountry(
                    tenant_id=admin.tenant_id,
                    **{k: v for k, v in cp.items() if k != "risk_level"},
                    risk_level=TicketingCountryRisk(cp["risk_level"]),
                )
                session.add(c)
                created["countries"] += 1

        # Obligations (tenant_id=None = global)
        for ob in ARGENTINA_OBLIGATIONS:
            exists = (await session.execute(
                select(TicketingObligation).where(
                    TicketingObligation.country_code == ob["country_code"],
                    TicketingObligation.title == ob["title"],
                )
            )).scalar_one_or_none()
            if not exists:
                from app.db.ticketing_models import TicketingRiskLevel, TicketingObligationCategory
                o = TicketingObligation(
                    tenant_id=None,
                    **{k: v for k, v in ob.items() if k not in ("legal_area", "risk_level")},
                    legal_area=TicketingObligationCategory(ob["legal_area"]),
                    risk_level=TicketingRiskLevel(ob["risk_level"]),
                )
                session.add(o)
                created["obligations"] += 1

        # Controls
        for ctrl in CONTROLS_LIBRARY:
            exists = (await session.execute(
                select(TicketingControl).where(
                    TicketingControl.control_code == ctrl["control_code"]
                )
            )).scalar_one_or_none()
            if not exists:
                from app.db.ticketing_models import TicketingObligationCategory
                c = TicketingControl(
                    tenant_id=None,
                    **{k: v for k, v in ctrl.items() if k != "category"},
                    category=TicketingObligationCategory(ctrl["category"]),
                )
                session.add(c)
                created["controls"] += 1

        await session.commit()

    return {
        "success": True,
        "seeded": created,
        "message": "Seed data loaded successfully. Use GET /ticketing/countries to verify.",
    }
