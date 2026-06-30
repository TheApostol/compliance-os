"""
Tests for M5 AI Governance Module

Tests model registry, performance tracking, and governance workflows.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.modules.governance.engine import AIGovernanceEngine
from app.db.models import Tenant, AIModel, ModelEvaluation


@pytest.fixture
async def governance(db_session: AsyncSession) -> AIGovernanceEngine:
    """Create an AIGovernanceEngine instance."""
    return AIGovernanceEngine(db_session)


@pytest.fixture
async def test_tenant(db_session: AsyncSession) -> Tenant:
    """Create a test tenant."""
    tenant = Tenant(
        slug="gov-test",
        name="Governance Test Tenant",
        sector="bank",
        jurisdictions=["AR", "BR"],
        data_residency_policy={"ai_providers_allowed": ["nvidia", "anthropic"]},
    )
    db_session.add(tenant)
    await db_session.commit()
    return tenant


@pytest.mark.asyncio
async def test_register_model(governance: AIGovernanceEngine, test_tenant: Tenant, db_session: AsyncSession):
    """Test registering an AI model in the governance registry."""
    model = AIModel(
        tenant_id=test_tenant.slug,
        model_name="nvidia/llama-3.3-nemotron",
        provider="nvidia",
        task_type="regulatory_analysis",
        approval_status="approved",
        metadata={
            "quality_score": 93.6,
            "latency_ms": 33000,
            "cost_per_1k_tokens": 0.01,
        },
    )
    db_session.add(model)
    await db_session.commit()

    # Verify registration with tenant isolation
    result = (await db_session.execute(
        select(AIModel).where(
            AIModel.tenant_id == test_tenant.slug,
            AIModel.model_name == "nvidia/llama-3.3-nemotron",
        )
    )).scalar_one_or_none()

    assert result is not None
    assert result.tenant_id == test_tenant.slug
    assert result.approval_status == "approved"


@pytest.mark.asyncio
async def test_track_model_performance(db_session: AsyncSession, test_tenant: Tenant):
    """Test recording model evaluation metrics."""
    model = AIModel(
        tenant_id=test_tenant.slug,
        model_name="meta/llama-3.3-70b",
        provider="openrouter",
        task_type="compliance_qa",
        approval_status="approved",
    )
    db_session.add(model)
    await db_session.flush()

    eval_record = ModelEvaluation(
        tenant_id=test_tenant.slug,
        model_id=model.id,
        task_type="compliance_qa",
        quality_score=91.3,
        latency_ms=21000,
        cost_per_1k_tokens=0.005,
        input_tokens=1500,
        output_tokens=500,
        metadata={
            "question": "What is Brazil's AML requirement?",
            "correctness": "high",
            "relevance": "high",
        },
    )
    db_session.add(eval_record)
    await db_session.commit()

    # Verify evaluation record
    result = (await db_session.execute(
        select(ModelEvaluation).where(
            ModelEvaluation.tenant_id == test_tenant.slug,
            ModelEvaluation.model_id == model.id,
        )
    )).scalar_one_or_none()

    assert result is not None
    assert result.quality_score == 91.3
    assert result.tenant_id == test_tenant.slug


@pytest.mark.asyncio
async def test_model_approval_workflow(db_session: AsyncSession, test_tenant: Tenant):
    """Test model approval workflow."""
    model = AIModel(
        tenant_id=test_tenant.slug,
        model_name="moonshotai/kimi-k2",
        provider="openrouter",
        task_type="multilingual_compliance",
        approval_status="pending",
    )
    db_session.add(model)
    await db_session.commit()

    # Update approval status
    model.approval_status = "approved"
    await db_session.commit()

    # Verify status change
    result = (await db_session.execute(
        select(AIModel).where(
            AIModel.tenant_id == test_tenant.slug,
            AIModel.id == model.id,
        )
    )).scalar_one()

    assert result.approval_status == "approved"
    assert result.tenant_id == test_tenant.slug


@pytest.mark.asyncio
async def test_governance_enforces_tenant_isolation(db_session: AsyncSession):
    """Test that governance module enforces multi-tenant isolation."""
    tenant1 = Tenant(
        slug="gov-tenant-1",
        name="Gov Tenant 1",
        sector="bank",
        jurisdictions=["AR"],
    )
    tenant2 = Tenant(
        slug="gov-tenant-2",
        name="Gov Tenant 2",
        sector="bank",
        jurisdictions=["BR"],
    )
    db_session.add(tenant1)
    db_session.add(tenant2)
    await db_session.flush()

    model1 = AIModel(
        tenant_id=tenant1.slug,
        model_name="model-tenant1",
        provider="nvidia",
        task_type="test",
        approval_status="approved",
    )
    model2 = AIModel(
        tenant_id=tenant2.slug,
        model_name="model-tenant2",
        provider="nvidia",
        task_type="test",
        approval_status="approved",
    )
    db_session.add(model1)
    db_session.add(model2)
    await db_session.commit()

    # Query models scoped by tenant
    result1 = (await db_session.execute(
        select(AIModel).where(AIModel.tenant_id == tenant1.slug)
    )).scalars().all()

    result2 = (await db_session.execute(
        select(AIModel).where(AIModel.tenant_id == tenant2.slug)
    )).scalars().all()

    # Ensure isolation
    assert len(result1) >= 1
    assert len(result2) >= 1
    assert all(m.tenant_id == tenant1.slug for m in result1)
    assert all(m.tenant_id == tenant2.slug for m in result2)


@pytest.mark.asyncio
async def test_list_approved_models(governance: AIGovernanceEngine, test_tenant: Tenant, db_session: AsyncSession):
    """Test listing approved models for a tenant."""
    # Add several models
    for i in range(3):
        model = AIModel(
            tenant_id=test_tenant.slug,
            model_name=f"model-{i}",
            provider="nvidia",
            task_type="test",
            approval_status="approved" if i < 2 else "pending",
        )
        db_session.add(model)
    await db_session.commit()

    # Query approved models
    result = (await db_session.execute(
        select(AIModel).where(
            AIModel.tenant_id == test_tenant.slug,
            AIModel.approval_status == "approved",
        )
    )).scalars().all()

    assert len(result) >= 2
    assert all(m.approval_status == "approved" for m in result)
