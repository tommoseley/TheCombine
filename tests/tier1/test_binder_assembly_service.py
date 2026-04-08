"""Tests for BinderAssemblyService (ADR-071 WS-BINDER-004).

No runtime, no real DB — uses mocked async sessions.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.domain.services.binder_assembly_service import (
    assemble_binder,
    BinderContent,
    DOC_TYPE_GROUPS,
    GROUP_ORDER,
)


SPACE_ID = str(uuid4())


def _make_mock_doc(
    display_id="WS-142",
    title="Test Document",
    doc_type_id="work_statement",
    version=1,
    parent_document_id=None,
):
    doc = MagicMock()
    doc.id = uuid4()
    doc.display_id = display_id
    doc.title = title
    doc.doc_type_id = doc_type_id
    doc.version = version
    doc.space_id = SPACE_ID
    doc.parent_document_id = parent_document_id
    return doc


def _mock_db(docs, parent_display_id=None):
    """Create a mock DB returning docs for the main query and parent lookup."""
    db = AsyncMock()

    # Main query returns all docs
    main_result = MagicMock()
    main_scalars = MagicMock()
    main_scalars.all.return_value = docs
    main_result.scalars.return_value = main_scalars

    # Parent lookup returns display_id
    parent_result = MagicMock()
    parent_result.scalar_one_or_none.return_value = parent_display_id

    db.execute.side_effect = [main_result] + [parent_result] * len(docs)
    return db


class TestAssembleBinder:
    @pytest.mark.asyncio
    async def test_empty_project(self):
        db = _mock_db([])
        result = await assemble_binder(db, SPACE_ID)

        assert isinstance(result, BinderContent)
        assert result.document_count == 0
        assert result.referenced_documents == []
        assert result.groups == []

    @pytest.mark.asyncio
    async def test_single_document(self):
        doc = _make_mock_doc(
            display_id="PD-001",
            title="Project Discovery",
            doc_type_id="project_discovery",
            version=2,
        )
        db = _mock_db([doc])

        result = await assemble_binder(db, SPACE_ID)

        assert result.document_count == 1
        assert len(result.referenced_documents) == 1

        ref = result.referenced_documents[0]
        assert ref["display_id"] == "PD-001"
        assert ref["title"] == "Project Discovery"
        assert ref["version"] == 2
        assert ref["doc_type_id"] == "project_discovery"
        assert ref["group"] == "discovery"

    @pytest.mark.asyncio
    async def test_multiple_doc_types_grouped(self):
        docs = [
            _make_mock_doc(display_id="PD-001", doc_type_id="project_discovery"),
            _make_mock_doc(display_id="TA-001", doc_type_id="technical_architecture"),
            _make_mock_doc(display_id="WP-001", doc_type_id="work_package"),
        ]
        db = _mock_db(docs)

        result = await assemble_binder(db, SPACE_ID)

        assert result.document_count == 3
        groups = [g["id"] for g in result.groups]
        assert "discovery" in groups
        assert "architecture" in groups
        assert "work_packages" in groups

    @pytest.mark.asyncio
    async def test_groups_in_pipeline_order(self):
        docs = [
            _make_mock_doc(display_id="WP-001", doc_type_id="work_package"),
            _make_mock_doc(display_id="PD-001", doc_type_id="project_discovery"),
            _make_mock_doc(display_id="TA-001", doc_type_id="technical_architecture"),
        ]
        db = _mock_db(docs)

        result = await assemble_binder(db, SPACE_ID)

        group_ids = [g["id"] for g in result.groups]
        assert group_ids.index("discovery") < group_ids.index("architecture")
        assert group_ids.index("architecture") < group_ids.index("work_packages")

    @pytest.mark.asyncio
    async def test_synthesis_delta_excluded(self):
        docs = [
            _make_mock_doc(display_id="PD-001", doc_type_id="project_discovery"),
            _make_mock_doc(display_id="SD-001", doc_type_id="synthesis_delta"),
        ]
        db = _mock_db(docs)

        result = await assemble_binder(db, SPACE_ID)

        assert result.document_count == 1
        assert all(r["doc_type_id"] != "synthesis_delta" for r in result.referenced_documents)

    @pytest.mark.asyncio
    async def test_version_pinned(self):
        doc = _make_mock_doc(display_id="TA-001", doc_type_id="technical_architecture", version=5)
        db = _mock_db([doc])

        result = await assemble_binder(db, SPACE_ID)

        assert result.referenced_documents[0]["version"] == 5

    @pytest.mark.asyncio
    async def test_project_id_in_output(self):
        db = _mock_db([])
        result = await assemble_binder(db, SPACE_ID)

        assert result.project_id == SPACE_ID

    @pytest.mark.asyncio
    async def test_assembled_at_is_iso_format(self):
        db = _mock_db([])
        result = await assemble_binder(db, SPACE_ID)

        # Should be parseable as ISO 8601
        assert "T" in result.assembled_at

    @pytest.mark.asyncio
    async def test_to_dict_structure(self):
        doc = _make_mock_doc(display_id="PD-001", doc_type_id="project_discovery")
        db = _mock_db([doc])

        result = await assemble_binder(db, SPACE_ID)
        d = result.to_dict()

        assert "project_id" in d
        assert "assembled_at" in d
        assert "document_count" in d
        assert "referenced_documents" in d
        assert "groups" in d

    @pytest.mark.asyncio
    async def test_ws_gets_parent_display_id(self):
        wp_id = uuid4()
        ws = _make_mock_doc(
            display_id="WS-001",
            doc_type_id="work_statement",
            parent_document_id=wp_id,
        )
        db = _mock_db([ws], parent_display_id="WP-001")

        result = await assemble_binder(db, SPACE_ID)

        assert result.referenced_documents[0]["parent_display_id"] == "WP-001"


class TestDocTypeGroups:
    def test_all_pipeline_types_have_groups(self):
        expected = [
            "concierge_intake", "project_discovery",
            "technical_architecture", "implementation_plan",
            "work_package", "work_statement", "work_package_candidate",
        ]
        for dt in expected:
            assert dt in DOC_TYPE_GROUPS, f"{dt} missing from DOC_TYPE_GROUPS"

    def test_all_group_ids_in_order(self):
        for dt, (group_id, _) in DOC_TYPE_GROUPS.items():
            assert group_id in GROUP_ORDER, f"Group {group_id} for {dt} not in GROUP_ORDER"
