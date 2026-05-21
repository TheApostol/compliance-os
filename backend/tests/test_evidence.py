"""
T3 — Evidence Engine unit tests.

Tests pure / side-effect-free functions that need no DB or AI:
  - _extract_text_pymupdf: real tiny PDF → (str, int)
  - _compute_custody_hash: deterministic
  - scanned PDF branch: prompt contains "[SCANNED PDF" when char_count < 50
"""

from __future__ import annotations

import hashlib
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.evidence.engine import (
    _compute_custody_hash,
    _extract_text_pymupdf,
    EvidenceEngine,
)


# ── _extract_text_pymupdf ─────────────────────────────────────────────────────


fitz = pytest.importorskip("fitz", reason="PyMuPDF (fitz) not installed — skipping PDF tests")


def _make_minimal_pdf_bytes() -> bytes:
    """Build a minimal 1-page PDF in memory with known text using fitz."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4
    page.insert_text((72, 100), "Hello ComplianceOS regulatory text")
    buf = doc.tobytes()
    doc.close()
    return bytes(buf)


class TestExtractTextPymupdf:
    def test_returns_tuple_of_str_and_int(self):
        pdf_bytes = _make_minimal_pdf_bytes()
        text, char_count = _extract_text_pymupdf(pdf_bytes)
        assert isinstance(text, str)
        assert isinstance(char_count, int)

    def test_text_is_non_empty_for_valid_pdf(self):
        pdf_bytes = _make_minimal_pdf_bytes()
        text, char_count = _extract_text_pymupdf(pdf_bytes)
        assert len(text) > 0
        assert char_count > 0

    def test_char_count_matches_text_length(self):
        pdf_bytes = _make_minimal_pdf_bytes()
        text, char_count = _extract_text_pymupdf(pdf_bytes)
        assert char_count == len(text)

    def test_known_text_appears_in_extraction(self):
        pdf_bytes = _make_minimal_pdf_bytes()
        text, _ = _extract_text_pymupdf(pdf_bytes)
        assert "ComplianceOS" in text or "Hello" in text

    def test_invalid_bytes_returns_error_string(self):
        garbage = b"this is definitely not a valid PDF"
        text, char_count = _extract_text_pymupdf(garbage)
        # Should return a fallback error string, not raise
        assert isinstance(text, str)
        assert char_count == 0

    def test_empty_bytes_returns_error_string(self):
        text, char_count = _extract_text_pymupdf(b"")
        assert isinstance(text, str)
        assert char_count == 0


# ── _compute_custody_hash ─────────────────────────────────────────────────────


class TestComputeCustodyHash:
    def test_returns_sha256_hex_string(self):
        h = _compute_custody_hash("abc123", {"key": "value"}, "2026-01-01T00:00:00+00:00")
        assert isinstance(h, str)
        assert len(h) == 64  # sha256 → 64 hex chars
        assert all(c in "0123456789abcdef" for c in h)

    def test_deterministic_same_inputs(self):
        source_hash = "deadbeef" * 8
        structured = {"document_type": "circular", "confidence": 90}
        timestamp = "2026-01-01T00:00:00+00:00"

        h1 = _compute_custody_hash(source_hash, structured, timestamp)
        h2 = _compute_custody_hash(source_hash, structured, timestamp)
        assert h1 == h2

    def test_different_source_hash_produces_different_result(self):
        structured = {"key": "value"}
        ts = "2026-01-01T00:00:00+00:00"
        h1 = _compute_custody_hash("hash_a", structured, ts)
        h2 = _compute_custody_hash("hash_b", structured, ts)
        assert h1 != h2

    def test_different_structured_data_produces_different_result(self):
        source = "abc123"
        ts = "2026-01-01T00:00:00+00:00"
        h1 = _compute_custody_hash(source, {"doc": "A"}, ts)
        h2 = _compute_custody_hash(source, {"doc": "B"}, ts)
        assert h1 != h2

    def test_different_timestamp_produces_different_result(self):
        source = "abc123"
        structured = {"key": "value"}
        h1 = _compute_custody_hash(source, structured, "2026-01-01T00:00:00+00:00")
        h2 = _compute_custody_hash(source, structured, "2026-06-01T12:00:00+00:00")
        assert h1 != h2

    def test_key_order_does_not_matter(self):
        """sort_keys=True means {"a":1,"b":2} == {"b":2,"a":1}."""
        source = "abc"
        ts = "2026-01-01T00:00:00+00:00"
        h1 = _compute_custody_hash(source, {"a": 1, "b": 2}, ts)
        h2 = _compute_custody_hash(source, {"b": 2, "a": 1}, ts)
        assert h1 == h2

    def test_manual_verification(self):
        """Verify the hash matches a manually computed value."""
        source_hash = "aabbcc"
        structured_data = {"x": 1}
        timestamp = "2026-01-01T00:00:00+00:00"

        canonical = json.dumps(structured_data, sort_keys=True, separators=(",", ":"))
        payload = f"{source_hash}:{canonical}:{timestamp}"
        expected = hashlib.sha256(payload.encode()).hexdigest()

        result = _compute_custody_hash(source_hash, structured_data, timestamp)
        assert result == expected


# ── Scanned PDF branch ────────────────────────────────────────────────────────


class TestScannedPdfBranch:
    """
    When char_count < 50, the engine should prepend '[SCANNED PDF' to the
    extracted_text before building the LLM prompt.
    """

    @pytest.mark.asyncio
    async def test_scanned_pdf_prompt_contains_marker(self):
        # Build mock orchestrator that captures what prompt it receives
        mock_orch = MagicMock()
        captured_prompts: list[str] = []

        async def fake_infer(req):
            captured_prompts.append(req.user_prompt)
            # Return a minimal success-like result
            from app.services.ai_orchestrator import InferenceResult
            return InferenceResult(
                success=True,
                response_text='{"document_type": "other", "confidence": 10}',
                parsed_json={"document_type": "other", "confidence": 10},
                model_used="test-model",
                fallback_chain_used=["test-model"],
                latency_ttft_ms=0.0,
                latency_total_ms=0.0,
                tokens_in=0,
                tokens_out=0,
                estimated_cost_usd=0.0,
                audit_id="deadbeef12345678",
                timestamp="2026-01-01T00:00:00+00:00",
            )

        mock_orch.infer = fake_infer

        engine = EvidenceEngine(orchestrator=mock_orch)

        # Patch out DB calls so the method doesn't try to connect
        with (
            patch.object(engine, "_find_by_source_hash", new=AsyncMock(return_value=None)),
            patch.object(engine, "_match_obligations", new=AsyncMock(return_value=[])),
            patch.object(engine, "_persist", new=AsyncMock(return_value=True)),
            # Patch _extract_text_pymupdf to simulate a scanned PDF (char_count < 50)
            patch(
                "app.modules.evidence.engine._extract_text_pymupdf",
                return_value=("tiny", 4),  # 4 chars — well below the 50-char threshold
            ),
            # Suppress best-effort RAG indexing.
            # get_rag is imported LOCALLY inside extract_from_pdf's try/except block,
            # so we patch it at its definition site (app.services.rag).
            # Any exception raised is silently swallowed by the try/except there.
            patch("app.services.rag.get_rag", side_effect=Exception("no rag")),
        ):
            await engine.extract_from_pdf(
                pdf_bytes=b"%PDF-1.4 fake",
                filename="scanned_regulation.pdf",
                tenant_id="polkorp",
            )

        assert len(captured_prompts) == 1, "Expected exactly one infer call"
        assert "[SCANNED PDF" in captured_prompts[0], (
            f"Expected '[SCANNED PDF' in prompt, got: {captured_prompts[0][:200]}"
        )

    @pytest.mark.asyncio
    async def test_non_scanned_pdf_prompt_does_not_contain_marker(self):
        """When char_count >= 50, the scanned marker should NOT appear."""
        mock_orch = MagicMock()
        captured_prompts: list[str] = []

        async def fake_infer(req):
            captured_prompts.append(req.user_prompt)
            from app.services.ai_orchestrator import InferenceResult
            return InferenceResult(
                success=True,
                response_text='{"document_type": "circular", "confidence": 95}',
                parsed_json={"document_type": "circular", "confidence": 95},
                model_used="test-model",
                fallback_chain_used=["test-model"],
                latency_ttft_ms=0.0,
                latency_total_ms=0.0,
                tokens_in=0,
                tokens_out=0,
                estimated_cost_usd=0.0,
                audit_id="deadbeef12345678",
                timestamp="2026-01-01T00:00:00+00:00",
            )

        mock_orch.infer = fake_infer
        engine = EvidenceEngine(orchestrator=mock_orch)

        long_text = "A" * 500  # well above 50-char threshold

        with (
            patch.object(engine, "_find_by_source_hash", new=AsyncMock(return_value=None)),
            patch.object(engine, "_match_obligations", new=AsyncMock(return_value=[])),
            patch.object(engine, "_persist", new=AsyncMock(return_value=True)),
            patch(
                "app.modules.evidence.engine._extract_text_pymupdf",
                return_value=(long_text, len(long_text)),
            ),
            patch("app.services.rag.get_rag", side_effect=Exception("no rag")),
        ):
            await engine.extract_from_pdf(
                pdf_bytes=b"%PDF-1.4 fake",
                filename="proper_regulation.pdf",
                tenant_id="polkorp",
            )

        assert len(captured_prompts) == 1
        assert "[SCANNED PDF" not in captured_prompts[0]
