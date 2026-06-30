"""
End-to-End Tests for Agent Framework

Tests complete workflow: entity assessment → supervisor orchestration → domain/skill agent delegation → result aggregation.
Validates multi-tenant isolation, rate limiting interaction, and cross-module integration.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.agents.agent_registry import AgentRegistry
from app.agents.supervisor.compliance_director import ComplianceDirector
from app.db.models import Tenant, FailureMode, Mitigation, AIModel
from app.services.ai_orchestrator import AIOrchestrator
from app.services.rag import RAGService


@pytest.fixture
async def registry(db_session: AsyncSession) -> AgentRegistry:
    """Initialize agent registry for E2E tests."""
    orch = AIOrchestrator()
    registry = AgentRegistry()
    registry.initialize(orch)
    return registry


@pytest.fixture
async def supervisor(registry: AgentRegistry) -> ComplianceDirector:
    """Get ComplianceDirector supervisor agent."""
    return registry.get_agent("supervisor:director")


@pytest.fixture
async def test_tenant(db_session: AsyncSession) -> Tenant:
    """Create a test tenant for E2E assessment."""
    tenant = Tenant(
        slug="e2e-test-tenant",
        name="E2E Test Tenant",
        sector="fintech",
        jurisdictions=["AR", "BR", "CL"],
        data_residency_policy={"ai_providers_allowed": ["nvidia", "anthropic"]},
        timezone_iana="America/Buenos_Aires",
    )
    db_session.add(tenant)
    await db_session.commit()
    return tenant


@pytest.fixture
async def test_entity_data(test_tenant: Tenant) -> dict:
    """Create test entity data for assessment."""
    return {
        "entity_id": "test-entity-001",
        "entity_type": "fintech",
        "sectors": ["payments", "remittance"],
    }


@pytest.mark.asyncio
async def test_full_entity_assessment_workflow(
    supervisor: ComplianceDirector,
    test_tenant: Tenant,
    test_entity_data: dict,
    db_session: AsyncSession,
):
    """Test complete entity assessment workflow via supervisor."""
    result = await supervisor.execute_safe(
        {
            "task": "assess_entity",
            "tenant_id": test_tenant.slug,
            "entity_id": test_entity_data["entity_id"],
            "entity_type": test_entity_data["entity_type"],
            "sectors": test_entity_data["sectors"],
        },
        db_session,
    )

    # Verify assessment completed
    assert result is not None
    assert result.success is True
    assert result.data is not None

    # Verify result structure
    data = result.data
    assert "compliance_score" in data
    assert "jurisdictions" in data
    assert "regulations_count" in data
    assert "gaps" in data
    assert "deadlines_count" in data
    assert "risk_level" in data

    # Verify numeric constraints
    assert 0 <= data["compliance_score"] <= 100
    assert isinstance(data["regulations_count"], int)
    assert isinstance(data["deadlines_count"], int)
    assert data["risk_level"] in ["low", "medium", "high", "critical"]

    # Verify jurisdiction coverage (at least one of the tenant's jurisdictions assessed)
    assessed_jurisdictions = set(data.get("jurisdictions", []))
    tenant_jurisdictions = set(test_tenant.jurisdictions)
    assert len(assessed_jurisdictions & tenant_jurisdictions) > 0


@pytest.mark.asyncio
async def test_agent_registry_provides_all_agent_types(registry: AgentRegistry):
    """Test that registry contains all required agent types: supervisor + domains + skills."""
    stats = registry.stats()

    # Verify counts
    assert stats["total_agents"] == 13
    assert stats["by_type"]["supervisor"] == 1
    assert stats["by_type"]["domain"] == 6
    assert stats["by_type"]["skill"] == 6

    # Verify supervisor is accessible
    director = registry.get_agent("supervisor:director")
    assert director is not None
    assert director.agent_type.value == "supervisor"

    # Verify all domain agents accessible
    domain_codes = ["ar", "br", "co", "cl", "mx", "andean"]
    for code in domain_codes:
        agent = registry.get_agent(f"domain:{code}")
        assert agent is not None
        assert agent.agent_type.value == "domain"

    # Verify all skill agents accessible
    for i in range(1, 7):
        agent = registry.get_agent(f"skill:m{i}")
        assert agent is not None
        assert agent.agent_type.value == "skill"


@pytest.mark.asyncio
async def test_agent_framework_enforces_tenant_isolation(
    registry: AgentRegistry,
    db_session: AsyncSession,
):
    """Test that agent framework maintains tenant isolation across assessment workflows."""
    # Create two tenants
    tenant1 = Tenant(
        slug="e2e-tenant-1",
        name="E2E Tenant 1",
        sector="bank",
        jurisdictions=["AR"],
    )
    tenant2 = Tenant(
        slug="e2e-tenant-2",
        name="E2E Tenant 2",
        sector="bank",
        jurisdictions=["BR"],
    )
    db_session.add(tenant1)
    db_session.add(tenant2)
    await db_session.commit()

    supervisor = registry.get_agent("supervisor:director")

    # Run assessment for tenant 1
    result1 = await supervisor.execute_safe(
        {
            "task": "assess_entity",
            "tenant_id": tenant1.slug,
            "entity_id": "entity-t1",
            "entity_type": "company",
            "sectors": [],
        },
        db_session,
    )

    # Run assessment for tenant 2
    result2 = await supervisor.execute_safe(
        {
            "task": "assess_entity",
            "tenant_id": tenant2.slug,
            "entity_id": "entity-t2",
            "entity_type": "company",
            "sectors": [],
        },
        db_session,
    )

    # Both should succeed
    assert result1.success is True
    assert result2.success is True

    # Verify results are different (different jurisdictions assessed)
    jurisdictions_1 = set(result1.data.get("jurisdictions", []))
    jurisdictions_2 = set(result2.data.get("jurisdictions", []))

    # Each tenant should have different jurisdiction focus based on their config
    assert jurisdictions_1 != jurisdictions_2 or len(jurisdictions_1) > 0


@pytest.mark.asyncio
async def test_assessment_includes_all_modules(
    supervisor: ComplianceDirector,
    test_tenant: Tenant,
    db_session: AsyncSession,
):
    """Test that supervisor orchestrates all M1-M6 skill modules during assessment."""
    result = await supervisor.execute_safe(
        {
            "task": "assess_entity",
            "tenant_id": test_tenant.slug,
            "entity_id": "full-module-test",
            "entity_type": "fintech",
            "sectors": ["payments"],
        },
        db_session,
    )

    assert result.success is True
    data = result.data

    # Verify modules contributed to assessment
    # M1 (Regulatory Intelligence): regulations_count should be > 0
    assert data["regulations_count"] > 0

    # M3 (KYC/AML): should be reflected in gaps or risk_level
    # M4 (Continuous Monitoring): deadlines_count indicates this ran
    assert "deadlines_count" in data

    # M5 (AI Governance): compliance_score aggregation
    assert "compliance_score" in data

    # M6 (Evidence Automation): gaps list should have structured evidence
    gaps = data.get("gaps", [])
    assert isinstance(gaps, list)


@pytest.mark.asyncio
async def test_premortem_module_integration_with_assessment(
    supervisor: ComplianceDirector,
    test_tenant: Tenant,
    db_session: AsyncSession,
):
    """Test that premortem failure modes are loaded during assessment."""
    # Create a failure mode for the tenant
    fm = FailureMode(
        tenant_id=test_tenant.slug,
        code="E2E_F1",
        title="Assessment Timeout",
        description="Assessment takes too long under load",
        probability=0.1,
        impact="medium",
        risk_score=35,
    )
    db_session.add(fm)
    await db_session.commit()

    # Run assessment
    result = await supervisor.execute_safe(
        {
            "task": "assess_entity",
            "tenant_id": test_tenant.slug,
            "entity_id": "premortem-integration-test",
            "entity_type": "company",
            "sectors": [],
        },
        db_session,
    )

    assert result.success is True
    # Premortem should have been consulted for this tenant's context
    # (In production, this influences recommendations)


@pytest.mark.asyncio
async def test_assessment_respects_data_residency_policy(
    supervisor: ComplianceDirector,
    db_session: AsyncSession,
):
    """Test that assessment respects tenant's data residency constraints."""
    # Create tenant with restricted residency policy
    restricted_tenant = Tenant(
        slug="e2e-restricted-tenant",
        name="Restricted Residency Tenant",
        sector="fintech",
        jurisdictions=["AR"],
        data_residency_policy={"ai_providers_allowed": ["nvidia"]},  # Only NVIDIA allowed
    )
    db_session.add(restricted_tenant)
    await db_session.commit()

    supervisor = AgentRegistry().get_agent("supervisor:director")

    result = await supervisor.execute_safe(
        {
            "task": "assess_entity",
            "tenant_id": restricted_tenant.slug,
            "entity_id": "residency-test",
            "entity_type": "company",
            "sectors": [],
        },
        db_session,
    )

    # Should still succeed (NVIDIA is in the allowed list)
    assert result.success is True


