"""Tests for DocumentReferenceResolver (ADR-071 WS-BINDER-001).

No runtime, no real DB — uses mocked async sessions.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.domain.services.document_reference_resolver import (
    ResolvedReference,
    resolve_reference,
    resolve_batch,
    _to_resolved,
)


# ============================================================================
# Helpers
# ============================================================================

SPACE_ID = str(uuid4())
DOC_UUID = uuid4()


def _make_mock_doc(
    doc_id=None,
    display_id="WS-142",
    title="Local Entity Extractor",
    doc_type_id="work_statement",
    version=3,
    space_id=None,
):
    """Create a mock Document ORM instance."""
    doc = MagicMock()
    doc.id = doc_id or DOC_UUID
    doc.display_id = display_id
    doc.title = title
    doc.doc_type_id = doc_type_id
    doc.version = version
    doc.space_id = space_id or SPACE_ID
    return doc


def _mock_db_returning(docs):
    """Create a mock async DB session that returns given docs from execute()."""
    db = AsyncMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = docs
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    result_mock.scalar_one_or_none.return_value = docs[0] if docs else None
    db.execute.return_value = result_mock
    return db


# ============================================================================
# _to_resolved
# ============================================================================


class TestToResolved:
    def test_converts_document_to_resolved_reference(self):
        doc = _make_mock_doc()
        result = _to_resolved(doc)

        assert isinstance(result, ResolvedReference)
        assert result.id == str(DOC_UUID)
        assert result.display_id == "WS-142"
        assert result.title == "Local Entity Extractor"
        assert result.doc_type_id == "work_statement"
        assert result.version == 3
        assert result.space_id == SPACE_ID

    def test_falls_back_to_display_id_when_title_is_none(self):
        doc = _make_mock_doc(title=None)
        result = _to_resolved(doc)
        assert result.title == "WS-142"

    def test_version_is_integer(self):
        doc = _make_mock_doc(version=5)
        result = _to_resolved(doc)
        assert result.version == 5
        assert isinstance(result.version, int)


# ============================================================================
# resolve_batch — display_id references
# ============================================================================


class TestResolveBatchDisplayId:
    @pytest.mark.asyncio
    async def test_resolves_single_display_id(self):
        doc = _make_mock_doc(display_id="WS-142")
        db = _mock_db_returning([doc])

        results = await resolve_batch(db, ["WS-142"], SPACE_ID)

        assert "WS-142" in results
        assert results["WS-142"].display_id == "WS-142"
        assert results["WS-142"].title == "Local Entity Extractor"

    @pytest.mark.asyncio
    async def test_resolves_multiple_display_ids(self):
        doc1 = _make_mock_doc(display_id="WS-142", title="Entity Extractor")
        doc2 = _make_mock_doc(display_id="TA-001", title="Technical Architecture", doc_type_id="technical_architecture")
        db = _mock_db_returning([doc1, doc2])

        results = await resolve_batch(db, ["WS-142", "TA-001"], SPACE_ID)

        assert results["WS-142"] is not None
        assert results["TA-001"] is not None

    @pytest.mark.asyncio
    async def test_unknown_reference_returns_none(self):
        db = _mock_db_returning([])

        results = await resolve_batch(db, ["WS-999"], SPACE_ID)

        assert results["WS-999"] is None

    @pytest.mark.asyncio
    async def test_empty_refs_returns_empty_dict(self):
        db = AsyncMock()

        results = await resolve_batch(db, [], SPACE_ID)

        assert results == {}
        db.execute.assert_not_called()


# ============================================================================
# resolve_batch — version-pinned resolution
# ============================================================================


class TestResolveBatchVersionPinned:
    @pytest.mark.asyncio
    async def test_resolves_pinned_version(self):
        doc = _make_mock_doc(display_id="PD-001", version=2)
        db = _mock_db_returning([doc])

        results = await resolve_batch(
            db, ["PD-001"], SPACE_ID,
            versions={"PD-001": 2},
        )

        assert results["PD-001"] is not None
        assert results["PD-001"].version == 2

    @pytest.mark.asyncio
    async def test_pinned_version_not_found_returns_none(self):
        db = _mock_db_returning([])
        # Override scalar_one_or_none for the pinned query
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        results = await resolve_batch(
            db, ["PD-001"], SPACE_ID,
            versions={"PD-001": 99},
        )

        assert results["PD-001"] is None


# ============================================================================
# resolve_batch — UUID references
# ============================================================================


class TestResolveBatchUUID:
    @pytest.mark.asyncio
    async def test_resolves_uuid_reference(self):
        doc_id = uuid4()
        doc = _make_mock_doc(doc_id=doc_id, display_id="WP-003")
        db = _mock_db_returning([doc])

        ref = str(doc_id)
        results = await resolve_batch(db, [ref], SPACE_ID)

        assert results[ref] is not None
        assert results[ref].display_id == "WP-003"

    @pytest.mark.asyncio
    async def test_mixed_uuid_and_display_id(self):
        doc_id = uuid4()
        doc1 = _make_mock_doc(doc_id=doc_id, display_id="WP-003")
        doc2 = _make_mock_doc(display_id="WS-142")

        # Two separate queries will happen: one for display_ids, one for UUIDs
        db = AsyncMock()
        display_result = MagicMock()
        display_scalars = MagicMock()
        display_scalars.all.return_value = [doc2]
        display_result.scalars.return_value = display_scalars

        uuid_result = MagicMock()
        uuid_scalars = MagicMock()
        uuid_scalars.all.return_value = [doc1]
        uuid_result.scalars.return_value = uuid_scalars

        db.execute.side_effect = [display_result, uuid_result]

        ref_uuid = str(doc_id)
        results = await resolve_batch(db, ["WS-142", ref_uuid], SPACE_ID)

        assert results["WS-142"] is not None
        assert results[ref_uuid] is not None


# ============================================================================
# resolve_reference (single)
# ============================================================================


class TestResolveReference:
    @pytest.mark.asyncio
    async def test_resolves_single_reference(self):
        doc = _make_mock_doc(display_id="TA-001", title="Tech Architecture")
        db = _mock_db_returning([doc])

        result = await resolve_reference(db, "TA-001", SPACE_ID)

        assert result is not None
        assert result.display_id == "TA-001"
        assert result.title == "Tech Architecture"

    @pytest.mark.asyncio
    async def test_returns_none_for_unknown(self):
        db = _mock_db_returning([])

        result = await resolve_reference(db, "XX-999", SPACE_ID)

        assert result is None

    @pytest.mark.asyncio
    async def test_version_pinned_single_reference(self):
        doc = _make_mock_doc(display_id="PD-001", version=2)
        db = _mock_db_returning([doc])

        result = await resolve_reference(db, "PD-001", SPACE_ID, version=2)

        assert result is not None
        assert result.version == 2
