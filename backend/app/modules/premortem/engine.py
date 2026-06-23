"""Premortem engine — Failure mode identification, mitigation planning, and risk tracking."""

from typing import Any
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.db.models import (
    PremortermFailureMode, PremortermMitigation, PremortermFinding,
    FailureModeSeverity, FailureModeStatus
)


class PremortermEngine:
    """Manages premortem failure modes, mitigations, and findings."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_failure_modes(
        self,
        tenant_id: str,
        category: str | None = None,
        severity: FailureModeSeverity | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve failure modes, optionally filtered by category or severity."""
        query = select(PremortermFailureMode).where(
            PremortermFailureMode.tenant_id == tenant_id
        )
        if category:
            query = query.where(PremortermFailureMode.category == category)
        if severity:
            query = query.where(PremortermFailureMode.severity == severity)

        result = await self.session.execute(query)
        modes = result.scalars().all()
        return [self._mode_to_dict(m) for m in modes]

    async def get_failure_mode(self, tenant_id: str, mode_id: UUID) -> dict[str, Any] | None:
        """Retrieve a specific failure mode with its mitigations."""
        query = select(PremortermFailureMode).where(
            and_(
                PremortermFailureMode.tenant_id == tenant_id,
                PremortermFailureMode.id == mode_id,
            )
        )
        result = await self.session.execute(query)
        mode = result.scalars().first()
        if not mode:
            return None

        # Get mitigations
        mit_query = select(PremortermMitigation).where(
            PremortermMitigation.failure_mode_id == mode_id
        )
        mit_result = await self.session.execute(mit_query)
        mitigations = mit_result.scalars().all()

        mode_dict = self._mode_to_dict(mode)
        mode_dict["mitigations"] = [self._mitigation_to_dict(m) for m in mitigations]
        return mode_dict

    async def create_failure_mode(
        self,
        tenant_id: str,
        scenario: str,
        description: str,
        impact: str,
        likelihood: str,
        severity: FailureModeSeverity,
        category: str,
        affected_modules: list[str],
    ) -> dict[str, Any]:
        """Create a new failure mode."""
        mode = PremortermFailureMode(
            tenant_id=tenant_id,
            scenario=scenario,
            description=description,
            impact=impact,
            likelihood=likelihood,
            severity=severity,
            category=category,
            affected_modules=affected_modules,
        )
        self.session.add(mode)
        await self.session.flush()
        return self._mode_to_dict(mode)

    async def update_failure_mode_status(
        self, tenant_id: str, mode_id: UUID, status: FailureModeStatus
    ) -> dict[str, Any] | None:
        """Update failure mode status."""
        query = select(PremortermFailureMode).where(
            and_(
                PremortermFailureMode.tenant_id == tenant_id,
                PremortermFailureMode.id == mode_id,
            )
        )
        result = await self.session.execute(query)
        mode = result.scalars().first()
        if not mode:
            return None

        mode.status = status
        await self.session.flush()
        return self._mode_to_dict(mode)

    async def get_mitigations(self, failure_mode_id: UUID) -> list[dict[str, Any]]:
        """Retrieve mitigations for a failure mode."""
        query = select(PremortermMitigation).where(
            PremortermMitigation.failure_mode_id == failure_mode_id
        )
        result = await self.session.execute(query)
        mitigations = result.scalars().all()
        return [self._mitigation_to_dict(m) for m in mitigations]

    async def create_mitigation(
        self,
        tenant_id: str,
        failure_mode_id: UUID,
        mitigation: str,
        owner: str | None = None,
        effort_estimate: str | None = None,
        priority: int = 0,
    ) -> dict[str, Any]:
        """Create a mitigation for a failure mode."""
        mit = PremortermMitigation(
            tenant_id=tenant_id,
            failure_mode_id=failure_mode_id,
            mitigation=mitigation,
            owner=owner,
            effort_estimate=effort_estimate,
            priority=priority,
        )
        self.session.add(mit)
        await self.session.flush()
        return self._mitigation_to_dict(mit)

    async def update_mitigation_status(
        self, mit_id: UUID, status: str
    ) -> dict[str, Any] | None:
        """Update mitigation status (pending/in_progress/completed)."""
        query = select(PremortermMitigation).where(PremortermMitigation.id == mit_id)
        result = await self.session.execute(query)
        mit = result.scalars().first()
        if not mit:
            return None

        mit.status = status
        await self.session.flush()
        return self._mitigation_to_dict(mit)

    async def get_findings(
        self, tenant_id: str, finding_type: str | None = None
    ) -> list[dict[str, Any]]:
        """Retrieve premortem findings."""
        query = select(PremortermFinding).where(PremortermFinding.tenant_id == tenant_id)
        if finding_type:
            query = query.where(PremortermFinding.finding_type == finding_type)

        result = await self.session.execute(query)
        findings = result.scalars().all()
        return [self._finding_to_dict(f) for f in findings]

    async def create_finding(
        self,
        tenant_id: str,
        title: str,
        description: str,
        finding_type: str,
        priority: str = "medium",
        related_failure_modes: list[UUID] | None = None,
    ) -> dict[str, Any]:
        """Create a premortem finding."""
        finding = PremortermFinding(
            tenant_id=tenant_id,
            title=title,
            description=description,
            finding_type=finding_type,
            priority=priority,
            related_failure_modes=related_failure_modes or [],
        )
        self.session.add(finding)
        await self.session.flush()
        return self._finding_to_dict(finding)

    async def get_premortem_summary(self, tenant_id: str) -> dict[str, Any]:
        """Get overall premortem health summary."""
        modes = await self.get_failure_modes(tenant_id)
        findings = await self.get_findings(tenant_id)

        severity_counts = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
        }
        for mode in modes:
            severity = mode.get("severity", "").lower()
            if severity in severity_counts:
                severity_counts[severity] += 1

        status_counts = {
            "identified": len([m for m in modes if m["status"] == "identified"]),
            "mitigated": len([m for m in modes if m["status"] == "mitigated"]),
            "resolved": len([m for m in modes if m["status"] == "resolved"]),
            "monitoring": len([m for m in modes if m["status"] == "monitoring"]),
        }

        return {
            "total_failure_modes": len(modes),
            "severity_distribution": severity_counts,
            "status_distribution": status_counts,
            "total_findings": len(findings),
            "findings_by_priority": {
                "critical": len([f for f in findings if f["priority"] == "critical"]),
                "high": len([f for f in findings if f["priority"] == "high"]),
                "medium": len([f for f in findings if f["priority"] == "medium"]),
                "low": len([f for f in findings if f["priority"] == "low"]),
            },
        }

    @staticmethod
    def _mode_to_dict(mode: PremortermFailureMode) -> dict[str, Any]:
        return {
            "id": str(mode.id),
            "scenario": mode.scenario,
            "description": mode.description,
            "impact": mode.impact,
            "likelihood": mode.likelihood,
            "severity": mode.severity.value,
            "category": mode.category,
            "affected_modules": mode.affected_modules,
            "status": mode.status.value,
            "created_at": mode.created_at.isoformat(),
            "updated_at": mode.updated_at.isoformat(),
        }

    @staticmethod
    def _mitigation_to_dict(mit: PremortermMitigation) -> dict[str, Any]:
        return {
            "id": str(mit.id),
            "failure_mode_id": str(mit.failure_mode_id),
            "mitigation": mit.mitigation,
            "owner": mit.owner,
            "effort_estimate": mit.effort_estimate,
            "priority": mit.priority,
            "status": mit.status,
            "due_date": mit.due_date.isoformat() if mit.due_date else None,
            "created_at": mit.created_at.isoformat(),
        }

    @staticmethod
    def _finding_to_dict(finding: PremortermFinding) -> dict[str, Any]:
        return {
            "id": str(finding.id),
            "title": finding.title,
            "description": finding.description,
            "finding_type": finding.finding_type,
            "priority": finding.priority,
            "related_failure_modes": finding.related_failure_modes,
            "status": finding.status,
            "created_at": finding.created_at.isoformat(),
        }
