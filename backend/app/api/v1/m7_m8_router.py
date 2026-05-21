import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select

from app.core.auth import CurrentUser, get_current_user, require_admin
from app.db.base import AsyncSessionLocal
from app.modules.predictive.engine import get_predictive_engine
from app.modules.workflows.engine import get_workflow_engine
from app.modules.workflows.models import Workflow, WorkflowStatus, WorkflowStep
from app.modules.crawler.latam_regulatory_crawler import crawl_latam_regulator

log = structlog.get_logger(__name__)

router = APIRouter(prefix='/api/v1', tags=['m7-m8'])


class WorkflowCreateRequest(BaseModel):
    title: str
    trigger_source: str
    severity: str = 'medium'


class EscalateRequest(BaseModel):
    assigned_to: str
    reason: str


@router.post('/workflow/remediation')
async def create_remediation_workflow(req: WorkflowCreateRequest, current_user: CurrentUser = Depends(get_current_user)):
    return await get_workflow_engine().create_remediation_workflow(
        tenant_id=current_user.tenant_id,
        title=req.title,
        trigger_source=req.trigger_source,
        severity=req.severity,
    )


@router.get('/workflow/')
async def list_workflows(current_user: CurrentUser = Depends(get_current_user)):
    """List all workflows for the current tenant, ordered by created_at desc, limit 50."""
    async with AsyncSessionLocal() as session:
        # Count steps per workflow via subquery
        step_count_sq = (
            select(WorkflowStep.workflow_id, func.count(WorkflowStep.id).label('step_count'))
            .group_by(WorkflowStep.workflow_id)
            .subquery()
        )
        stmt = (
            select(Workflow, step_count_sq.c.step_count)
            .outerjoin(step_count_sq, Workflow.id == step_count_sq.c.workflow_id)
            .where(Workflow.tenant_id == current_user.tenant_id)
            .order_by(Workflow.created_at.desc())
            .limit(50)
        )
        rows = (await session.execute(stmt)).all()

    return [
        {
            'workflow_id': str(wf.id),
            'title': wf.title,
            'workflow_type': wf.workflow_type,
            'severity': wf.severity,
            'status': wf.status.value,
            'trigger_source': wf.trigger_source,
            'created_at': wf.created_at.isoformat() if wf.created_at else None,
            'step_count': step_count or 0,
        }
        for wf, step_count in rows
    ]


@router.get('/workflow/{workflow_id}')
async def get_workflow(workflow_id: str, current_user: CurrentUser = Depends(get_current_user)):
    """Get a single workflow with all its steps. Raises 404 if not found or tenant mismatch."""
    async with AsyncSessionLocal() as session:
        wf_stmt = select(Workflow).where(Workflow.id == workflow_id)
        wf = (await session.execute(wf_stmt)).scalar_one_or_none()

        if wf is None or wf.tenant_id != current_user.tenant_id:
            raise HTTPException(status_code=404, detail='Workflow not found')

        steps_stmt = (
            select(WorkflowStep)
            .where(WorkflowStep.workflow_id == wf.id)
            .order_by(WorkflowStep.order_index)
        )
        steps = (await session.execute(steps_stmt)).scalars().all()

    return {
        'workflow_id': str(wf.id),
        'title': wf.title,
        'workflow_type': wf.workflow_type,
        'severity': wf.severity,
        'status': wf.status.value,
        'trigger_source': wf.trigger_source,
        'assigned_to': wf.assigned_to,
        'created_at': wf.created_at.isoformat() if wf.created_at else None,
        'metadata': wf.metadata_json,
        'steps': [
            {
                'step_id': str(s.id),
                'step_type': s.step_type,
                'title': s.title,
                'status': s.status,
                'requires_approval': s.requires_approval,
                'completed': s.completed,
                'order_index': s.order_index,
            }
            for s in steps
        ],
    }


