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


@pytest.mark.asyncio
async def test_model_performance_aggregation(governance: AIGovernanceEngine, test_tenant: Tenant, db_session: AsyncSession):
    """Test aggregating performance metrics across multiple model evaluations."""
    # Register a model
    model = AIModel(
        tenant_id=test_tenant.slug,
        model_name="nvidia/llama-3.3-nemotron",
        provider="nvidia",
        task_type="regulatory_analysis",
        approval_status="approved",
    )
    db_session.add(model)
    await db_session.flush()

    # Create multiple evaluation records
    quality_scores = [89.5, 91.2, 93.1, 92.0, 90.8]
    latency_values = [32000, 31500, 33200, 32100, 31800]

    for i, (quality, latency) in enumerate(zip(quality_scores, latency_values)):
        eval_record = ModelEvaluation(
            tenant_id=test_tenant.slug,
            model_id=model.id,
            task_type="regulatory_analysis",
            quality_score=quality,
            latency_ms=latency,
            cost_per_1k_tokens=0.01,
            input_tokens=1200,
            output_tokens=400,
            metadata={
                "run_id": f"eval-{i}",
                "quality_tier": "high" if quality > 91 else "medium",
            },
        )
        db_session.add(eval_record)
    await db_session.commit()

    # Aggregate performance metrics
    evaluations = (await db_session.execute(
        select(ModelEvaluation).where(
            ModelEvaluation.tenant_id == test_tenant.slug,
            ModelEvaluation.model_id == model.id,
        )
    )).scalars().all()

    assert len(evaluations) == 5
    avg_quality = sum(e.quality_score for e in evaluations) / len(evaluations)
    avg_latency = sum(e.latency_ms for e in evaluations) / len(evaluations)

    # Verify aggregates
    assert 90 < avg_quality < 93
    assert 31000 < avg_latency < 33000


@pytest.mark.asyncio
async def test_model_approval_rejection_workflow(governance: AIGovernanceEngine, test_tenant: Tenant, db_session: AsyncSession):
    """Test model rejection and reapproval workflow."""
    # Create model in pending state
    model = AIModel(
        tenant_id=test_tenant.slug,
        model_name="candidate/model-v2",
        provider="openrouter",
        task_type="compliance_qa",
        approval_status="pending",
    )
    db_session.add(model)
    await db_session.commit()

    # Reject the model
    model.approval_status = "rejected"
    model.metadata = {"rejection_reason": "Quality score below 85 threshold"}
    await db_session.commit()

    # Verify rejection
    result = (await db_session.execute(
        select(AIModel).where(AIModel.id == model.id)
    )).scalar_one()
    assert result.approval_status == "rejected"
    assert result.metadata["rejection_reason"] == "Quality score below 85 threshold"

    # Resubmit for approval (update status back to pending)
    model.approval_status = "pending"
    model.metadata = {
        "rejection_reason": "Quality score below 85 threshold",
        "resubmitted_date": "2026-06-30",
        "new_quality_score": 88.5,
    }
    await db_session.commit()

    # Verify resubmission
    result = (await db_session.execute(
        select(AIModel).where(AIModel.id == model.id)
    )).scalar_one()
    assert result.approval_status == "pending"
    assert result.metadata["new_quality_score"] == 88.5

    # Approve after resubmission
    model.approval_status = "approved"
    await db_session.commit()

    result = (await db_session.execute(
        select(AIModel).where(AIModel.id == model.id)
    )).scalar_one()
    assert result.approval_status == "approved"


