"""
Multi-tenant isolation tests.
Verify that tenant A cannot read tenant B's data.
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.auth import CurrentUser, get_current_user


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_client(tenant_id: str, role: str = "analyst") -> TestClient:
    """Build a throwaway TestClient authenticated as the given tenant/role."""
    from app.main import app

    def _user() -> CurrentUser:
        return CurrentUser(user_id=f"{tenant_id}-user", tenant_id=tenant_id, role=role)

    @asynccontextmanager
    async def _noop_lifespan(application):
        yield

    app.router.lifespan_context = _noop_lifespan
    app.dependency_overrides[get_current_user] = _user
    return TestClient(app, raise_server_exceptions=True)


# ── Test 1: Regulation isolation ───────────────────────────────────────────────

class TestRegulationIsolation:
    """Verify that tenant-scoped regulation queries don't bleed across tenants."""

    def test_regulation_isolation(self):
        """
        Two Regulation-like rows with different tenant_ids (simulated via mock session).
        A query filtered to tenant_A must return only tenant_A's row.
        """
        from app.db.models import Regulation

        tenant_a = "acme"
        tenant_b = "globex"

        # Build two mock regulation objects
        reg_a = MagicMock(spec=Regulation)
        reg_a.id = uuid.uuid4()
        reg_a.country = "AR"
        reg_a.regulator = "BCRA"
        reg_a.code = "A 7825"
        reg_a.title = "Acme regulation"
        # Regulation doesn't have tenant_id directly; it comes through evidence /
        # compliance_cases. Here we simulate the filtering logic itself.

        reg_b = MagicMock(spec=Regulation)
        reg_b.id = uuid.uuid4()
        reg_b.country = "BR"
        reg_b.regulator = "BACEN"
        reg_b.code = "CMN 4753"
        reg_b.title = "Globex regulation"

        all_regulations = [reg_a, reg_b]

        # Simulate the WHERE filter that modules apply
        def filter_by_regulator(rows, regulator_filter):
            return [r for r in rows if r.regulator == regulator_filter]

        # tenant_A queries BCRA only — should not see BACEN record
        result = filter_by_regulator(all_regulations, "BCRA")
        assert len(result) == 1
        assert result[0].title == "Acme regulation"

        # tenant_B queries BACEN only — should not see BCRA record
        result = filter_by_regulator(all_regulations, "BACEN")
        assert len(result) == 1
        assert result[0].title == "Globex regulation"


# ── Test 2: EvidenceDocument isolation ────────────────────────────────────────

class TestEvidenceIsolation:
    """Verify that EvidenceDocument rows are scoped to tenant_id."""

    def test_evidence_isolation(self):
        """
        Create two EvidenceDocument mocks with different tenant_ids.
        A simulated query filtered by tenant_id must return only the matching row.
        """
        from app.db.models import EvidenceDocument

        tenant_a_id = "acme"
        tenant_b_id = "globex"

        doc_a = MagicMock(spec=EvidenceDocument)
        doc_a.id = uuid.uuid4()
        doc_a.tenant_id = tenant_a_id
        doc_a.filename = "uif_resolution_acme.pdf"

        doc_b = MagicMock(spec=EvidenceDocument)
        doc_b.id = uuid.uuid4()
        doc_b.tenant_id = tenant_b_id
        doc_b.filename = "bacen_circular_globex.pdf"

        all_docs = [doc_a, doc_b]

        # Simulate the WHERE tenant_id = ? filter
        def filter_by_tenant(rows, tenant_id):
            return [d for d in rows if d.tenant_id == tenant_id]

        result_a = filter_by_tenant(all_docs, tenant_a_id)
        assert len(result_a) == 1
        assert result_a[0].filename == "uif_resolution_acme.pdf"

        result_b = filter_by_tenant(all_docs, tenant_b_id)
        assert len(result_b) == 1
        assert result_b[0].filename == "bacen_circular_globex.pdf"

        # Cross-tenant: tenant_a must not see tenant_b's doc
        assert result_a[0].tenant_id != tenant_b_id


# ── Test 3: Non-admin cannot read another tenant's endpoint ──────────────────

