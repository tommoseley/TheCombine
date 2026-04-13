"""Tests for WorkPlanAssemblyService (ADR-071 WS-BINDER-007).

No runtime, no real DB — uses mocked async sessions.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.domain.services.work_plan_assembly_service import (
    assemble_work_plan,
    WorkPlanContent,
    _compose_executive_summary,
    _build_decision_log,
    _build_dependency_summary,
)


SPACE_ID = str(uuid4())


def _make_mock_doc(
    display_id="WS-001",
    title="Test Document",
    doc_type_id="work_statement",
    version=1,
    content=None,
    parent_document_id=None,
):
    doc = MagicMock()
    doc.id = uuid4()
    doc.display_id = display_id
    doc.title = title
    doc.doc_type_id = doc_type_id
    doc.version = version
    doc.space_id = SPACE_ID
    doc.content = content or {}
    doc.parent_document_id = parent_document_id
    return doc


def _mock_db_multi(query_results):
    """Mock DB that returns different results for sequential queries."""
    db = AsyncMock()
    results = []
    for docs in query_results:
        if isinstance(docs, list):
            result = MagicMock()
            scalars = MagicMock()
            scalars.all.return_value = docs
            result.scalars.return_value = scalars
            result.scalar_one_or_none.return_value = docs[0] if docs else None
            results.append(result)
        else:
            # Single doc or None
            result = MagicMock()
            scalars = MagicMock()
            scalars.all.return_value = [docs] if docs else []
            result.scalars.return_value = scalars
            result.scalar_one_or_none.return_value = docs
            results.append(result)
    db.execute.side_effect = results
    return db


class TestBuildDecisionLog:
    @pytest.mark.asyncio
    async def test_empty_when_no_synthesis(self):
        db = _mock_db_multi([None])
        log = await _build_decision_log(db, SPACE_ID)
        assert log == []

    @pytest.mark.asyncio
    async def test_builds_from_operator_decisions(self):
        doc = _make_mock_doc(
            doc_type_id="synthesis_delta",
            content={
                "actions": [
                    {"action_type": "MERGE_WS", "targets": ["WS-001", "WS-002"],
                     "severity": "should_fix", "headline": "Merge overlapping WSs"},
                ],
                "questions": [],
                "_operator_decisions": {
                    "MERGE_WS-WS-001,WS-002": {
                        "decision": "accept",
                        "note": "Option 1 — separate paths",
                        "decided_at": "2026-04-08T12:00:00Z",
                    },
                },
            },
        )
        db = _mock_db_multi([doc])

        log = await _build_decision_log(db, SPACE_ID)

        assert len(log) == 1
        assert log[0]["decision"] == "accept"
        assert log[0]["headline"] == "Merge overlapping WSs"
        assert log[0]["note"] == "Option 1 — separate paths"
        assert log[0]["finding_type"] == "action"


class TestBuildDependencySummary:
    @pytest.mark.asyncio
    async def test_empty_when_no_wps(self):
        db = _mock_db_multi([[]])
        deps = await _build_dependency_summary(db, SPACE_ID)
        assert deps == []

    @pytest.mark.asyncio
    async def test_extracts_dependencies(self):
        wp = _make_mock_doc(
            display_id="WP-002",
            title="Second Package",
            doc_type_id="work_package",
            content={
                "dependencies": [
                    {"wp_id": "WP-001", "dependency_type": "depends_on", "title": "First Package"},
                ],
            },
        )
        db = _mock_db_multi([[wp]])

        deps = await _build_dependency_summary(db, SPACE_ID)

        assert len(deps) == 1
        assert deps[0]["from_display_id"] == "WP-002"
        assert deps[0]["to_display_id"] == "WP-001"
        assert deps[0]["dependency_type"] == "depends_on"


class TestWorkPlanContent:
    def test_to_dict_has_all_fields(self):
        content = WorkPlanContent(
            project_id="test",
            assembled_at="2026-04-08T12:00:00Z",
            document_count=5,
            referenced_documents=[],
            groups=[],
            executive_summary={"project_name": "Test"},
            decision_log=[],
            dependency_summary=[],
        )
        d = content.to_dict()

        assert "project_id" in d
        assert "executive_summary" in d
        assert "decision_log" in d
        assert "dependency_summary" in d
        assert "referenced_documents" in d
        assert "groups" in d