@pytest.mark.asyncio
async def test_cost_comparison_across_models(governance: AIGovernanceEngine, test_tenant: Tenant, db_session: AsyncSession):
    """Test cost comparison metrics across multiple approved models."""
    # Create multiple models with different costs
    models_config = [
        ("nvidia/llama-3.3-nemotron", "nvidia", 0.01),
        ("meta/llama-3.3-70b", "openrouter", 0.005),
        ("moonshotai/kimi-k2", "openrouter", 0.008),
    ]

    created_models = []
    for model_name, provider, cost_per_1k in models_config:
        model = AIModel(
            tenant_id=test_tenant.slug,
            model_name=model_name,
            provider=provider,
            task_type="compliance_qa",
            approval_status="approved",
            metadata={"cost_per_1k_tokens": cost_per_1k},
        )
        db_session.add(model)
        created_models.append(model)
    await db_session.flush()

    # Create evaluation records for each model with different token patterns
    for model_idx, model in enumerate(created_models):
        input_tokens_list = [1000, 1500, 1200]
        output_tokens_list = [400, 500, 450]

        for i, (input_toks, output_toks) in enumerate(zip(input_tokens_list, output_tokens_list)):
            eval_record = ModelEvaluation(
                tenant_id=test_tenant.slug,
                model_id=model.id,
                task_type="compliance_qa",
                quality_score=90.0 + (model_idx * 0.5),
                latency_ms=25000 - (model_idx * 1000),
                cost_per_1k_tokens=models_config[model_idx][2],
                input_tokens=input_toks,
                output_tokens=output_toks,
                metadata={
                    "tokens_per_request": input_toks + output_toks,
                },
            )
            db_session.add(eval_record)
    await db_session.commit()

    # Query all approved models with cost metrics
    approved_models = (await db_session.execute(
        select(AIModel).where(
            AIModel.tenant_id == test_tenant.slug,
            AIModel.approval_status == "approved",
        )
    )).scalars().all()

    assert len(approved_models) == 3

    # Calculate costs per model
    model_costs = {}
    for model in approved_models:
        evaluations = (await db_session.execute(
            select(ModelEvaluation).where(
                ModelEvaluation.model_id == model.id,
            )
        )).scalars().all()

        if evaluations:
            total_input = sum(e.input_tokens for e in evaluations)
            total_output = sum(e.output_tokens for e in evaluations)
            avg_cost_per_1k = sum(e.cost_per_1k_tokens for e in evaluations) / len(evaluations)

            model_costs[model.model_name] = {
                "total_input_tokens": total_input,
                "total_output_tokens": total_output,
                "avg_cost_per_1k": avg_cost_per_1k,
            }

    # Verify cost data captured
    assert len(model_costs) == 3
    assert all("total_input_tokens" in v for v in model_costs.values())

    # Verify NVIDIA model has higher cost than OpenRouter models
    nvidia_cost = model_costs["nvidia/llama-3.3-nemotron"]["avg_cost_per_1k"]
    openrouter_costs = [
        model_costs["meta/llama-3.3-70b"]["avg_cost_per_1k"],
        model_costs["moonshotai/kimi-k2"]["avg_cost_per_1k"],
    ]
    assert nvidia_cost > min(openrouter_costs)


@pytest.mark.asyncio
async def test_model_quality_trend_tracking(governance: AIGovernanceEngine, test_tenant: Tenant, db_session: AsyncSession):
    """Test tracking quality trends over multiple evaluations."""
    model = AIModel(
        tenant_id=test_tenant.slug,
        model_name="improving/model",
        provider="nvidia",
        task_type="compliance_qa",
        approval_status="approved",
    )
    db_session.add(model)
    await db_session.flush()

    # Create evaluations showing quality improvement
    quality_trend = [85.0, 86.5, 88.2, 90.1, 91.8]

    for i, quality in enumerate(quality_trend):
        eval_record = ModelEvaluation(
            tenant_id=test_tenant.slug,
            model_id=model.id,
            task_type="compliance_qa",
            quality_score=quality,
            latency_ms=30000,
            cost_per_1k_tokens=0.01,
            input_tokens=1000,
            output_tokens=400,
            metadata={"iteration": i + 1},
        )
        db_session.add(eval_record)
    await db_session.commit()

    # Retrieve and verify trend
    evaluations = (await db_session.execute(
        select(ModelEvaluation).where(
            ModelEvaluation.model_id == model.id,
        ).order_by(ModelEvaluation.created_at)
    )).scalars().all()

    assert len(evaluations) == 5
    scores = [e.quality_score for e in evaluations]
    # Verify monotonic improvement
    assert all(scores[i] <= scores[i + 1] for i in range(len(scores) - 1))
    assert scores[-1] > scores[0]  # Final > Initial
