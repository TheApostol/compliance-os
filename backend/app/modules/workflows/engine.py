from __future__ import annotations

from app.modules.workflows.models import Workflow, WorkflowStep
from app.db.base import AsyncSessionLocal


class WorkflowEngine:

    async def create_remediation_workflow(self, tenant_id: str, title: str, trigger_source: str, severity: str = 'medium'):
        async with AsyncSessionLocal() as session:
            wf = Workflow(
                tenant_id=tenant_id,
                workflow_type='remediation',
                title=title,
                trigger_source=trigger_source,
                severity=severity,
            )
            session.add(wf)
            await session.flush()

            default_steps = [
                ('impact_analysis', 'Analyze regulatory impact', False),
                ('policy_review', 'Review affected policies', True),
                ('evidence_collection', 'Collect evidence', False),
                ('final_approval', 'Compliance officer approval', True),
            ]

            for idx, (stype, stitle, approval) in enumerate(default_steps):
                session.add(WorkflowStep(
                    workflow_id=wf.id,
                    step_type=stype,
                    title=stitle,
                    requires_approval=approval,
                    order_index=idx,
                ))

            await session.commit()
            await session.refresh(wf)

            return {
                'workflow_id': str(wf.id),
                'status': wf.status.value,
                'title': wf.title,
            }


_engine = WorkflowEngine()


def get_workflow_engine():
    return _engine
