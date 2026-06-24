"""
T4 — RAG Service unit tests.

Tests:
  - _chunk_text: produces chunks ≤ CHUNK_SIZE + overhead, all ≥ 50 chars, overlaps work
  - context_for_query: empty retrieve → ""
  - context_for_query: 2 chunks returned → output contains "[1]" and "[2]"
  - _collection_name: per-tenant naming + tenant-less "_global" collection (T0.2)
  - index_all_regulations: indexes each row under its own tenant_id, not the caller's (T0.2)

All Qdrant / embedding I/O is mocked.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.rag import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    COLLECTION,
    RAGService,
    _chunk_text,
    _collection_name,
)


# ── _chunk_text ───────────────────────────────────────────────────────────────


class TestChunkText:
    def test_short_text_returns_single_chunk(self):
        text = "A" * 100  # well under CHUNK_SIZE
        chunks = _chunk_text(text)
        assert len(chunks) == 1
        assert chunks[0] == "A" * 100

    def test_empty_text_returns_empty_list(self):
        chunks = _chunk_text("")
        assert chunks == []

    def test_very_short_text_filtered_out(self):
        """Text shorter than 51 chars is filtered by the ≥50 guard."""
        chunks = _chunk_text("A" * 40)
        assert chunks == []

    def test_51_chars_is_kept(self):
        """Filter is len > 50 (strictly), so 51 chars must survive."""
        chunks = _chunk_text("B" * 51)
        assert len(chunks) == 1

    def test_long_text_produces_multiple_chunks(self):
        text = "X" * (CHUNK_SIZE * 3)
        chunks = _chunk_text(text)
        assert len(chunks) > 1

    def test_all_chunks_at_most_chunk_size_plus_overhead(self):
        text = "W" * (CHUNK_SIZE * 5)
        chunks = _chunk_text(text)
        for c in chunks:
            # strip() is called on each chunk; the chunk itself should be ≤ CHUNK_SIZE
            assert len(c) <= CHUNK_SIZE, f"Chunk length {len(c)} exceeds CHUNK_SIZE {CHUNK_SIZE}"

    def test_all_chunks_more_than_50_chars(self):
        """Filter keeps only chunks with len > 50 (strictly greater)."""
        text = "Z" * (CHUNK_SIZE * 4)
        chunks = _chunk_text(text)
        for c in chunks:
            assert len(c) > 50, f"Chunk too short: {len(c)}"

    def test_overlap_means_content_repeated(self):
        """
        Adjacent chunks should share CHUNK_OVERLAP characters (or close to it)
        when the text is uniform and long enough.
        """
        # Use a cycling pattern so we can verify overlap
        pattern = "abcdefghij"  # 10 chars
        reps = (CHUNK_SIZE * 3) // len(pattern) + 1
        text = (pattern * reps)[: CHUNK_SIZE * 3]
        chunks = _chunk_text(text)
        assert len(chunks) >= 2
        # The tail of chunk[0] should appear at the start of chunk[1]
        tail = chunks[0][-(CHUNK_OVERLAP):]
        head = chunks[1][: CHUNK_OVERLAP]
        assert tail == head, (
            f"Expected overlap of {CHUNK_OVERLAP} chars; "
            f"tail={tail!r}, head={head!r}"
        )

    def test_whitespace_stripped_from_chunks(self):
        # Insert leading/trailing spaces that strip() should remove
        text = "  " + "A" * CHUNK_SIZE + "  "
        chunks = _chunk_text(text)
        for c in chunks:
            assert c == c.strip()

    def test_realistic_regulatory_text(self):
        """Simulate a realistic multi-paragraph regulatory document."""
        paragraph = (
            "Los sujetos obligados deberán reportar operaciones sospechosas "
            "a la Unidad de Información Financiera dentro de las 48 horas "
            "de haber tomado conocimiento de la misma. "
        )
        text = paragraph * 20  # ~2400 chars
        chunks = _chunk_text(text)
        assert len(chunks) >= 1
        for c in chunks:
            assert 50 < len(c) <= CHUNK_SIZE


# ── context_for_query ─────────────────────────────────────────────────────────


class TestContextForQuery:
    """Tests for RAGService.context_for_query — Qdrant calls are fully mocked."""

    def _make_service(self) -> RAGService:
        """Return a RAGService instance with a mock orchestrator pre-wired."""
        svc = RAGService()
        return svc

    @pytest.mark.asyncio
    async def test_empty_retrieve_returns_empty_string(self):
        svc = self._make_service()

        with patch.object(svc, "retrieve", new=AsyncMock(return_value=[])):
            result = await svc.context_for_query(
                question="What are the AML requirements?",
                tenant_id="polkorp",
            )

        assert result == ""

    @pytest.mark.asyncio
    async def test_two_chunks_returns_numbered_references(self):
        svc = self._make_service()

        fake_chunks = [
            {
                "score": 0.92,
                "text": "The entity must report suspicious transactions within 48 hours.",
                "regulator": "UIF",
                "code": "Res. 30/2017",
                "country": "AR",
                "title": "AML Reporting Requirements",
            },
            {
                "score": 0.85,
                "text": "Customer due diligence must be performed before onboarding.",
                "regulator": "BCRA",
                "code": "Com. A 7825",
                "country": "AR",
                "title": "KYC Obligations",
            },
        ]

        with patch.object(svc, "retrieve", new=AsyncMock(return_value=fake_chunks)):
            result = await svc.context_for_query(
                question="What are the AML requirements?",
                tenant_id="polkorp",
            )

        assert "[1]" in result, "Expected numbered reference [1] in context output"
        assert "[2]" in result, "Expected numbered reference [2] in context output"

    @pytest.mark.asyncio
    async def test_context_contains_chunk_text(self):
        svc = self._make_service()

        fake_chunks = [
            {
                "score": 0.90,
                "text": "Suspicious transaction threshold is USD 10,000.",
                "regulator": "UIF",
                "code": "Res. 30/2017",
                "country": "AR",
                "title": "AML",
            },
        ]

        with patch.object(svc, "retrieve", new=AsyncMock(return_value=fake_chunks)):
            result = await svc.context_for_query(
                question="What is the threshold?",
                tenant_id="polkorp",
            )

        assert "Suspicious transaction threshold" in result

    @pytest.mark.asyncio
    async def test_context_contains_regulator_info(self):
        svc = self._make_service()

        fake_chunks = [
            {
                "score": 0.88,
                "text": "Annual report required.",
                "regulator": "BCRA",
                "code": "Com. A 1234",
                "country": "AR",
                "title": "Reporting",
            },
        ]

        with patch.object(svc, "retrieve", new=AsyncMock(return_value=fake_chunks)):
            result = await svc.context_for_query(
                question="What reports are required?",
                tenant_id="polkorp",
            )

        assert "BCRA" in result
        assert "AR" in result

    @pytest.mark.asyncio
    async def test_single_chunk_has_reference_1(self):
        svc = self._make_service()

        fake_chunks = [
            {
                "score": 0.80,
                "text": "Single obligation text here.",
                "regulator": "SBS",
                "code": "Res. 100",
                "country": "PE",
                "title": "Obligations",
            },
        ]

        with patch.object(svc, "retrieve", new=AsyncMock(return_value=fake_chunks)):
            result = await svc.context_for_query(
                question="Any question",
                tenant_id="polkorp",
            )

        assert "[1]" in result
        assert "[2]" not in result


# ── _collection_name (T0.2 — per-tenant Qdrant namespacing) ───────────────────


class TestCollectionName:
    def test_tenant_id_produces_suffixed_collection(self):
        assert _collection_name("polkorp") == f"{COLLECTION}_polkorp"

    def test_none_tenant_id_produces_global_collection(self):
        assert _collection_name(None) == f"{COLLECTION}_global"

    def test_non_alphanumeric_chars_are_sanitized(self):
        assert _collection_name("acme-corp.test") == f"{COLLECTION}_acme_corp_test"

    def test_different_tenants_produce_different_collections(self):
        assert _collection_name("polkorp") != _collection_name("acme")


# ── index_all_regulations (T0.2 — each row indexed under its own tenant_id) ───


def _make_regulation(tenant_id: str | None, code: str = "UIF/2024/001") -> MagicMock:
    from app.db.models import Regulation

    reg = MagicMock(spec=Regulation)
    reg.id = uuid.uuid4()
    reg.tenant_id = tenant_id
    reg.code = code
    reg.country = "AR"
    reg.regulator = "UIF"
    reg.title = "AML Reporting Regulation"
    reg.full_text = "Some regulatory text long enough to be indexed."
    return reg


class TestIndexAllRegulations:
    """index_all_regulations must route each row to ITS OWN tenant_id, not the
    caller-supplied outer tenant_id — this was the latent bug T0.2 fixed."""

    @pytest.mark.asyncio
    async def test_each_row_indexed_under_its_own_tenant_id(self):
        svc = RAGService()
        owned_reg = _make_regulation(tenant_id="acme", code="ACME/001")
        global_reg = _make_regulation(tenant_id=None, code="GLOBAL/001")

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [owned_reg, global_reg]
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value = mock_scalars

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_execute_result)
        mock_session.commit = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("app.db.base.AsyncSessionLocal", return_value=mock_session),
            patch.object(svc, "index_regulation", new=AsyncMock(return_value=1)) as mock_index,
        ):
            # outer tenant_id is deliberately different from either row's real
            # tenant_id, to prove rows aren't re-indexed under the caller's tenant.
            await svc.index_all_regulations(tenant_id="some-other-caller")

        called_tenant_ids = [call.kwargs["tenant_id"] for call in mock_index.call_args_list]
        assert called_tenant_ids == ["acme", None]
