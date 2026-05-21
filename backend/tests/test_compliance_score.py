"""
Unit tests for compliance_score.compute_score.
All DB calls are mocked — no live database required.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.compliance_score import ComplianceScore, ObligationScore, compute_score


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entity(entity_id: str, tenant_id: str = "t1", name: str = "Acme") -> MagicMock:
    e = MagicMock()
    e.id = entity_id
    e.tenant_id = tenant_id
    e.name = name
    return e


def _make_vertex(
    vertex_id: str | None = None,
    vertex_type: str = "obligation",
    entity_id: str | None = None,
    label: str = "Test obligation",
    properties: dict | None = None,
) -> MagicMock:
    v = MagicMock()
    v.id = vertex_id or str(uuid.uuid4())
    v.vertex_type = vertex_type
    v.entity_id = entity_id
    v.label = label
    v.properties = properties or {}
    return v


def _make_edge(
    edge_id: str | None = None,
    edge_type: str = "APPLIES_TO",
    from_vertex_id: str | None = None,
    to_vertex_id: str | None = None,
) -> MagicMock:
    e = MagicMock()
    e.id = edge_id or str(uuid.uuid4())
    e.edge_type = edge_type
    e.from_vertex_id = from_vertex_id or str(uuid.uuid4())
    e.to_vertex_id = to_vertex_id or str(uuid.uuid4())
    return e


# ---------------------------------------------------------------------------
# Session mock builder
# ---------------------------------------------------------------------------

def _build_session_mock(query_map: list) -> MagicMock:
    """
    Build an AsyncMock session where each successive execute() call returns the
    next item from query_map.

    - If the item is a list  → supports .scalars().all()
    - Otherwise              → supports .scalar_one_or_none()
    """
    call_results = []
    for result in query_map:
        exec_result = MagicMock()
        if isinstance(result, list):
            exec_result.scalar_one_or_none.return_value = None
            scalars_mock = MagicMock()
            scalars_mock.all.return_value = result
            exec_result.scalars.return_value = scalars_mock
        else:
            exec_result.scalar_one_or_none.return_value = result
            scalars_mock = MagicMock()
            scalars_mock.all.return_value = []
            exec_result.scalars.return_value = scalars_mock
        call_results.append(exec_result)

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=call_results)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    return session


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_score_entity_not_found():
    """Entity query returns None → compute_score returns None."""
    entity_id = str(uuid.uuid4())
    session = _build_session_mock([None])  # entity not found

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr("app.db.base.AsyncSessionLocal", lambda: session)
        result = await compute_score(entity_id=entity_id, tenant_id="t1")

    assert result is None


@pytest.mark.asyncio
async def test_score_no_vertex():
    """Entity exists but has no GraphVertex → score_pct=100.0, total=0."""
    entity_id = str(uuid.uuid4())
    entity = _make_entity(entity_id)

    session = _build_session_mock([
        entity,  # ComplianceEntity query
        None,    # GraphVertex query → not found
    ])

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr("app.db.base.AsyncSessionLocal", lambda: session)
        result = await compute_score(entity_id=entity_id, tenant_id="t1")

    assert result is not None
    assert isinstance(result, ComplianceScore)
    assert result.score_pct == 100.0
    assert result.total_obligations == 0
    assert result.satisfied_obligations == 0
    assert result.breakdown == []


@pytest.mark.asyncio
async def test_score_no_obligations():
    """Entity + vertex exist, but no APPLIES_TO edges → score_pct=100.0, total=0."""
    entity_id = str(uuid.uuid4())
    entity_vertex_id = str(uuid.uuid4())
    entity = _make_entity(entity_id)
    entity_vertex = _make_vertex(entity_vertex_id, vertex_type="entity", entity_id=entity_id)

    session = _build_session_mock([
        entity,         # entity query
        entity_vertex,  # vertex query
        [],             # APPLIES_TO edges → empty
    ])

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr("app.db.base.AsyncSessionLocal", lambda: session)
        result = await compute_score(entity_id=entity_id, tenant_id="t1")

    assert result is not None
    assert result.score_pct == 100.0
    assert result.total_obligations == 0
    assert result.satisfied_obligations == 0
    assert result.breakdown == []


@pytest.mark.asyncio
async def test_score_all_satisfied():
    """3 obligations all with SATISFIES edges → score_pct=100.0."""
    entity_id = str(uuid.uuid4())
    entity_vertex_id = str(uuid.uuid4())
    entity = _make_entity(entity_id)
    entity_vertex = _make_vertex(entity_vertex_id, vertex_type="entity", entity_id=entity_id)

    ob_vertex_ids = [str(uuid.uuid4()) for _ in range(3)]
    ctrl_vertex_ids = [str(uuid.uuid4()) for _ in range(3)]

    applies_edges = [
        _make_edge(edge_type="APPLIES_TO", from_vertex_id=ob_id, to_vertex_id=entity_vertex_id)
        for ob_id in ob_vertex_ids
    ]
    ob_vertices = [
        _make_vertex(
            ob_id, vertex_type="obligation", label=f"Obligation {i}",
            properties={"obligation_type": "reporting"},
        )
        for i, ob_id in enumerate(ob_vertex_ids)
    ]
    satisfies_edges = [
        _make_edge(edge_type="SATISFIES", from_vertex_id=ctrl_id, to_vertex_id=ob_id)
        for ctrl_id, ob_id in zip(ctrl_vertex_ids, ob_vertex_ids)
    ]
    ctrl_vertices = [
        _make_vertex(ctrl_id, vertex_type="control", label=f"Control {i}")
        for i, ctrl_id in enumerate(ctrl_vertex_ids)
    ]

    # Query sequence: entity, entity_vertex, applies_edges list,
    # then per obligation: ob_vertex, satisfies_edge, ctrl_vertex
    query_map = [entity, entity_vertex, applies_edges]
    for ob_v, sat_e, ctrl_v in zip(ob_vertices, satisfies_edges, ctrl_vertices):
        query_map += [ob_v, sat_e, ctrl_v]

    session = _build_session_mock(query_map)

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr("app.db.base.AsyncSessionLocal", lambda: session)
        result = await compute_score(entity_id=entity_id, tenant_id="t1")

    assert result is not None
    assert result.score_pct == 100.0
    assert result.total_obligations == 3
    assert result.satisfied_obligations == 3
    assert all(o.is_satisfied for o in result.breakdown)


@pytest.mark.asyncio
async def test_score_none_satisfied():
    """3 obligations, no SATISFIES edges → score_pct=0.0."""
    entity_id = str(uuid.uuid4())
    entity_vertex_id = str(uuid.uuid4())
    entity = _make_entity(entity_id)
    entity_vertex = _make_vertex(entity_vertex_id, vertex_type="entity", entity_id=entity_id)

    ob_vertex_ids = [str(uuid.uuid4()) for _ in range(3)]
    applies_edges = [
        _make_edge(edge_type="APPLIES_TO", from_vertex_id=ob_id, to_vertex_id=entity_vertex_id)
        for ob_id in ob_vertex_ids
    ]
    ob_vertices = [
        _make_vertex(ob_id, vertex_type="obligation", label=f"Obligation {i}")
        for i, ob_id in enumerate(ob_vertex_ids)
    ]

    query_map = [entity, entity_vertex, applies_edges]
    for ob_v in ob_vertices:
        query_map += [ob_v, None]  # no SATISFIES edge

    session = _build_session_mock(query_map)

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr("app.db.base.AsyncSessionLocal", lambda: session)
        result = await compute_score(entity_id=entity_id, tenant_id="t1")

    assert result is not None
    assert result.score_pct == 0.0
    assert result.total_obligations == 3
    assert result.satisfied_obligations == 0
    assert all(not o.is_satisfied for o in result.breakdown)
    assert all(o.control_label is None for o in result.breakdown)


@pytest.mark.asyncio
async def test_score_partial():
    """2 of 4 obligations satisfied → score_pct=50.0."""
    entity_id = str(uuid.uuid4())
    entity_vertex_id = str(uuid.uuid4())
    entity = _make_entity(entity_id)
    entity_vertex = _make_vertex(entity_vertex_id, vertex_type="entity", entity_id=entity_id)

    ob_vertex_ids = [str(uuid.uuid4()) for _ in range(4)]
    ctrl_vertex_ids = [str(uuid.uuid4()) for _ in range(2)]

    applies_edges = [
        _make_edge(edge_type="APPLIES_TO", from_vertex_id=ob_id, to_vertex_id=entity_vertex_id)
        for ob_id in ob_vertex_ids
    ]
    ob_vertices = [
        _make_vertex(ob_id, vertex_type="obligation", label=f"Obligation {i}")
        for i, ob_id in enumerate(ob_vertex_ids)
    ]
    satisfies_edges = [
        _make_edge(
            edge_type="SATISFIES",
            from_vertex_id=ctrl_vertex_ids[i],
            to_vertex_id=ob_vertex_ids[i],
        )
        for i in range(2)
    ]
    ctrl_vertices = [
        _make_vertex(ctrl_vertex_ids[i], vertex_type="control", label=f"Control {i}")
        for i in range(2)
    ]

    query_map = [entity, entity_vertex, applies_edges]
    for i, ob_v in enumerate(ob_vertices):
        if i < 2:
            query_map += [ob_v, satisfies_edges[i], ctrl_vertices[i]]
        else:
            query_map += [ob_v, None]  # not satisfied

    session = _build_session_mock(query_map)

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr("app.db.base.AsyncSessionLocal", lambda: session)
        result = await compute_score(entity_id=entity_id, tenant_id="t1")

    assert result is not None
    assert result.score_pct == 50.0
    assert result.total_obligations == 4
    assert result.satisfied_obligations == 2
    assert sum(1 for o in result.breakdown if o.is_satisfied) == 2
    assert sum(1 for o in result.breakdown if not o.is_satisfied) == 2


@pytest.mark.asyncio
async def test_breakdown_has_control_label():
    """Satisfied obligation includes the control_label in breakdown."""
    entity_id = str(uuid.uuid4())
    entity_vertex_id = str(uuid.uuid4())
    ob_vertex_id = str(uuid.uuid4())
    ctrl_vertex_id = str(uuid.uuid4())

    entity = _make_entity(entity_id)
    entity_vertex = _make_vertex(entity_vertex_id, vertex_type="entity", entity_id=entity_id)
    applies_edge = _make_edge(
        edge_type="APPLIES_TO", from_vertex_id=ob_vertex_id, to_vertex_id=entity_vertex_id
    )
    ob_vertex = _make_vertex(
        ob_vertex_id,
        vertex_type="obligation",
        label="SAR Reporting",
        properties={"obligation_type": "reporting"},
    )
    satisfies_edge = _make_edge(
        edge_type="SATISFIES", from_vertex_id=ctrl_vertex_id, to_vertex_id=ob_vertex_id
    )
    ctrl_vertex = _make_vertex(ctrl_vertex_id, vertex_type="control", label="Automated SAR Workflow")

    query_map = [entity, entity_vertex, [applies_edge], ob_vertex, satisfies_edge, ctrl_vertex]
    session = _build_session_mock(query_map)

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr("app.db.base.AsyncSessionLocal", lambda: session)
        result = await compute_score(entity_id=entity_id, tenant_id="t1")

    assert result is not None
    assert len(result.breakdown) == 1
    ob_score: ObligationScore = result.breakdown[0]
    assert ob_score.is_satisfied is True
    assert ob_score.control_label == "Automated SAR Workflow"
    assert ob_score.title == "SAR Reporting"
    assert ob_score.obligation_type == "reporting"
