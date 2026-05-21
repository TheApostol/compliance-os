from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth import CurrentUser, get_current_user
from app.modules.workflows.engine import get_workflow_engine
from app.modules.predictive.engine import get_predictive_engine

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
