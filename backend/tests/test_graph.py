"""
T5 — Graph Service unit tests.

Tests:
  - get_graph() returns a GraphService singleton (same object on second call)
  - graph_stats SQL executes without error when given a mock async session
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.graph_service import GraphService, get_graph


# ── Singleton ─────────────────────────────────────────────────────────────────


class TestGetGraphSingleton:
    def test_get_graph_returns_graph_service_instance(self):
        """get_graph() must return a GraphService."""
        graph = get_graph()
        assert isinstance(graph, GraphService)

    def test_get_graph_same_object_on_second_call(self):
        """get_graph() must be a singleton — two calls return the same object."""
        g1 = get_graph()
        g2 = get_graph()
        assert g1 is g2, "get_graph() should return the same GraphService instance each time"

    def test_get_graph_consistent_across_multiple_calls(self):
        """Verify identity holds for 3 consecutive calls."""
        g1 = get_graph()
        g2 = get_graph()
        g3 = get_graph()
        assert g1 is g2 is g3


# ── graph_stats with mock session ────────────────────────────────────────────


class TestGraphStats:
    """
    graph_stats() executes two SQL queries and aggregates results.
    We mock AsyncSessionLocal so no real DB connection is needed.
    """

    @pytest.mark.asyncio
    async def test_graph_stats_returns_expected_keys(self):
        """graph_stats should return dict with vertices, edges, total_vertices, total_edges."""

        # Build mock row objects that behave like SQLAlchemy RowProxy
        def _make_rows(pairs: list[tuple]) -> list[MagicMock]:
            rows = []
            for key, count in pairs:
                row = MagicMock()
                row.vertex_type = key
                row.edge_type = key
                row.cnt = count
                rows.append(row)
            return rows

        vertex_rows = _make_rows([("regulation", 5), ("obligation", 12), ("regulator", 3)])
        edge_rows = _make_rows([("REQUIRES", 12), ("ISSUED_BY", 5)])

        # Mock async context manager for AsyncSessionLocal
        mock_session = AsyncMock()

        call_count = 0

        async def fake_execute(stmt, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.__iter__ = MagicMock(return_value=iter(vertex_rows))
            else:
                result.__iter__ = MagicMock(return_value=iter(edge_rows))
            return result

        mock_session.execute = fake_execute

        # AsyncSessionLocal is used as an async context manager
        mock_session_cm = MagicMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.graph_service.AsyncSessionLocal", return_value=mock_session_cm):
            graph = GraphService()
            result = await graph.graph_stats()

        assert "vertices" in result
        assert "edges" in result
        assert "total_vertices" in result
        assert "total_edges" in result

    @pytest.mark.asyncio
    async def test_graph_stats_aggregates_counts_correctly(self):
        """Verify total_vertices and total_edges are sums of the per-type counts."""

        def _make_rows(pairs: list[tuple]) -> list[MagicMock]:
            rows = []
            for key, count in pairs:
                row = MagicMock()
                row.vertex_type = key
                row.edge_type = key
                row.cnt = count
                rows.append(row)
            return rows

        vertex_rows = _make_rows([("regulation", 10), ("obligation", 20)])
        edge_rows = _make_rows([("REQUIRES", 15), ("ISSUED_BY", 10)])

        mock_session = AsyncMock()
        call_count = 0

        async def fake_execute(stmt, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.__iter__ = MagicMock(return_value=iter(vertex_rows))
            else:
                result.__iter__ = MagicMock(return_value=iter(edge_rows))
            return result

        mock_session.execute = fake_execute

        mock_session_cm = MagicMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.graph_service.AsyncSessionLocal", return_value=mock_session_cm):
            graph = GraphService()
            result = await graph.graph_stats()

        assert result["total_vertices"] == 30  # 10 + 20
        assert result["total_edges"] == 25     # 15 + 10

    @pytest.mark.asyncio
    async def test_graph_stats_empty_db_returns_zero_totals(self):
        """When DB has no vertices/edges, totals should be 0."""
        mock_session = AsyncMock()
        call_count = 0

        async def fake_execute(stmt, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            result.__iter__ = MagicMock(return_value=iter([]))
            return result

        mock_session.execute = fake_execute

        mock_session_cm = MagicMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.graph_service.AsyncSessionLocal", return_value=mock_session_cm):
            graph = GraphService()
            result = await graph.graph_stats()

        assert result["total_vertices"] == 0
        assert result["total_edges"] == 0
        assert result["vertices"] == {}
        assert result["edges"] == {}


# ── link_obligation_to_sectors ────────────────────────────────────────────────


class TestLinkObligationToSectors:
    """
    link_obligation_to_sectors() should create sector entity vertices and
    APPLIES_TO edges for each (obligation_code, sector) combination.
    """

    @pytest.mark.asyncio
    async def test_creates_sector_vertex_and_applies_to_edge(self):
        """
        Given one obligation with applies_to_sectors=["PSP"], the method
        must create a sector vertex and one APPLIES_TO edge.
        """
        # Obligation mock with obligation_code and applies_to_sectors
        mock_obl = MagicMock()
        mock_obl.obligation_code = "AR_BCRA_PSP_001"
        mock_obl.applies_to_sectors = ["PSP"]

        # Obligation vertex mock found in DB
        mock_obl_vertex = MagicMock()
        mock_obl_vertex.id = uuid.uuid4()

        # Session mock that returns the obligation vertex on select(GraphVertex)
        mock_session = AsyncMock()
        mock_session_cm = MagicMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=False)

        scalar_result = MagicMock()
        scalar_result.scalar_one_or_none = MagicMock(return_value=mock_obl_vertex)
        mock_session.execute = AsyncMock(return_value=scalar_result)

        graph = GraphService()

        # Stub out upsert_vertex and upsert_edge to avoid real DB calls
        graph.upsert_vertex = AsyncMock(return_value=str(uuid.uuid4()))
        graph.upsert_edge = AsyncMock(return_value=str(uuid.uuid4()))

        with patch("app.services.graph_service.AsyncSessionLocal", return_value=mock_session_cm):
            result = await graph.link_obligation_to_sectors(
                regulation_id="reg-001",
                obligations_data=[
                    {
                        "obligation_code": "AR_BCRA_PSP_001",
                        "applies_to_sectors": ["PSP"],
                    }
                ],
            )

        assert result["sector_vertices"] == 1
        assert result["edges_created"] == 1
        graph.upsert_vertex.assert_awaited_once()
        graph.upsert_edge.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_skips_obligations_without_sectors(self):
        """Obligations with empty applies_to_sectors produce no vertices or edges."""
        graph = GraphService()
        graph.upsert_vertex = AsyncMock()
        graph.upsert_edge = AsyncMock()

        result = await graph.link_obligation_to_sectors(
            regulation_id="reg-002",
            obligations_data=[
                {"obligation_code": "AR_BCRA_001", "applies_to_sectors": []},
                {"obligation_code": "", "applies_to_sectors": ["PSP"]},
            ],
        )

        assert result["sector_vertices"] == 0
        assert result["edges_created"] == 0
        graph.upsert_vertex.assert_not_awaited()
        graph.upsert_edge.assert_not_awaited()


# ── register_entity ───────────────────────────────────────────────────────────


class TestRegisterEntity:
    """
    register_entity() must return a dict with entity_id, vertex_id, and
    obligations_linked.
    """

    @pytest.mark.asyncio
    async def test_returns_expected_keys(self):
        """register_entity returns a dict with entity_id, vertex_id, obligations_linked."""
        fake_entity_id = str(uuid.uuid4())
        fake_vertex_id = str(uuid.uuid4())

        # Mock ComplianceEntity returned by DB (simulates existing row)
        mock_entity = MagicMock()
        mock_entity.id = uuid.UUID(fake_entity_id)
        mock_entity.sectors = ["PSP"]
        mock_entity.properties = {}

        scalar_result = MagicMock()
        scalar_result.scalar_one_or_none = MagicMock(return_value=mock_entity)

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=scalar_result)
        mock_session.commit = AsyncMock()

        mock_session_cm = MagicMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=False)

        graph = GraphService()
        graph.upsert_vertex = AsyncMock(return_value=fake_vertex_id)
        graph._wire_entity_to_obligations = AsyncMock(return_value=3)

        with patch("app.services.graph_service.AsyncSessionLocal", return_value=mock_session_cm):
            result = await graph.register_entity(
                tenant_id="polkorp",
                name="Acme PSP S.A.",
                entity_type="company",
                sectors=["PSP"],
                properties={"country": "AR"},
            )

        assert "entity_id" in result
        assert "vertex_id" in result
        assert "obligations_linked" in result
        assert result["vertex_id"] == fake_vertex_id
        assert result["obligations_linked"] == 3

    @pytest.mark.asyncio
    async def test_entity_id_is_string(self):
        """entity_id in the result must be a non-empty string."""
        fake_entity_id = str(uuid.uuid4())

        mock_entity = MagicMock()
        mock_entity.id = uuid.UUID(fake_entity_id)
        mock_entity.sectors = []
        mock_entity.properties = {}

        scalar_result = MagicMock()
        scalar_result.scalar_one_or_none = MagicMock(return_value=mock_entity)

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=scalar_result)
        mock_session.commit = AsyncMock()

        mock_session_cm = MagicMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=False)

        graph = GraphService()
        graph.upsert_vertex = AsyncMock(return_value=str(uuid.uuid4()))
        graph._wire_entity_to_obligations = AsyncMock(return_value=0)

        with patch("app.services.graph_service.AsyncSessionLocal", return_value=mock_session_cm):
            result = await graph.register_entity(
                tenant_id="polkorp",
                name="Solo Corp",
                entity_type="individual",
                sectors=[],
            )

        assert isinstance(result["entity_id"], str)
        assert len(result["entity_id"]) > 0


# ── _wire_entity_to_obligations ───────────────────────────────────────────────


class TestWireEntityToObligations:
    """
    _wire_entity_to_obligations() with empty sectors list must return 0 without
    touching the DB.
    """

    @pytest.mark.asyncio
    async def test_empty_sectors_returns_zero(self):
        """When sectors=[], no DB queries and 0 edges created."""
        graph = GraphService()
        graph.upsert_edge = AsyncMock()

        result = await graph._wire_entity_to_obligations(
            entity_vertex_id=str(uuid.uuid4()),
            sectors=[],
        )

        assert result == 0
        graph.upsert_edge.assert_not_awaited()