@router.post('/workflow/{workflow_id}/steps/{step_id}/complete')
async def complete_step(
    workflow_id: str,
    step_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Mark a step as completed. Advances workflow status based on remaining steps."""
    async with AsyncSessionLocal() as session:
        wf_stmt = select(Workflow).where(Workflow.id == workflow_id)
        wf = (await session.execute(wf_stmt)).scalar_one_or_none()

        if wf is None or wf.tenant_id != current_user.tenant_id:
            raise HTTPException(status_code=404, detail='Workflow not found')

        step_stmt = select(WorkflowStep).where(
            WorkflowStep.id == step_id,
            WorkflowStep.workflow_id == wf.id,
        )
        step = (await session.execute(step_stmt)).scalar_one_or_none()

        if step is None:
            raise HTTPException(status_code=404, detail='Step not found')

        step.completed = True
        step.status = 'completed'

        # Load all steps ordered to determine next state
        all_steps_stmt = (
            select(WorkflowStep)
            .where(WorkflowStep.workflow_id == wf.id)
            .order_by(WorkflowStep.order_index)
        )
        all_steps = (await session.execute(all_steps_stmt)).scalars().all()

        # Find the next incomplete step after the current one
        next_step = None
        found_current = False
        for s in all_steps:
            if str(s.id) == step_id:
                found_current = True
                continue
            if found_current and not s.completed:
                next_step = s
                break

        all_completed = all(s.completed or str(s.id) == step_id for s in all_steps)

        if all_completed:
            wf.status = WorkflowStatus.COMPLETED
        elif next_step is not None and next_step.requires_approval:
            wf.status = WorkflowStatus.APPROVAL_REQUIRED
        else:
            wf.status = WorkflowStatus.RUNNING

        await session.commit()
        log.info('workflow_step_completed', workflow_id=workflow_id, step_id=step_id, new_status=wf.status.value)

    return {
        'workflow_id': workflow_id,
        'step_id': step_id,
        'step_status': 'completed',
        'workflow_status': wf.status.value,
    }


@router.post('/workflow/{workflow_id}/steps/{step_id}/approve')
async def approve_step(
    workflow_id: str,
    step_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Approve a step that requires_approval=True. Advances the workflow state."""
    async with AsyncSessionLocal() as session:
        wf_stmt = select(Workflow).where(Workflow.id == workflow_id)
        wf = (await session.execute(wf_stmt)).scalar_one_or_none()

        if wf is None or wf.tenant_id != current_user.tenant_id:
            raise HTTPException(status_code=404, detail='Workflow not found')

        step_stmt = select(WorkflowStep).where(
            WorkflowStep.id == step_id,
            WorkflowStep.workflow_id == wf.id,
        )
        step = (await session.execute(step_stmt)).scalar_one_or_none()

        if step is None:
            raise HTTPException(status_code=404, detail='Step not found')

        if not step.requires_approval:
            raise HTTPException(status_code=400, detail='Step does not require approval')

        step.completed = True
        step.status = 'approved'

        # Load all steps ordered to determine next state
        all_steps_stmt = (
            select(WorkflowStep)
            .where(WorkflowStep.workflow_id == wf.id)
            .order_by(WorkflowStep.order_index)
        )
        all_steps = (await session.execute(all_steps_stmt)).scalars().all()

        # Find the next incomplete step after the current one
        next_step = None
        found_current = False
        for s in all_steps:
            if str(s.id) == step_id:
                found_current = True
                continue
            if found_current and not s.completed:
                next_step = s
                break

        all_completed = all(s.completed or str(s.id) == step_id for s in all_steps)

        if all_completed:
            wf.status = WorkflowStatus.COMPLETED
        elif next_step is not None and next_step.requires_approval:
            wf.status = WorkflowStatus.APPROVAL_REQUIRED
        else:
            wf.status = WorkflowStatus.RUNNING

        await session.commit()
        log.info('workflow_step_approved', workflow_id=workflow_id, step_id=step_id, new_status=wf.status.value)

    return {
        'workflow_id': workflow_id,
        'step_id': step_id,
        'step_status': 'approved',
        'workflow_status': wf.status.value,
    }


@router.post('/workflow/{workflow_id}/escalate')
async def escalate_workflow(
    workflow_id: str,
    body: EscalateRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Escalate a workflow, setting its status to ESCALATED and assigning it to a new owner."""
    async with AsyncSessionLocal() as session:
        wf_stmt = select(Workflow).where(Workflow.id == workflow_id)
        wf = (await session.execute(wf_stmt)).scalar_one_or_none()

        if wf is None or wf.tenant_id != current_user.tenant_id:
            raise HTTPException(status_code=404, detail='Workflow not found')

        wf.status = WorkflowStatus.ESCALATED
        wf.assigned_to = body.assigned_to

        await session.commit()
        log.info('workflow_escalated', workflow_id=workflow_id, assigned_to=body.assigned_to, reason=body.reason)

    return {
        'workflow_id': workflow_id,
        'status': WorkflowStatus.ESCALATED.value,
        'assigned_to': body.assigned_to,
    }


@router.get('/predict/jurisdiction-risk')
async def jurisdiction_risk_scores(current_user: CurrentUser = Depends(get_current_user)):
    return await get_predictive_engine().jurisdiction_risk_scores(tenant_id=current_user.tenant_id)


class ExpansionSimulationRequest(BaseModel):
    business_model: str
    countries: list[str]


@router.post('/simulate/market-entry')
async def simulate_market_entry(req: ExpansionSimulationRequest, current_user: CurrentUser = Depends(get_current_user)):
    return await get_predictive_engine().simulate_market_entry(
        business_model=req.business_model,
        countries=req.countries,
        tenant_id=current_user.tenant_id,
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
