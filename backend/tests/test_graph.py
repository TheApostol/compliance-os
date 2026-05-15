"""
T5 — Graph Service unit tests.

Tests:
  - get_graph() returns a GraphService singleton (same object on second call)
  - graph_stats SQL executes without error when given a mock async session
"""

from __future__ import annotations

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
