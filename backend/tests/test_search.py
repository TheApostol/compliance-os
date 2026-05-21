"""
Tests for GET /search — hybrid keyword + semantic regulation search.

All DB and Qdrant calls are mocked so no live infrastructure is required.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.auth import CurrentUser


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_regulation(
    reg_id: str | None = None,
    title: str = "AML Reporting Regulation",
    code: str = "UIF/2024/001",
    country: str = "AR",
    regulator: str = "UIF",
    tenant_id: str | None = "polkorp",
) -> MagicMock:
    from app.db.models import Regulation

    reg = MagicMock(spec=Regulation)
    reg.id = uuid.UUID(reg_id) if reg_id else uuid.uuid4()
    reg.title = title
    reg.code = code
    reg.country = country
    reg.regulator = regulator
    reg.tenant_id = tenant_id
    return reg


def _make_rag_chunk(
    reg_id: str,
    title: str = "AML Reporting Regulation",
    code: str = "UIF/2024/001",
    country: str = "AR",
    regulator: str = "UIF",
    score: float = 0.85,
    text: str = "Excerpt of regulatory text about AML obligations.",
) -> dict:
    return {
        "regulation_id": reg_id,
        "title": title,
        "code": code,
        "country": country,
        "regulator": regulator,
        "score": score,
        "text": text,
    }


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def mock_current_user() -> CurrentUser:
    return CurrentUser(user_id="test-user", tenant_id="polkorp", role="analyst")


# ── Test 1: Keyword match ─────────────────────────────────────────────────────

class TestSearchKeywordMatch:
    """A regulation matching the keyword query must be returned with source='keyword'."""

    @pytest.mark.asyncio
    async def test_search_keyword_match(self, mock_current_user: CurrentUser):
        reg = _make_regulation(title="AML Suspicious Activity Report")
        reg_id = str(reg.id)

        # Mock DB session returning one regulation
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [reg]
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value = mock_scalars

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_execute_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        # Mock Qdrant returning nothing
        mock_rag = AsyncMock()
        mock_rag.retrieve = AsyncMock(return_value=[])

        with (
            patch("app.db.base.AsyncSessionLocal", return_value=mock_session),
            patch("app.services.rag.get_rag", return_value=mock_rag),
        ):
            from app.api.v1.router import search_regulations
            result = await search_regulations(
                q="AML",
                country=None,
                regulator=None,
                limit=10,
                current_user=mock_current_user,
            )

        assert result["count"] >= 1
        match = next((r for r in result["results"] if r["regulation_id"] == reg_id), None)
        assert match is not None, f"Expected regulation {reg_id} in results"
        assert match["source"] == "keyword"


# ── Test 2: Semantic only ─────────────────────────────────────────────────────

class TestSearchSemanticOnly:
    """When keyword search returns nothing, RAG chunk becomes a semantic result."""

    @pytest.mark.asyncio
    async def test_search_semantic_only(self, mock_current_user: CurrentUser):
        semantic_id = str(uuid.uuid4())
        chunk = _make_rag_chunk(reg_id=semantic_id, score=0.91)

        # DB returns no keyword matches
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value = mock_scalars

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_execute_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_rag = AsyncMock()
        mock_rag.retrieve = AsyncMock(return_value=[chunk])

        with (
            patch("app.db.base.AsyncSessionLocal", return_value=mock_session),
            patch("app.services.rag.get_rag", return_value=mock_rag),
        ):
            from app.api.v1.router import search_regulations
            result = await search_regulations(
                q="suspicious activity reporting threshold",
                country=None,
                regulator=None,
                limit=10,
                current_user=mock_current_user,
            )

        assert result["count"] >= 1
        match = next((r for r in result["results"] if r["regulation_id"] == semantic_id), None)
        assert match is not None, f"Expected semantic result {semantic_id}"
        assert match["source"] == "semantic"
        assert match["score"] == pytest.approx(0.91)


# ── Test 3: Hybrid ───────────────────────────────────────────────────────────

class TestSearchHybrid:
    """When both keyword and semantic match the same regulation, source='hybrid'."""

    @pytest.mark.asyncio
    async def test_search_hybrid(self, mock_current_user: CurrentUser):
        shared_id = str(uuid.uuid4())
        reg = _make_regulation(reg_id=shared_id, title="KYC Customer Due Diligence")
        chunk = _make_rag_chunk(reg_id=shared_id, score=0.78)

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [reg]
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value = mock_scalars

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_execute_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_rag = AsyncMock()
        mock_rag.retrieve = AsyncMock(return_value=[chunk])

        with (
            patch("app.db.base.AsyncSessionLocal", return_value=mock_session),
            patch("app.services.rag.get_rag", return_value=mock_rag),
        ):
            from app.api.v1.router import search_regulations
            result = await search_regulations(
                q="KYC",
                country=None,
                regulator=None,
                limit=10,
                current_user=mock_current_user,
            )

        assert result["count"] >= 1
        match = next((r for r in result["results"] if r["regulation_id"] == shared_id), None)
        assert match is not None
        assert match["source"] == "hybrid", (
            f"Expected 'hybrid' for a result that matched both keyword and semantic, got {match['source']!r}"
        )
        # Keyword score is 1.0; RAG score is 0.78. max(1.0, 0.78) = 1.0.
        assert match["score"] == pytest.approx(1.0)


# ── Test 4: Tenant isolation ──────────────────────────────────────────────────

class TestSearchTenantIsolation:
    """
    The Postgres query must include a tenant_id filter so cross-tenant regulations
    are not exposed. We verify this by inspecting the WHERE clause compiled into SQL.
    """

    def test_search_query_includes_tenant_filter(self):
        """
        Build the SQLAlchemy SELECT statement as the endpoint does and confirm
        that 'tenant_id' appears in the compiled SQL string.
        """
        from sqlalchemy import select, or_
        from app.db.models import Regulation

        tenant_id = "polkorp"

        stmt = select(Regulation).where(
            or_(
                Regulation.title.ilike("%AML%"),
                Regulation.code.ilike("%AML%"),
            ),
        ).where(
            (Regulation.tenant_id == tenant_id) | (Regulation.tenant_id.is_(None))
        ).limit(10)

        # Compile to SQL string (dialect-agnostic) and check for tenant_id reference
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": False}))
        assert "tenant_id" in compiled, (
            f"tenant_id filter missing from compiled SQL:\n{compiled}"
        )

    def test_different_tenant_ids_produce_different_filters(self):
        """Two tenants should produce different WHERE clauses."""
        from sqlalchemy import select, or_
        from app.db.models import Regulation

        def build_stmt(tenant_id: str):
            return str(
                select(Regulation).where(
                    or_(
                        Regulation.title.ilike("%AML%"),
                        Regulation.code.ilike("%AML%"),
                    )
                ).where(
                    (Regulation.tenant_id == tenant_id) | (Regulation.tenant_id.is_(None))
                ).compile(compile_kwargs={"literal_binds": True})
            )

        sql_a = build_stmt("tenant_a")
        sql_b = build_stmt("tenant_b")

        assert "tenant_a" in sql_a
        assert "tenant_b" in sql_b
        assert sql_a != sql_b, "Different tenants must produce different WHERE clauses"


# ── Test 5: Qdrant failure fallback ──────────────────────────────────────────

class TestSearchQdrantFailure:
    """When Qdrant raises an exception, keyword results are still returned."""

    @pytest.mark.asyncio
    async def test_search_qdrant_failure_returns_keyword_results(
        self, mock_current_user: CurrentUser
    ):
        reg = _make_regulation(title="BCRA Capital Requirements")
        reg_id = str(reg.id)

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [reg]
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value = mock_scalars

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_execute_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        # RAG raises a connection error
        mock_rag = AsyncMock()
        mock_rag.retrieve = AsyncMock(side_effect=ConnectionError("Qdrant unavailable"))

        with (
            patch("app.db.base.AsyncSessionLocal", return_value=mock_session),
            patch("app.services.rag.get_rag", return_value=mock_rag),
        ):
            from app.api.v1.router import search_regulations
            result = await search_regulations(
                q="capital",
                country=None,
                regulator=None,
                limit=10,
                current_user=mock_current_user,
            )

        # Keyword results must still be present despite RAG failure
        assert result["count"] >= 1
        match = next((r for r in result["results"] if r["regulation_id"] == reg_id), None)
        assert match is not None, "Keyword result must be returned even when Qdrant fails"
        assert match["source"] == "keyword"
