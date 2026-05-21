"""
Tests for the export service and export endpoints.
All DB access is mocked — no live database required.
"""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.auth import CurrentUser, get_current_user
from app.services.export_service import (
    export_evidence_csv,
    export_obligations_csv,
    export_compliance_report_pdf,
)


# ─────────────────────────────────────────────────────────────────────────────
# Test client fixture (no-op lifespan, auth overridden)
# ─────────────────────────────────────────────────────────────────────────────

def _analyst_user() -> CurrentUser:
    return CurrentUser(user_id="test-user", tenant_id="polkorp", role="analyst")


@pytest.fixture(scope="module")
def export_client() -> TestClient:
    """TestClient with no-op lifespan and auth override (no DB connection needed)."""
    from app.main import app

    @asynccontextmanager
    async def _noop_lifespan(app):
        yield

    app.router.lifespan_context = _noop_lifespan
    app.dependency_overrides[get_current_user] = _analyst_user

    with TestClient(app, raise_server_exceptions=True) as client:
        yield client

    app.dependency_overrides.pop(get_current_user, None)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_score(score_pct=75.0, total=4, satisfied=3):
    score = MagicMock()
    score.score_pct = score_pct
    score.total_obligations = total
    score.satisfied_obligations = satisfied
    score.breakdown = []
    return score


def _make_obligation_score(satisfied=True):
    ob = MagicMock()
    ob.title = "SAR Reporting obligation"
    ob.obligation_type = "reporting"
    ob.is_satisfied = satisfied
    ob.control_label = "Control A" if satisfied else None
    return ob


# ─────────────────────────────────────────────────────────────────────────────
# 1. test_obligations_csv_empty
# ─────────────────────────────────────────────────────────────────────────────

def test_obligations_csv_empty():
    """Empty obligations list → CSV contains 'No obligations found' marker."""
    result = export_obligations_csv([])
    assert isinstance(result, bytes)
    text = result.decode("utf-8")
    assert "No obligations found" in text


# ─────────────────────────────────────────────────────────────────────────────
# 2. test_obligations_csv_rows
# ─────────────────────────────────────────────────────────────────────────────

def test_obligations_csv_rows():
    """2 obligation dicts → header row + 2 data rows."""
    obligations = [
        {
            "id": str(uuid.uuid4()),
            "regulation_code": "ComA-7825",
            "regulator": "BCRA",
            "country": "AR",
            "description": "File SAR within 24 hours",
            "obligation_type": "reporting",
            "deadline": "2026-06-30",
            "created_at": "2026-01-01T00:00:00+00:00",
        },
        {
            "id": str(uuid.uuid4()),
            "regulation_code": "UIF-RES-4/2017",
            "regulator": "UIF",
            "country": "AR",
            "description": "Customer due diligence",
            "obligation_type": "kyc",
            "deadline": "ongoing",
            "created_at": "2026-01-02T00:00:00+00:00",
        },
    ]
    result = export_obligations_csv(obligations)
    assert isinstance(result, bytes)
    text = result.decode("utf-8")
    lines = [l for l in text.splitlines() if l.strip()]
    # Header + 2 data rows
    assert len(lines) == 3
    assert "regulation_code" in lines[0]  # header present
    assert "ComA-7825" in text
    assert "UIF-RES-4/2017" in text


# ─────────────────────────────────────────────────────────────────────────────
# 3. test_evidence_csv_rows
# ─────────────────────────────────────────────────────────────────────────────

def test_evidence_csv_rows():
    """2 evidence document dicts → header row + 2 data rows."""
    documents = [
        {
            "id": str(uuid.uuid4()),
            "title": "bcra_resolution.pdf",
            "doc_type": "pdf",
            "confidence_score": "87",
            "custody_hash": "abc123",
            "uploaded_by": "analyst@acme.com",
            "created_at": "2026-01-01T00:00:00+00:00",
        },
        {
            "id": str(uuid.uuid4()),
            "title": "uif_guidance.pdf",
            "doc_type": "pdf",
            "confidence_score": "92",
            "custody_hash": "def456",
            "uploaded_by": "admin@acme.com",
            "created_at": "2026-01-02T00:00:00+00:00",
        },
    ]
    result = export_evidence_csv(documents)
    assert isinstance(result, bytes)
    text = result.decode("utf-8")
    lines = [l for l in text.splitlines() if l.strip()]
    assert len(lines) == 3              # header + 2 data rows
    assert "custody_hash" in lines[0]  # header present
    assert "abc123" in text
    assert "def456" in text


# ─────────────────────────────────────────────────────────────────────────────
# 4. test_pdf_returns_pdf_bytes
# ─────────────────────────────────────────────────────────────────────────────

def test_pdf_returns_pdf_bytes():
    """export_compliance_report_pdf returns bytes that start with the PDF magic bytes."""
    score = _make_score()
    obligations = [_make_obligation_score(satisfied=True), _make_obligation_score(satisfied=False)]
    alerts = [
        {
            "regulation_code": "ComA-7825",
            "title": "SAR filing deadline approaching",
            "deadline": "2026-06-30",
            "days_remaining": 40,
            "severity": "high",
        }
    ]

    result = export_compliance_report_pdf(
        entity_name="Acme PSP S.A.",
        score=score,
        obligations=obligations,
        alerts=alerts,
        tenant_id="polkorp",
    )

    assert isinstance(result, bytes)
    assert result[:4] == b"%PDF", f"Expected PDF magic bytes, got {result[:8]!r}"


# ─────────────────────────────────────────────────────────────────────────────
# 5. test_export_endpoint_csv
# ─────────────────────────────────────────────────────────────────────────────

def test_export_endpoint_csv(export_client):
    """
    GET /api/v1/export/obligations.csv → 200, content-type text/csv.
    DB is mocked to return an empty result set.
    """
    empty_execute_result = MagicMock()
    empty_execute_result.all.return_value = []

    session_mock = AsyncMock()
    session_mock.execute = AsyncMock(return_value=empty_execute_result)
    session_mock.__aenter__ = AsyncMock(return_value=session_mock)
    session_mock.__aexit__ = AsyncMock(return_value=False)

    with patch("app.db.base.AsyncSessionLocal", return_value=session_mock):
        response = export_client.get("/api/v1/export/obligations.csv")

    assert response.status_code == 200
    assert "text/csv" in response.headers.get("content-type", "")
