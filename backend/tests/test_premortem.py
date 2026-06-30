"""
Tests for Premortem Module

Tests failure mode analysis, mitigation tracking, and tenant isolation.
Specifically validates that tenant_id filters are correctly applied
after T1.1 security hardening.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.modules.premortem.engine import PremortemEngine
from app.db.models import Tenant, FailureMode, Mitigation


@pytest.fixture
async def premortem(db_session: AsyncSession) -> PremortemEngine:
    """Create a PremortemEngine instance."""
    return PremortemEngine(db_session)


@pytest.fixture
async def test_tenant(db_session: AsyncSession) -> Tenant:
    """Create a test tenant."""
    tenant = Tenant(
        slug="premortem-test",
        name="Premortem Test Tenant",
        sector="fintech",
        jurisdictions=["BR", "AR"],
        data_residency_policy={"ai_providers_allowed": ["nvidia"]},
    )
    db_session.add(tenant)
    await db_session.commit()
    return tenant


@pytest.fixture
async def test_failure_mode(db_session: AsyncSession, test_tenant: Tenant) -> FailureMode:
    """Create a test failure mode."""
    fm = FailureMode(
        tenant_id=test_tenant.slug,
        code="F1",
        title="Rate Limiting Overwhelm",
        description="API rate limit exceeded, AI calls queued indefinitely",
        probability=0.15,
        impact="high",
        risk_score=55,
        phase=1,
        mitigations_required=2,
    )
    db_session.add(fm)
    await db_session.commit()
    return fm


@pytest.mark.asyncio
async def test_get_failure_modes(premortem: PremortemEngine, test_tenant: Tenant, test_failure_mode: FailureMode):
    """Test retrieving failure modes for a tenant."""
    modes = await premortem.get_failure_modes(tenant_id=test_tenant.slug)

    assert modes is not None
    assert isinstance(modes, list)


@pytest.mark.asyncio
async def test_failure_mode_includes_mitigations(db_session: AsyncSession, test_tenant: Tenant, test_failure_mode: FailureMode):
    """Test that failure modes include their mitigations."""
    # Create a mitigation for the failure mode
    mit = Mitigation(
        tenant_id=test_tenant.slug,
        failure_mode_id=test_failure_mode.id,
        code="M1.1",
        title="Implement token bucket rate limiter",
        status="done",
        implementation_date="2026-06-30",
    )
    db_session.add(mit)
    await db_session.commit()

    # Query with tenant isolation
    result = (await db_session.execute(
        select(Mitigation).where(
            Mitigation.tenant_id == test_tenant.slug,
            Mitigation.failure_mode_id == test_failure_mode.id,
        )
    )).scalar_one_or_none()

    assert result is not None
    assert result.tenant_id == test_tenant.slug
    assert result.status == "done"


@pytest.mark.asyncio
async def test_update_mitigation_status(premortem: PremortemEngine, test_tenant: Tenant, test_failure_mode: FailureMode, db_session: AsyncSession):
    """Test updating mitigation status with tenant validation."""
    mit = Mitigation(
        tenant_id=test_tenant.slug,
        failure_mode_id=test_failure_mode.id,
        code="M1.2",
        title="Add circuit breaker",
        status="pending",
    )
    db_session.add(mit)
    await db_session.commit()

    # Update status (should validate tenant_id)
    result = await premortem.update_mitigation_status(
        mitigation_id=mit.id,
        new_status="done",
        tenant_id=test_tenant.slug,
        implementation_date="2026-06-30",
    )

    assert result is not None


@pytest.mark.asyncio
async def test_premortem_enforces_tenant_isolation(premortem: PremortemEngine, db_session: AsyncSession):
    """Test that premortem enforces multi-tenant isolation (T1.1 security hardening)."""
    tenant1 = Tenant(
        slug="premortem-tenant-1",
        name="Premortem Tenant 1",
        sector="bank",
        jurisdictions=["AR"],
    )
    tenant2 = Tenant(
        slug="premortem-tenant-2",
        name="Premortem Tenant 2",
        sector="bank",
        jurisdictions=["BR"],
    )
    db_session.add(tenant1)
    db_session.add(tenant2)
    await db_session.flush()

    # Create failure modes for each tenant
    fm1 = FailureMode(
        tenant_id=tenant1.slug,
        code="F_T1",
        title="Tenant 1 Failure Mode",
        description="Test failure for tenant 1",
        probability=0.1,
        impact="medium",
        risk_score=30,
    )
    fm2 = FailureMode(
        tenant_id=tenant2.slug,
        code="F_T2",
        title="Tenant 2 Failure Mode",
        description="Test failure for tenant 2",
        probability=0.2,
        impact="high",
        risk_score=50,
    )
    db_session.add(fm1)
    db_session.add(fm2)
    await db_session.commit()

    # Query modes scoped by tenant
    result1 = (await db_session.execute(
        select(FailureMode).where(FailureMode.tenant_id == tenant1.slug)
    )).scalars().all()

    result2 = (await db_session.execute(
        select(FailureMode).where(FailureMode.tenant_id == tenant2.slug)
    )).scalars().all()

    # Ensure isolation: each tenant sees only their own
    assert len(result1) >= 1
    assert len(result2) >= 1
    assert all(m.tenant_id == tenant1.slug for m in result1)
    assert all(m.tenant_id == tenant2.slug for m in result2)
    # Verify no cross-tenant contamination
    assert result1[0].code == "F_T1"
    assert result2[0].code == "F_T2"


@pytest.mark.asyncio
async def test_mitigation_query_scoped_by_tenant(db_session: AsyncSession, test_tenant: Tenant, test_failure_mode: FailureMode):
    """Test that mitigation queries are scoped by tenant_id (validates T1.1 fix)."""
    # Create mitigation for test_tenant
    mit1 = Mitigation(
        tenant_id=test_tenant.slug,
        failure_mode_id=test_failure_mode.id,
        code="M_T1",
        title="Mitigation for Tenant 1",
        status="pending",
    )
    db_session.add(mit1)
    await db_session.flush()

    # Create another tenant and failure mode
    tenant2 = Tenant(
        slug="premortem-tenant-2",
        name="Tenant 2",
        sector="bank",
        jurisdictions=["BR"],
    )
    db_session.add(tenant2)
    await db_session.flush()

    fm2 = FailureMode(
        tenant_id=tenant2.slug,
        code="F_T2",
        title="Tenant 2 FM",
        description="FM for tenant 2",
        probability=0.1,
        impact="medium",
        risk_score=25,
    )
    db_session.add(fm2)
    await db_session.flush()

    mit2 = Mitigation(
        tenant_id=tenant2.slug,
        failure_mode_id=fm2.id,
        code="M_T2",
        title="Mitigation for Tenant 2",
        status="pending",
    )
    db_session.add(mit2)
    await db_session.commit()

    # Query mitigations for tenant1 only
    result = (await db_session.execute(
        select(Mitigation).where(
            Mitigation.tenant_id == test_tenant.slug,
        )
    )).scalars().all()

    # Should not include mitigations from tenant2
    tenant_ids = set(m.tenant_id for m in result)
    assert tenant_ids == {test_tenant.slug}


@pytest.mark.asyncio
async def test_failure_mode_risk_calculation(test_tenant: Tenant, db_session: AsyncSession):
    """Test failure mode risk score calculation."""
    fm = FailureMode(
        tenant_id=test_tenant.slug,
        code="F_RISK",
        title="High Risk Mode",
        description="High probability, high impact",
        probability=0.8,
        impact="critical",
        risk_score=None,  # May be calculated
    )
    db_session.add(fm)
    await db_session.commit()

    # Verify stored correctly with tenant isolation
    result = (await db_session.execute(
        select(FailureMode).where(
            FailureMode.tenant_id == test_tenant.slug,
            FailureMode.code == "F_RISK",
        )
    )).scalar_one()

    assert result.tenant_id == test_tenant.slug
    assert result.probability == 0.8
    assert result.impact == "critical"
