"""Premortem API endpoints — Failure mode analysis and mitigation tracking."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Any
from uuid import UUID

from app.core.auth import CurrentUser, get_current_user
from app.db.base import AsyncSessionLocal
from app.modules.premortem.engine import PremortermEngine
from app.db.models import FailureModeSeverity, FailureModeStatus

premortem_router = APIRouter(prefix="/api/v1/premortem", tags=["premortem"])


# ═══════════════════════════════════════════════════════════════════
# Request/Response Models
# ═══════════════════════════════════════════════════════════════════

class FailureModeCreate(BaseModel):
    scenario: str
    description: str
    impact: str
    likelihood: str
    severity: str
    category: str
    affected_modules: list[str] = []


class FailureModeUpdate(BaseModel):
    status: str


class MitigationCreate(BaseModel):
    failure_mode_id: str
    mitigation: str
    owner: str | None = None
    effort_estimate: str | None = None
    priority: int = 0


class MitigationUpdate(BaseModel):
    status: str


class FindingCreate(BaseModel):
    title: str
    description: str
    finding_type: str
    priority: str = "medium"
    related_failure_modes: list[str] = []


# ═══════════════════════════════════════════════════════════════════
# Endpoints
# ═══════════════════════════════════════════════════════════════════

@premortem_router.get("/summary")
async def get_premortem_summary(user: CurrentUser = Depends(get_current_user)):
    """Get overall premortem health summary."""
    async with AsyncSessionLocal() as session:
        engine = PremortermEngine(session)
        summary = await engine.get_premortem_summary(user.tenant_id)
        return summary


@premortem_router.get("/failure-modes")
async def list_failure_modes(
    user: CurrentUser = Depends(get_current_user),
    category: str | None = Query(None),
    severity: str | None = Query(None),
):
    """List failure modes, optionally filtered by category or severity."""
    async with AsyncSessionLocal() as session:
        engine = PremortermEngine(session)
        sev = FailureModeSeverity(severity) if severity else None
        modes = await engine.get_failure_modes(user.tenant_id, category, sev)
        return {"failure_modes": modes}


@premortem_router.get("/failure-modes/{mode_id}")
async def get_failure_mode(mode_id: str, user: CurrentUser = Depends(get_current_user)):
    """Retrieve a specific failure mode with its mitigations."""
    try:
        mode_uuid = UUID(mode_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid mode ID format")

    async with AsyncSessionLocal() as session:
        engine = PremortermEngine(session)
        mode = await engine.get_failure_mode(user.tenant_id, mode_uuid)
        if not mode:
            raise HTTPException(status_code=404, detail="Failure mode not found")
        return mode


@premortem_router.post("/failure-modes")
async def create_failure_mode(
    req: FailureModeCreate, user: CurrentUser = Depends(get_current_user)
):
    """Create a new failure mode."""
    try:
        severity = FailureModeSeverity(req.severity)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid severity value")

    async with AsyncSessionLocal() as session:
        engine = PremortermEngine(session)
        mode = await engine.create_failure_mode(
            tenant_id=user.tenant_id,
            scenario=req.scenario,
            description=req.description,
            impact=req.impact,
            likelihood=req.likelihood,
            severity=severity,
            category=req.category,
            affected_modules=req.affected_modules,
        )
        await session.commit()
        return mode


@premortem_router.patch("/failure-modes/{mode_id}")
async def update_failure_mode_status(
    mode_id: str, req: FailureModeUpdate, user: CurrentUser = Depends(get_current_user)
):
    """Update failure mode status."""
    try:
        mode_uuid = UUID(mode_id)
        status = FailureModeStatus(req.status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid value: {str(e)}")

    async with AsyncSessionLocal() as session:
        engine = PremortermEngine(session)
        mode = await engine.update_failure_mode_status(user.tenant_id, mode_uuid, status)
        if not mode:
            raise HTTPException(status_code=404, detail="Failure mode not found")
        await session.commit()
        return mode


@premortem_router.post("/failure-modes/{mode_id}/mitigations")
async def create_mitigation(
    mode_id: str, req: MitigationCreate, user: CurrentUser = Depends(get_current_user)
):
    """Create a mitigation for a failure mode."""
    try:
        mode_uuid = UUID(mode_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid mode ID format")

    async with AsyncSessionLocal() as session:
        engine = PremortermEngine(session)
        # Verify failure mode exists
        mode = await engine.get_failure_mode(user.tenant_id, mode_uuid)
        if not mode:
            raise HTTPException(status_code=404, detail="Failure mode not found")

        mit = await engine.create_mitigation(
            tenant_id=user.tenant_id,
            failure_mode_id=mode_uuid,
            mitigation=req.mitigation,
            owner=req.owner,
            effort_estimate=req.effort_estimate,
            priority=req.priority,
        )
        await session.commit()
        return mit


@premortem_router.get("/mitigations/{mit_id}")
async def get_mitigation(mit_id: str, user: CurrentUser = Depends(get_current_user)):
    """Retrieve a specific mitigation."""
    try:
        mit_uuid = UUID(mit_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid mitigation ID format")

    async with AsyncSessionLocal() as session:
        engine = PremortermEngine(session)
        # Note: mitigation doesn't have direct retrieval, get through failure mode
        # For now, return not implemented; can enhance if needed
        raise HTTPException(status_code=501, detail="Use failure-modes/{mode_id} to get mitigations")


@premortem_router.patch("/mitigations/{mit_id}")
async def update_mitigation_status(
    mit_id: str, req: MitigationUpdate, user: CurrentUser = Depends(get_current_user)
):
    """Update mitigation status."""
    try:
        mit_uuid = UUID(mit_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid mitigation ID format")

    async with AsyncSessionLocal() as session:
        engine = PremortermEngine(session)
        mit = await engine.update_mitigation_status(mit_uuid, req.status)
        if not mit:
            raise HTTPException(status_code=404, detail="Mitigation not found")
        await session.commit()
        return mit


@premortem_router.get("/findings")
async def list_findings(
    user: CurrentUser = Depends(get_current_user),
    finding_type: str | None = Query(None),
):
    """List premortem findings."""
    async with AsyncSessionLocal() as session:
        engine = PremortermEngine(session)
        findings = await engine.get_findings(user.tenant_id, finding_type)
        return {"findings": findings}


@premortem_router.post("/findings")
async def create_finding(
    req: FindingCreate, user: CurrentUser = Depends(get_current_user)
):
    """Create a premortem finding."""
    async with AsyncSessionLocal() as session:
        engine = PremortermEngine(session)
        # Convert string UUIDs to actual UUIDs
        failure_mode_ids = []
        for fm_id in req.related_failure_modes:
            try:
                failure_mode_ids.append(UUID(fm_id))
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid failure mode ID: {fm_id}")

        finding = await engine.create_finding(
            tenant_id=user.tenant_id,
            title=req.title,
            description=req.description,
            finding_type=req.finding_type,
            priority=req.priority,
            related_failure_modes=failure_mode_ids,
        )
        await session.commit()
        return finding
