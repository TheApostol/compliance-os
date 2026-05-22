from __future__ import annotations

import uuid as _uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select

from app.core.auth import CurrentUser, get_current_user, require_admin
from app.db.base import AsyncSessionLocal
from app.db.models import Ticket, TicketPriority, TicketStatus
from app.modules.workflows.engine import get_workflow_engine
from app.modules.predictive.engine import get_predictive_engine
from app.modules.crawler.latam_regulatory_crawler import crawl_latam_regulator

router = APIRouter(prefix='/api/v1', tags=['m7-m8'])


class WorkflowCreateRequest(BaseModel):
    title: str
    trigger_source: str
    severity: str = 'medium'


@router.post('/workflow/remediation')
async def create_remediation_workflow(req: WorkflowCreateRequest, current_user: CurrentUser = Depends(get_current_user)):
    return await get_workflow_engine().create_remediation_workflow(
        tenant_id=current_user.tenant_id,
        title=req.title,
        trigger_source=req.trigger_source,
        severity=req.severity,
    )


@router.get('/predict/jurisdiction-risk')
async def jurisdiction_risk_scores(current_user: CurrentUser = Depends(get_current_user)):
    return await get_predictive_engine().jurisdiction_risk_scores()


class ExpansionSimulationRequest(BaseModel):
    business_model: str
    countries: list[str]


@router.post('/simulate/market-entry')
async def simulate_market_entry(req: ExpansionSimulationRequest, current_user: CurrentUser = Depends(get_current_user)):
    return await get_predictive_engine().simulate_market_entry(
        business_model=req.business_model,
        countries=req.countries,
    )


@router.post('/crawler/latam/{regulator}')
async def run_latam_regulatory_crawler(
    regulator: str,
    store: bool = Query(default=True),
    admin: CurrentUser = Depends(require_admin),
):
    return await crawl_latam_regulator(
        regulator=regulator,
        tenant_id=admin.tenant_id,
        store=store,
    )


# ── M9 Ticketing ────────────────────────────────────────────────────────────

class TicketCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    priority: TicketPriority = TicketPriority.MEDIUM


class TicketUpdateRequest(BaseModel):
    status: TicketStatus


@router.get('/tickets')
async def list_tickets(current_user: CurrentUser = Depends(get_current_user)):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Ticket)
            .where(Ticket.tenant_id == current_user.tenant_id)
            .order_by(Ticket.created_at.desc())
        )
        tickets = result.scalars().all()
        return [
            {
                'id': str(t.id),
                'title': t.title,
                'description': t.description,
                'status': t.status,
                'priority': t.priority,
                'created_by': t.created_by,
                'created_at': t.created_at.isoformat() if t.created_at else None,
                'updated_at': t.updated_at.isoformat() if t.updated_at else None,
            }
            for t in tickets
        ]


@router.post('/tickets')
async def create_ticket(req: TicketCreateRequest, current_user: CurrentUser = Depends(get_current_user)):
    async with AsyncSessionLocal() as session:
        ticket = Ticket(
            tenant_id=current_user.tenant_id,
            title=req.title,
            description=req.description,
            priority=req.priority,
            created_by=getattr(current_user, 'email', None) or current_user.tenant_id,
        )
        session.add(ticket)
        await session.commit()
        await session.refresh(ticket)
        return {
            'id': str(ticket.id),
            'title': ticket.title,
            'description': ticket.description,
            'status': ticket.status,
            'priority': ticket.priority,
            'created_by': ticket.created_by,
            'created_at': ticket.created_at.isoformat() if ticket.created_at else None,
        }


@router.patch('/tickets/{ticket_id}')
async def update_ticket_status(
    ticket_id: str,
    req: TicketUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Ticket).where(
                Ticket.id == _uuid.UUID(ticket_id),
                Ticket.tenant_id == current_user.tenant_id,
            )
        )
        ticket = result.scalar_one_or_none()
        if ticket is None:
            raise HTTPException(status_code=404, detail='Ticket not found')
        ticket.status = req.status
        await session.commit()
        await session.refresh(ticket)
        return {
            'id': str(ticket.id),
            'title': ticket.title,
            'status': ticket.status,
            'priority': ticket.priority,
            'updated_at': ticket.updated_at.isoformat() if ticket.updated_at else None,
        }
