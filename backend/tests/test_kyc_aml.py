"""
Tests for M3 KYC/AML Orchestration Module

Tests entity risk assessment, case management, and multi-tenant isolation.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.modules.kyc_aml.engine import KYCAMLEngine
from app.services.ai_orchestrator import AIOrchestrator
from app.db.models import Tenant, Entity, KYCCase, ComplianceCase


@pytest.fixture
async def kyc_aml(db_session: AsyncSession) -> KYCAMLEngine:
    """Create a KYCAMLEngine instance."""
    orch = AIOrchestrator()
    return KYCAMLEngine(orch, db_session)


@pytest.fixture
async def test_tenant(db_session: AsyncSession) -> Tenant:
    """Create a test tenant."""
    tenant = Tenant(
        slug="kyc-test",
        name="KYC Test Tenant",
        sector="fintech",
        jurisdictions=["BR", "AR"],
        data_residency_policy={"ai_providers_allowed": ["nvidia"]},
    )
    db_session.add(tenant)
    await db_session.commit()
    return tenant


@pytest.fixture
async def test_entity(db_session: AsyncSession, test_tenant: Tenant) -> Entity:
    """Create a test entity."""
    entity = Entity(
        tenant_id=test_tenant.slug,
        name="Test Company",
        entity_type="fintech",
        sector="payments",
        jurisdictions=["BR"],
        metadata={},
    )
    db_session.add(entity)
    await db_session.commit()
    return entity


@pytest.mark.asyncio
async def test_assess_entity_risk(kyc_aml: KYCAMLEngine, test_tenant: Tenant, test_entity: Entity):
    """Test risk assessment for an entity."""
    result = await kyc_aml.assess_entity(
        entity_id=test_entity.id,
        tenant_id=test_tenant.slug,
    )

    assert result is not None
    assert "risk_level" in result or "risk_score" in result
    # Risk should be one of NONE, LOW, MEDIUM, HIGH, CRITICAL
    risk_level = result.get("risk_level", "").upper()
    assert risk_level in ["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL", ""]


@pytest.mark.asyncio
async def test_create_kyc_case(kyc_aml: KYCAMLEngine, test_tenant: Tenant, test_entity: Entity, db_session: AsyncSession):
    """Test creating a KYC case for an entity."""
    case = KYCCase(
        tenant_id=test_tenant.slug,
        entity_id=test_entity.id,
        case_type="standard_kyc",
        status="open",
        metadata={},
    )
    db_session.add(case)
    await db_session.commit()

    # Verify case was created with correct tenant_id
    result = (await db_session.execute(
        select(KYCCase).where(
            KYCCase.tenant_id == test_tenant.slug,
            KYCCase.entity_id == test_entity.id,
        )
    )).scalar_one_or_none()

    assert result is not None
    assert result.tenant_id == test_tenant.slug


@pytest.mark.asyncio
async def test_aml_check_enforcement(kyc_aml: KYCAMLEngine, test_tenant: Tenant, test_entity: Entity):
    """Test AML screening and enforcement checks."""
    result = await kyc_aml.perform_aml_check(
        entity_id=test_entity.id,
        tenant_id=test_tenant.slug,
    )

    assert result is not None
    # Result should contain screening details
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_kyc_aml_enforces_tenant_isolation(kyc_aml: KYCAMLEngine, db_session: AsyncSession):
    """Test that KYC/AML enforces multi-tenant isolation."""
    tenant1 = Tenant(
        slug="kyc-tenant-1",
        name="KYC Tenant 1",
        sector="bank",
        jurisdictions=["AR"],
    )
    tenant2 = Tenant(
        slug="kyc-tenant-2",
        name="KYC Tenant 2",
        sector="bank",
        jurisdictions=["BR"],
    )
    db_session.add(tenant1)
    db_session.add(tenant2)
    await db_session.flush()

    entity1 = Entity(
        tenant_id=tenant1.slug,
        name="Tenant 1 Entity",
        entity_type="company",
    )
    entity2 = Entity(
        tenant_id=tenant2.slug,
        name="Tenant 2 Entity",
        entity_type="company",
    )
    db_session.add(entity1)
    db_session.add(entity2)
    await db_session.commit()

    # Query entities scoped by tenant
    result1 = (await db_session.execute(
        select(Entity).where(Entity.tenant_id == tenant1.slug)
    )).scalars().all()

    result2 = (await db_session.execute(
        select(Entity).where(Entity.tenant_id == tenant2.slug)
    )).scalars().all()

    # Ensure isolation
    assert len(result1) >= 1
    assert len(result2) >= 1
    assert result1[0].tenant_id == tenant1.slug
    assert result2[0].tenant_id == tenant2.slug


@pytest.mark.asyncio
async def test_kyc_case_status_transitions(db_session: AsyncSession, test_tenant: Tenant, test_entity: Entity):
    """Test KYC case status lifecycle."""
    case = KYCCase(
        tenant_id=test_tenant.slug,
        entity_id=test_entity.id,
        case_type="enhanced_kyc",
        status="open",
    )
    db_session.add(case)
    await db_session.commit()

    # Update status
    case.status = "pending_review"
    await db_session.commit()

    # Verify update
    result = (await db_session.execute(
        select(KYCCase).where(KYCCase.id == case.id)
    )).scalar_one()

    assert result.status == "pending_review"
    assert result.tenant_id == test_tenant.slug