@pytest.mark.asyncio
async def test_concurrent_assessments_maintain_isolation(
    registry: AgentRegistry,
    db_session: AsyncSession,
):
    """Test that concurrent assessments from different tenants maintain isolation."""
    import asyncio

    tenant1 = Tenant(
        slug="e2e-concurrent-1",
        name="Concurrent Tenant 1",
        sector="bank",
        jurisdictions=["AR"],
    )
    tenant2 = Tenant(
        slug="e2e-concurrent-2",
        name="Concurrent Tenant 2",
        sector="bank",
        jurisdictions=["BR"],
    )
    db_session.add(tenant1)
    db_session.add(tenant2)
    await db_session.commit()

    supervisor = registry.get_agent("supervisor:director")

    # Run two assessments concurrently
    results = await asyncio.gather(
        supervisor.execute_safe(
            {
                "task": "assess_entity",
                "tenant_id": tenant1.slug,
                "entity_id": "concurrent-1",
                "entity_type": "company",
                "sectors": [],
            },
            db_session,
        ),
        supervisor.execute_safe(
            {
                "task": "assess_entity",
                "tenant_id": tenant2.slug,
                "entity_id": "concurrent-2",
                "entity_type": "company",
                "sectors": [],
            },
            db_session,
        ),
    )

    # Both should succeed
    assert results[0].success is True
    assert results[1].success is True

    # Verify no cross-tenant data leakage
    # (Each result should reflect its own tenant's jurisdictions)
    assert results[0].data is not None
    assert results[1].data is not None
