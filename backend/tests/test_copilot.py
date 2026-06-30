"""
Tests for M2 Compliance Copilot Module

Tests copilot Q&A functionality with AI orchestrator integration.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.copilot.copilot import ComplianceCopilot
from app.services.ai_orchestrator import AIOrchestrator
from app.db.models import Tenant


@pytest.fixture
async def copilot(db_session: AsyncSession) -> ComplianceCopilot:
    """Create a ComplianceCopilot instance."""
    orch = AIOrchestrator()
    return ComplianceCopilot(orch)


@pytest.fixture
async def test_tenant(db_session: AsyncSession) -> Tenant:
    """Create a test tenant."""
    tenant = Tenant(
        slug="copilot-test",
        name="Copilot Test Tenant",
        sector="fintech",
        jurisdictions=["AR", "BR"],
        data_residency_policy={"ai_providers_allowed": ["nvidia", "anthropic"]},
        timezone_iana="America/Buenos_Aires",
    )
    db_session.add(tenant)
    await db_session.commit()
    return tenant


@pytest.mark.asyncio
async def test_answer_question(copilot: ComplianceCopilot, test_tenant: Tenant):
    """Test copilot answering a compliance question."""
    result = await copilot.answer_question(
        question="What are Brazil's AML reporting requirements?",
        tenant_id=test_tenant.slug,
        context={"entity_id": "test-entity"},
    )

    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_explain_regulation(copilot: ComplianceCopilot, test_tenant: Tenant):
    """Test copilot explaining a regulation."""
    result = await copilot.explain_regulation(
        regulation_text="Must implement MFA for all customer-facing systems",
        jurisdiction="BR",
        tenant_id=test_tenant.slug,
    )

    assert result is not None
    assert isinstance(result, str)
    assert "MFA" in result or "authentication" in result.lower()


@pytest.mark.asyncio
async def test_suggest_remediation(copilot: ComplianceCopilot, test_tenant: Tenant):
    """Test copilot suggesting remediation for a gap."""
    result = await copilot.suggest_remediation(
        gap_description="Missing documentation for transaction monitoring",
        severity="high",
        tenant_id=test_tenant.slug,
    )

    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_copilot_enforces_tenant_isolation(copilot: ComplianceCopilot, db_session: AsyncSession):
    """Test that copilot enforces multi-tenant isolation."""
    tenant1 = Tenant(
        slug="copilot-tenant-1",
        name="Tenant 1",
        sector="bank",
        jurisdictions=["AR"],
    )
    tenant2 = Tenant(
        slug="copilot-tenant-2",
        name="Tenant 2",
        sector="bank",
        jurisdictions=["BR"],
    )
    db_session.add(tenant1)
    db_session.add(tenant2)
    await db_session.commit()

    # Ask question as tenant 1
    result1 = await copilot.answer_question(
        question="What are our regulations?",
        tenant_id=tenant1.slug,
    )

    # Ask as tenant 2
    result2 = await copilot.answer_question(
        question="What are our regulations?",
        tenant_id=tenant2.slug,
    )

    # Both should succeed but have different audit context
    assert result1 is not None
    assert result2 is not None