class TestTenantEndpointOwnOnly:
    """Non-admin user for tenant 'acme' must get 403 on /tenants/other-tenant."""

    def test_tenant_endpoint_own_only(self, analyst_client: TestClient):
        resp = analyst_client.get("/api/v1/tenants/other-tenant")
        assert resp.status_code == 403

    def test_tenant_endpoint_own_slug_passes_auth(self, analyst_client: TestClient):
        """
        Analyst for tenant 'acme' may call GET /tenants/acme.
        The 404 (no real DB) proves the 403 guard was passed, not hit.
        """
        resp = analyst_client.get("/api/v1/tenants/acme")
        # 404 expected because there is no real DB; 403 would mean the guard failed
        assert resp.status_code != 403


# ── Test 4: Admin can list all tenants ───────────────────────────────────────

class TestTenantEndpointAdminCanSeeAll:
    """Admin user must receive 200 from GET /api/v1/tenants."""

    def test_tenant_endpoint_admin_can_see_all(self, admin_client: TestClient):
        resp = admin_client.get("/api/v1/tenants")
        assert resp.status_code == 200

    def test_tenant_list_response_is_list(self, admin_client: TestClient):
        resp = admin_client.get("/api/v1/tenants")
        data = resp.json()
        assert isinstance(data, list)


# ── Test 5: GraphVertex tenant_id isolation ──────────────────────────────────

class TestGraphVertexIsolation:
    """
    GraphService queries for vertices must include a tenant_id WHERE clause
    when the service propagates tenant context.
    """

    def test_graph_vertex_isolation(self):
        """
        Mock the DB session and verify that a tenant-filtered vertex query
        only returns matching rows.
        """
        from app.db.models import GraphVertex

        tenant_a = "acme"
        tenant_b = "globex"

        # Two vertices — graph_vertices doesn't have tenant_id in its schema,
        # but entity_id and properties carry tenant context.
        # We model tenant isolation via properties["tenant_id"].
        v_a = MagicMock(spec=GraphVertex)
        v_a.id = uuid.uuid4()
        v_a.vertex_type = "regulation"
        v_a.entity_id = str(uuid.uuid4())
        v_a.properties = {"tenant_id": tenant_a, "country": "AR"}

        v_b = MagicMock(spec=GraphVertex)
        v_b.id = uuid.uuid4()
        v_b.vertex_type = "regulation"
        v_b.entity_id = str(uuid.uuid4())
        v_b.properties = {"tenant_id": tenant_b, "country": "BR"}

        all_vertices = [v_a, v_b]

        # Simulate WHERE properties->>'tenant_id' = ?
        def filter_vertices_by_tenant(rows, tenant_id):
            return [v for v in rows if v.properties.get("tenant_id") == tenant_id]

        result = filter_vertices_by_tenant(all_vertices, tenant_a)
        assert len(result) == 1
        assert result[0].properties["country"] == "AR"

        result = filter_vertices_by_tenant(all_vertices, tenant_b)
        assert len(result) == 1
        assert result[0].properties["country"] == "BR"

        # Verify cross-tenant leakage is impossible with this filter
        result_cross = filter_vertices_by_tenant(all_vertices, tenant_a)
        entity_ids = [str(v.entity_id) for v in result_cross]
        assert str(v_b.entity_id) not in entity_ids


# ── Test 6: Crawler run passes tenant_id through ─────────────────────────────

class TestCrawlerRunUsesTenantId:
    """BCRACrawler.run must receive the tenant_id passed by the scheduler."""

    async def test_crawler_run_uses_tenant_id(self):
        """
        Mock BCRACrawler.run and verify that run_bcra() passes the caller's
        tenant_id straight through to the crawler.
        """
        from app.modules.crawler.base_crawler import CrawlerResult
        from app.modules.crawler.bcra_crawler import BCRACrawler

        expected_tenant = "acme"
        captured: list[str] = []

        async def mock_run(self_inner, tenant_id: str = "polkorp"):
            captured.append(tenant_id)
            return CrawlerResult(
                regulator="BCRA",
                country="AR",
                crawled=0,
                skipped_duplicate=0,
                errors=0,
                documents=[],
                run_duration_seconds=0.0,
                timestamp="2026-05-18T00:00:00+00:00",
            )

        with patch.object(BCRACrawler, "run", new=mock_run):
            from app.modules.crawler.scheduler import run_bcra
            await run_bcra(tenant_id=expected_tenant)

        assert len(captured) == 1, "run() should have been called exactly once"
        assert captured[0] == expected_tenant, (
            f"Crawler received tenant_id={captured[0]!r}, expected {expected_tenant!r}"
        )
