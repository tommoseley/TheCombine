"""Tests for PlanExecutor._upsert_child_document and _mark_stale_children (WS-CRAP-009).

Tests the 2 extracted sub-methods:
1. _upsert_child_document
2. _mark_stale_children
"""

import importlib
import importlib.util
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------

class FakeState:
    """Minimal DocumentWorkflowState stub."""

    def __init__(self):
        self.project_id = str(uuid4())
        self.document_type = "implementation_plan"


class FakeDocument:
    """Minimal Document stub for existing children."""

    def __init__(self, instance_id, version=1):
        self.id = uuid4()
        self.instance_id = instance_id
        self.content = {"data": "old"}
        self.title = f"Old title: {instance_id}"
        self.version = version
        self.is_latest = True
        self.lifecycle_state = "complete"

    def update_revision_hash(self):
        pass

    def mark_stale(self):
        self.lifecycle_state = "stale"


# ---------------------------------------------------------------------------
# Fixture: PlanExecutor with mocked dependencies
# ---------------------------------------------------------------------------

@pytest.fixture
def executor():
    """Create PlanExecutor with mocked dependencies, avoiding circular imports."""
    mock_production = MagicMock()
    mock_production.publish_event = AsyncMock()
    sys.modules.setdefault("app.api.v1.routers.production", mock_production)

    spec = importlib.util.spec_from_file_location(
        "plan_executor_spawn_test",
        "app/domain/workflow/plan_executor.py",
        submodule_search_locations=[],
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    PlanExecutor = mod.PlanExecutor

    pe = PlanExecutor.__new__(PlanExecutor)
    pe._db_session = AsyncMock()
    pe._persistence = AsyncMock()
    return pe


# ===================================================================
# 1. _upsert_child_document
# ===================================================================

class TestUpsertChildDocument:
    @pytest.mark.asyncio
    async def test_existing_child_is_updated(self, executor):
        """Existing child → version incremented, content/title updated."""
        state = FakeState()
        parent_id = uuid4()
        existing_doc = FakeDocument("alpha", version=2)
        existing_children = {"alpha": existing_doc}

        spec = {
            "identifier": "alpha",
            "doc_type_id": "work_package",
            "title": "Updated Title",
            "content": {"data": "new"},
        }

        result = await executor._upsert_child_document(
            spec, existing_children, state, parent_id,
        )

        assert result == "updated"
        assert existing_doc.version == 3
        assert existing_doc.content == {"data": "new"}
        assert existing_doc.title == "Updated Title"

    @pytest.mark.asyncio
    async def test_new_child_is_created(self, executor):
        """New child → Document created and added to session."""
        state = FakeState()
        parent_id = uuid4()
        existing_children = {}

        spec = {
            "identifier": "beta",
            "doc_type_id": "work_package",
            "title": "New WP",
            "content": {"data": "fresh"},
        }

        result = await executor._upsert_child_document(
            spec, existing_children, state, parent_id,
        )

        assert result == "created"
        executor._db_session.add.assert_called_once()
        created_doc = executor._db_session.add.call_args[0][0]
        assert created_doc.title == "New WP"
        assert created_doc.instance_id == "beta"

    @pytest.mark.asyncio
    async def test_missing_identifier_returns_skipped(self, executor):
        """Spec without identifier → skipped."""
        state = FakeState()
        parent_id = uuid4()

        spec = {
            "identifier": "",
            "doc_type_id": "work_package",
            "title": "No ID",
            "content": {},
        }

        result = await executor._upsert_child_document(
            spec, {}, state, parent_id,
        )

        assert result == "skipped"
        executor._db_session.add.assert_not_called()


# ===================================================================
# 2. _mark_stale_children
# ===================================================================

class TestMarkStaleChildren:
    def test_child_not_in_spawned_ids_marked_stale(self, executor):
        """Children not in spawned set are marked stale with is_latest=False."""
        doc_alpha = FakeDocument("alpha")
        doc_beta = FakeDocument("beta")

        existing = {"alpha": doc_alpha, "beta": doc_beta}
        spawned = {"alpha"}  # beta is removed

        count = executor._mark_stale_children(existing, spawned)

        assert count == 1
        assert doc_beta.is_latest is False
        assert doc_beta.lifecycle_state == "stale"
        # alpha untouched
        assert doc_alpha.is_latest is True
        assert doc_alpha.lifecycle_state == "complete"

    def test_all_children_in_spawned_ids_no_changes(self, executor):
        """All children still in spec → no stale marks, returns 0."""
        doc_alpha = FakeDocument("alpha")
        doc_beta = FakeDocument("beta")

        existing = {"alpha": doc_alpha, "beta": doc_beta}
        spawned = {"alpha", "beta"}

        count = executor._mark_stale_children(existing, spawned)

        assert count == 0
        assert doc_alpha.is_latest is True
        assert doc_beta.is_latest is True
