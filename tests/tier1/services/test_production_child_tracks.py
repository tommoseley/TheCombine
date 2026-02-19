"""Tests for child document tracks in production service."""

import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4


class FakeDocument:
    """Minimal Document stub for production service tests."""

    def __init__(self, doc_type_id, title="", content=None, parent_id=None, status="draft", instance_id=None):
        self.id = uuid4()
        self.doc_type_id = doc_type_id
        self.title = title
        self.content = content or {}
        self.parent_document_id = parent_id
        self.status = status
        self.is_latest = True
        self.space_type = "project"
        self.space_id = uuid4()
        self.instance_id = instance_id


class FakeScalarResult:
    """Minimal scalars().all() stub."""

    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items


class FakeResult:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return FakeScalarResult(self._items)

    def scalar_one_or_none(self):
        return self._items[0] if self._items else None


def make_doc_type_deps():
    """Return minimal document_type_dependencies for implementation_plan."""
    return [
        {
            "id": "project_discovery",
            "name": "Project Discovery",
            "requires": [],
            "scope": "project",
            "may_own": [],
            "collection_field": None,
            "child_doc_type": None,
        },
        {
            "id": "implementation_plan",
            "name": "Implementation Plan",
            "requires": ["project_discovery"],
            "scope": "project",
            "may_own": ["epic"],
            "collection_field": "epics",
            "child_doc_type": "epic",
        },
    ]


@pytest.mark.asyncio
async def test_child_docs_included_as_tracks():
    """Spawned epic docs appear as additional tracks with non-project scope."""
    from app.api.services.production_service import get_production_tracks

    project_uuid = uuid4()

    # Parent document
    ipf_doc = FakeDocument(
        "implementation_plan",
        title="Implementation Plan",
        content={"epics": []},
        status="complete",
    )
    # Discovery doc (required for IPF to be unblocked)
    disc_doc = FakeDocument(
        "project_discovery",
        title="Project Discovery",
        status="complete",
    )

    # Child epic documents
    epic1 = FakeDocument(
        "epic",
        title="Epic: Storage Foundation",
        content={"epic_id": "storage_foundation", "name": "Storage Foundation", "intent": "Local storage", "sequence": 1},
        parent_id=ipf_doc.id,
    )
    epic2 = FakeDocument(
        "epic",
        title="Epic: Data Models",
        content={"epic_id": "data_models", "name": "Data Models", "intent": "Core data structures", "sequence": 2},
        parent_id=ipf_doc.id,
    )

    # Set up DB mock to return docs based on query
    call_count = 0

    async def mock_execute(query):
        nonlocal call_count
        call_count += 1
        # Call 1: project documents (space_id based)
        if call_count == 1:
            return FakeResult([disc_doc, ipf_doc])
        # Call 2: active workflow executions
        elif call_count == 2:
            return FakeResult([])
        # Call 3: document type descriptions
        elif call_count == 3:
            return FakeResult([])
        # Call 4: child epic documents
        elif call_count == 4:
            return FakeResult([epic1, epic2])
        return FakeResult([])

    db = AsyncMock()
    db.execute = mock_execute

    with patch("app.api.services.production_service.get_document_type_dependencies", return_value=make_doc_type_deps()), \
         patch("app.api.services.production_service._get_workflow_plan", return_value=None):
        tracks = await get_production_tracks(db, str(project_uuid))

    # Find the child tracks
    child_tracks = [t for t in tracks if t.get("scope") == "epic"]
    assert len(child_tracks) == 2

    # Check child track properties
    storage = next(t for t in child_tracks if t["identifier"] == "storage_foundation")
    assert storage["document_type"] == "epic"
    assert storage["document_name"] == "Epic: Storage Foundation"
    assert storage["state"] == "produced"
    assert storage["sequence"] == 1

    data_models = next(t for t in child_tracks if t["identifier"] == "data_models")
    assert data_models["document_type"] == "epic"
    assert data_models["document_name"] == "Epic: Data Models"
    assert data_models["description"] == "Core data structures"
    assert data_models["sequence"] == 2


@pytest.mark.asyncio
async def test_no_child_tracks_when_no_children_exist():
    """No extra tracks when parent has no spawned children."""
    from app.api.services.production_service import get_production_tracks

    project_uuid = uuid4()

    ipf_doc = FakeDocument(
        "implementation_plan",
        title="Implementation Plan",
        content={"epics": []},
        status="complete",
    )
    disc_doc = FakeDocument(
        "project_discovery",
        title="Project Discovery",
        status="complete",
    )

    call_count = 0

    async def mock_execute(query):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return FakeResult([disc_doc, ipf_doc])
        elif call_count == 2:
            return FakeResult([])
        elif call_count == 3:
            return FakeResult([])
        elif call_count == 4:
            return FakeResult([])  # No children
        return FakeResult([])

    db = AsyncMock()
    db.execute = mock_execute

    with patch("app.api.services.production_service.get_document_type_dependencies", return_value=make_doc_type_deps()), \
         patch("app.api.services.production_service._get_workflow_plan", return_value=None):
        tracks = await get_production_tracks(db, str(project_uuid))

    child_tracks = [t for t in tracks if t.get("scope") == "epic"]
    assert len(child_tracks) == 0


@pytest.mark.asyncio
async def test_no_child_query_when_parent_doc_not_produced():
    """Don't query children if parent document doesn't exist yet."""
    from app.api.services.production_service import get_production_tracks

    project_uuid = uuid4()

    # Only discovery doc exists, no IPF yet
    disc_doc = FakeDocument(
        "project_discovery",
        title="Project Discovery",
        status="complete",
    )

    call_count = 0

    async def mock_execute(query):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return FakeResult([disc_doc])
        elif call_count == 2:
            return FakeResult([])
        elif call_count == 3:
            return FakeResult([])
        return FakeResult([])

    db = AsyncMock()
    db.execute = mock_execute

    with patch("app.api.services.production_service.get_document_type_dependencies", return_value=make_doc_type_deps()), \
         patch("app.api.services.production_service._get_workflow_plan", return_value=None):
        tracks = await get_production_tracks(db, str(project_uuid))

    child_tracks = [t for t in tracks if t.get("scope") == "epic"]
    assert len(child_tracks) == 0
    # Should only make 3 DB calls (docs, executions, doc_type_descriptions) - no child query
    assert call_count == 3
