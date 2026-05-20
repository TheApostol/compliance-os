"""
Deadline alert unit tests — pure function coverage (no DB required).

Tests:
  1-4: _severity_for_days thresholds
  5-7: _extract_deadline from properties / description / none
  8:   check_deadlines returns correct summary dict (mocked DB)
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.monitoring.deadline_checker import (
    _severity_for_days,
    _extract_deadline,
    check_deadlines,
)


# ── severity thresholds ───────────────────────────────────────────────────────

def test_severity_critical():
    assert _severity_for_days(0) == "critical"


def test_severity_high():
    assert _severity_for_days(5) == "high"


def test_severity_medium():
    assert _severity_for_days(20) == "medium"


def test_severity_low():
    assert _severity_for_days(60) == "low"


# ── _extract_deadline ─────────────────────────────────────────────────────────

def test_extract_deadline_from_properties():
    ob = SimpleNamespace(
        properties={"deadline": "2026-06-01"},
        description=None,
    )
    result = _extract_deadline(ob)
    assert result is not None
    assert result.year == 2026
    assert result.month == 6
    assert result.day == 1


def test_extract_deadline_from_description():
    ob = SimpleNamespace(
        properties={},
        description="Submit AML report by 2026-06-15 or face penalty.",
    )
    result = _extract_deadline(ob)
    assert result is not None
    assert result.year == 2026
    assert result.month == 6
    assert result.day == 15


def test_extract_deadline_none():
    ob = SimpleNamespace(
        properties={},
        description="No date here, just generic compliance text.",
    )
    result = _extract_deadline(ob)
    assert result is None


# ── check_deadlines summary ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_check_deadlines_returns_summary():
    """
    Mock DB with 2 obligations:
      - ob1: has a deadline 30 days from now → alert created
      - ob2: no deadline → skipped
    Expects: {"created": 1, "updated": 0, "total_checked": 2}
    """
    now = datetime.now(tz=timezone.utc)
    deadline_30 = now + timedelta(days=30)

    # Two fake regulations + obligations
    reg = SimpleNamespace(
        id="reg-001",
        code="BCRA-7825",
        regulator="BCRA",
        country="AR",
        tenant_id="polkorp",
    )

    ob_with_deadline = SimpleNamespace(
        id="ob-001",
        regulation_id="reg-001",
        properties={"deadline": deadline_30.isoformat()},
        description="Submit report",
    )
    ob_no_deadline = SimpleNamespace(
        id="ob-002",
        regulation_id="reg-001",
        properties={},
        description="No date in here",
    )

    # Build mock session using AsyncMock
    mock_session = AsyncMock()

    # Simulate execute() calls returning different scalars depending on query
    call_count = [0]

    async def fake_execute(stmt):
        call_count[0] += 1
        result = MagicMock()
        if call_count[0] == 1:
            # First call: select Regulation
            result.scalars.return_value.all.return_value = [reg]
        elif call_count[0] == 2:
            # Second call: select Obligation
            result.scalars.return_value.all.return_value = [ob_with_deadline, ob_no_deadline]
        else:
            # Subsequent calls: checking for existing DeadlineAlert
            result.scalar_one_or_none.return_value = None
        return result

    mock_session.execute = fake_execute
    mock_session.commit = AsyncMock()
    mock_session.add = MagicMock()

    # Patch AsyncSessionLocal to return our mock session as a context manager
    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    with patch(
        "app.modules.monitoring.deadline_checker.AsyncSessionLocal",
        return_value=mock_ctx,
    ):
        result = await check_deadlines(tenant_id="polkorp")

    assert result["total_checked"] == 2
    assert result["created"] == 1
    assert result["updated"] == 0
