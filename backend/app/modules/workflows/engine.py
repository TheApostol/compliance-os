"""
M7 — Workflow Orchestration & Remediation
==========================================
Real state machine: DAG-validated step graphs, dependency gating,
approval gating, and timeout-based escalation (premortem F9 mitigation).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select

from app.modules.workflows.models import Workflow, WorkflowStatus, WorkflowStep
from app.db.base import AsyncSessionLocal

DEFAULT_STEP_TIMEOUT_DAYS = 7


class WorkflowError(ValueError):
    """Raised for invalid DAGs or illegal state transitions."""


def _validate_dag(steps: list[dict[str, Any]]) -> None:
    """DFS-based cycle detection over step.depends_on edges (premortem F9)."""
    by_index = {s["order_index"]: s for s in steps}
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {idx: WHITE for idx in by_index}

    def visit(idx: int) -> None:
        if idx not in by_index:
            raise WorkflowError(f"step depends_on references unknown order_index {idx}")
        if color[idx] == GRAY:
            raise WorkflowError(f"cycle detected in workflow DAG at step {idx}")
        if color[idx] == BLACK:
            return
        color[idx] = GRAY
        for dep in by_index[idx].get("depends_on") or []:
            visit(dep)
        color[idx] = BLACK

    for idx in by_index:
        if color[idx] == WHITE:
            visit(idx)


class WorkflowEngine:

    async def create_remediation_workflow(
        self, tenant_id: str, title: str, trigger_source: str, severity: str = "medium"
    ) -> dict[str, Any]:
        default_steps = [
            {"step_type": "impact_analysis", "title": "Analyze regulatory impact", "requires_approval": False},
            {"step_type": "policy_review", "title": "Review affected policies", "requires_approval": True},
            {"step_type": "evidence_collection", "title": "Collect evidence", "requires_approval": False},
            {"step_type": "final_approval", "title": "Compliance officer approval", "requires_approval": True},
        ]
        # default workflow is strictly linear: each step gated on the previous one
        for idx, step in enumerate(default_steps):
            step["order_index"] = idx
            step["depends_on"] = [idx - 1] if idx > 0 else []

        return await self.create_workflow(
            tenant_id=tenant_id,
            workflow_type="remediation",
            title=title,
            trigger_source=trigger_source,
            severity=severity,
            steps=default_steps,
        )

    async def create_workflow(
        self,
        tenant_id: str,
        workflow_type: str,
        title: str,
        trigger_source: str,
        severity: str,
        steps: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not steps:
            raise WorkflowError("workflow must have at least one step")
        _validate_dag(steps)

        async with AsyncSessionLocal() as session:
            wf = Workflow(
                tenant_id=tenant_id,
                workflow_type=workflow_type,
                title=title,
                trigger_source=trigger_source,
                severity=severity,
            )
            session.add(wf)
            await session.flush()

            now = datetime.now(timezone.utc)
            for step in steps:
                session.add(WorkflowStep(
                    workflow_id=wf.id,
                    step_type=step["step_type"],
                    title=step["title"],
                    requires_approval=step.get("requires_approval", False),
                    order_index=step["order_index"],
                    depends_on=step.get("depends_on") or [],
                    due_at=now + timedelta(days=step.get("timeout_days", DEFAULT_STEP_TIMEOUT_DAYS)),
                ))

            # the workflow starts RUNNING if its first eligible step needs no approval
            first_steps = [s for s in steps if not s.get("depends_on")]
            wf.status = (
                WorkflowStatus.APPROVAL_REQUIRED
                if any(s.get("requires_approval") for s in first_steps)
                else WorkflowStatus.RUNNING
            )

            await session.commit()
            await session.refresh(wf)
            return await self._workflow_to_dict(session, wf)

    async def get_workflow(self, tenant_id: str, workflow_id: str) -> dict[str, Any] | None:
        async with AsyncSessionLocal() as session:
            wf = await self._load_workflow(session, tenant_id, workflow_id)
            if wf is None:
                return None
            return await self._workflow_to_dict(session, wf)

    async def list_workflows(self, tenant_id: str, status: str | None = None) -> list[dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            stmt = select(Workflow).where(Workflow.tenant_id == tenant_id)
            if status:
                stmt = stmt.where(Workflow.status == WorkflowStatus(status))
            stmt = stmt.order_by(Workflow.created_at.desc())
            result = await session.execute(stmt)
            workflows = result.scalars().all()
            return [await self._workflow_to_dict(session, wf) for wf in workflows]

    async def advance_step(
        self,
        tenant_id: str,
        workflow_id: str,
        step_id: str,
        action: str,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """action in {'approve', 'complete', 'reject'}. Enforces dependency + approval gating."""
        if action not in {"approve", "complete", "reject"}:
            raise WorkflowError(f"unknown action '{action}'")

        async with AsyncSessionLocal() as session:
            wf = await self._load_workflow(session, tenant_id, workflow_id)
            if wf is None:
                raise WorkflowError("workflow not found")

            step = next((s for s in wf.steps if str(s.id) == str(step_id)), None)
            if step is None:
                raise WorkflowError("step not found on workflow")
            if step.completed or step.status == "rejected":
                raise WorkflowError(f"step already in terminal state '{step.status}'")

            unmet = [
                dep for dep in (step.depends_on or [])
                if not any(s.order_index == dep and s.completed for s in wf.steps)
            ]
            if unmet:
                raise WorkflowError(f"step blocked — unmet dependencies on steps {unmet}")

            now = datetime.now(timezone.utc)
            if step.started_at is None:
                step.started_at = now

            if action == "reject":
                step.status = "rejected"
                wf.status = WorkflowStatus.ESCALATED
            elif action == "approve":
                if not step.requires_approval:
                    raise WorkflowError("step does not require approval")
                step.approved_by = user_id or "unknown"
                step.status = "approved"
            elif action == "complete":
                if step.requires_approval and not step.approved_by:
                    raise WorkflowError("step requires approval before it can be completed")
                step.completed = True
                step.status = "completed"
                step.completed_at = now

            await session.flush()
            await self._recompute_status(session, wf)
            await session.commit()
            await session.refresh(wf)
            return await self._workflow_to_dict(session, wf)

    async def check_step_timeouts(self, tenant_id: str | None = None) -> list[dict[str, Any]]:
        """Escalate any open step past its due_at. Intended to run on a schedule (premortem T3.2)."""
        now = datetime.now(timezone.utc)
        escalated: list[dict[str, Any]] = []
        async with AsyncSessionLocal() as session:
            stmt = select(WorkflowStep).where(
                WorkflowStep.completed.is_(False),
                WorkflowStep.escalated.is_(False),
                WorkflowStep.due_at.isnot(None),
                WorkflowStep.due_at < now,
            )
            result = await session.execute(stmt)
            for step in result.scalars().all():
                wf = await session.get(Workflow, step.workflow_id)
                if wf is None or (tenant_id and wf.tenant_id != tenant_id):
                    continue
                step.escalated = True
                wf.status = WorkflowStatus.ESCALATED
                escalated.append({"workflow_id": str(wf.id), "step_id": str(step.id), "title": step.title})
            await session.commit()
        return escalated

    async def _load_workflow(self, session, tenant_id: str, workflow_id: str) -> Workflow | None:
        stmt = select(Workflow).where(Workflow.id == workflow_id, Workflow.tenant_id == tenant_id)
        result = await session.execute(stmt)
        wf = result.scalar_one_or_none()
        if wf is not None:
            await session.refresh(wf, attribute_names=["steps"])
        return wf

    async def _recompute_status(self, session, wf: Workflow) -> None:
        await session.refresh(wf, attribute_names=["steps"])
        if any(s.status == "rejected" for s in wf.steps):
            wf.status = WorkflowStatus.ESCALATED
            return
        if all(s.completed for s in wf.steps):
            wf.status = WorkflowStatus.COMPLETED
            return

        completed_idx = {s.order_index for s in wf.steps if s.completed}
        eligible = [
            s for s in wf.steps
            if not s.completed and set(s.depends_on or []).issubset(completed_idx)
        ]
        wf.status = (
            WorkflowStatus.APPROVAL_REQUIRED
            if any(s.requires_approval and not s.approved_by for s in eligible)
            else WorkflowStatus.RUNNING
        )

    @staticmethod
    async def _workflow_to_dict(session, wf: Workflow) -> dict[str, Any]:
        await session.refresh(wf, attribute_names=["steps"])
        return {
            "workflow_id": str(wf.id),
            "workflow_type": wf.workflow_type,
            "title": wf.title,
            "trigger_source": wf.trigger_source,
            "severity": wf.severity,
            "status": wf.status.value,
            "created_at": wf.created_at.isoformat() if wf.created_at else None,
            "steps": [
                {
                    "step_id": str(s.id),
                    "step_type": s.step_type,
                    "title": s.title,
                    "status": s.status,
                    "order_index": s.order_index,
                    "depends_on": s.depends_on or [],
                    "requires_approval": s.requires_approval,
                    "completed": s.completed,
                    "approved_by": s.approved_by,
                    "escalated": s.escalated,
                    "due_at": s.due_at.isoformat() if s.due_at else None,
                    "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                }
                for s in sorted(wf.steps, key=lambda s: s.order_index)
            ],
        }


_engine = WorkflowEngine()


def get_workflow_engine() -> WorkflowEngine:
    return _engine
