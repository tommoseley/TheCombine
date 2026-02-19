"""Tests for PlanExecutor._spawn_child_documents idempotency and drift."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


# Minimal DocumentWorkflowState stub
class FakeState:
    def __init__(self, document_type="implementation_plan", project_id=None, execution_id=None):
        self.document_type = document_type
        self.project_id = project_id or str(uuid4())
        self.execution_id = execution_id or "exec-test-123"
        self.context_state = {}
        self.workflow_id = "implementation_plan"


# Minimal Document stub
class FakeDocument:
    def __init__(self, epic_id, version=1, is_latest=True, lifecycle_state="complete"):
        self.id = uuid4()
        self.content = {"epic_id": epic_id}
        self.title = f"Epic: {epic_id}"
        self.version = version
        self.is_latest = is_latest
        self.lifecycle_state = lifecycle_state
        self.doc_type_id = "epic"
        self.instance_id = epic_id

    def update_revision_hash(self):
        pass

    def mark_stale(self):
        self.lifecycle_state = "stale"


def _make_child_specs(epic_ids):
    """Build child specs like the handler would produce."""
    return [
        {
            "doc_type_id": "epic",
            "title": f"Epic: {eid}",
            "content": {
                "epic_id": eid,
                "name": eid.replace("_", " ").title(),
                "_lineage": {
                    "parent_document_type": "implementation_plan",
                    "parent_execution_id": None,
                    "source_candidate_ids": [],
                    "transformation": "kept",
                    "transformation_notes": "",
                },
            },
            "identifier": eid,
        }
        for eid in epic_ids
    ]


@pytest.fixture
def executor():
    """Create a minimal object with _spawn_child_documents bound to it.

    Avoids importing PlanExecutor directly (circular import).
    Instead, imports the module and binds just the method we need.
    """
    import importlib
    import sys

    # Import the module without triggering __init__.py circular imports
    # by loading plan_executor.py directly
    spec = importlib.util.spec_from_file_location(
        "plan_executor_test",
        "app/domain/workflow/plan_executor.py",
        submodule_search_locations=[],
    )
    mod = importlib.util.module_from_spec(spec)

    # Provide the dependencies the module needs at import time
    # Mock out the circular import: publish_event
    mock_production = MagicMock()
    mock_production.publish_event = AsyncMock()
    sys.modules.setdefault("app.api.v1.routers.production", mock_production)

    spec.loader.exec_module(mod)
    PlanExecutor = mod.PlanExecutor

    db = AsyncMock()
    persistence = AsyncMock()
    pe = PlanExecutor.__new__(PlanExecutor)
    pe._db_session = db
    pe._persistence = persistence
    return pe


class TestSpawnChildDocuments:
    @pytest.mark.asyncio
    async def test_creates_new_children(self, executor):
        """First run: creates children, no existing docs."""
        state = FakeState()
        parent_id = uuid4()
        specs = _make_child_specs(["alpha", "beta"])

        # No existing children
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        executor._db_session.execute = AsyncMock(return_value=mock_result)

        with patch("app.domain.handlers.registry.handler_exists", return_value=True), \
             patch("app.domain.handlers.registry.get_handler") as mock_handler:
            mock_handler.return_value.get_child_documents.return_value = specs

            await executor._spawn_child_documents(
                state, {}, parent_id, "Test Plan", execution_id="exec-001"
            )

        # Should have called db_session.add twice (2 new children)
        assert executor._db_session.add.call_count == 2
        await_commit = executor._db_session.commit
        assert await_commit.called

    @pytest.mark.asyncio
    async def test_injects_execution_id_into_lineage(self, executor):
        """Execution ID is injected into child lineage metadata."""
        state = FakeState()
        parent_id = uuid4()
        specs = _make_child_specs(["alpha"])

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        executor._db_session.execute = AsyncMock(return_value=mock_result)

        with patch("app.domain.handlers.registry.handler_exists", return_value=True), \
             patch("app.domain.handlers.registry.get_handler") as mock_handler:
            mock_handler.return_value.get_child_documents.return_value = specs

            await executor._spawn_child_documents(
                state, {}, parent_id, "Test Plan", execution_id="exec-injected"
            )

        # Check the content passed to Document constructor
        add_call = executor._db_session.add.call_args
        created_doc = add_call[0][0]
        assert created_doc.content["_lineage"]["parent_execution_id"] == "exec-injected"

    @pytest.mark.asyncio
    async def test_updates_existing_child_instead_of_duplicating(self, executor):
        """Idempotency: existing child is updated, not duplicated."""
        state = FakeState()
        parent_id = uuid4()

        existing_doc = FakeDocument("alpha", version=1)
        specs = _make_child_specs(["alpha"])
        specs[0]["content"]["intent"] = "Updated intent"

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [existing_doc]
        executor._db_session.execute = AsyncMock(return_value=mock_result)

        with patch("app.domain.handlers.registry.handler_exists", return_value=True), \
             patch("app.domain.handlers.registry.get_handler") as mock_handler:
            mock_handler.return_value.get_child_documents.return_value = specs

            await executor._spawn_child_documents(
                state, {}, parent_id, "Test Plan", execution_id="exec-002"
            )

        # Should NOT have called add (update in place)
        assert executor._db_session.add.call_count == 0
        # Existing doc should be updated
        assert existing_doc.content["intent"] == "Updated intent"
        assert existing_doc.version == 2
        assert existing_doc.title == "Epic: alpha"

    @pytest.mark.asyncio
    async def test_supersedes_removed_children(self, executor):
        """Drift: children no longer in spec are marked stale."""
        state = FakeState()
        parent_id = uuid4()

        # Existing has alpha and beta; new spec only has alpha
        existing_alpha = FakeDocument("alpha")
        existing_beta = FakeDocument("beta")
        specs = _make_child_specs(["alpha"])

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [existing_alpha, existing_beta]
        executor._db_session.execute = AsyncMock(return_value=mock_result)

        with patch("app.domain.handlers.registry.handler_exists", return_value=True), \
             patch("app.domain.handlers.registry.get_handler") as mock_handler:
            mock_handler.return_value.get_child_documents.return_value = specs

            await executor._spawn_child_documents(
                state, {}, parent_id, "Test Plan", execution_id="exec-003"
            )

        # Beta should be superseded
        assert existing_beta.is_latest is False
        assert existing_beta.lifecycle_state == "stale"
        # Alpha should still be current
        assert existing_alpha.is_latest is True

    @pytest.mark.asyncio
    async def test_no_handler_does_nothing(self, executor):
        """No handler registered = no work."""
        state = FakeState(document_type="unknown_type")
        parent_id = uuid4()

        with patch("app.domain.handlers.registry.handler_exists", return_value=False):
            await executor._spawn_child_documents(
                state, {}, parent_id, "Test Plan"
            )

        executor._db_session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_specs_does_nothing(self, executor):
        """Handler returns no children = no DB work."""
        state = FakeState()
        parent_id = uuid4()

        with patch("app.domain.handlers.registry.handler_exists", return_value=True), \
             patch("app.domain.handlers.registry.get_handler") as mock_handler:
            mock_handler.return_value.get_child_documents.return_value = []

            await executor._spawn_child_documents(
                state, {}, parent_id, "Test Plan"
            )

        executor._db_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_mixed_create_update_supersede(self, executor):
        """All three operations in one run."""
        state = FakeState()
        parent_id = uuid4()

        # Existing: alpha (stays), beta (removed), no gamma yet
        existing_alpha = FakeDocument("alpha")
        existing_beta = FakeDocument("beta")

        # New spec: alpha (update), gamma (create) - beta removed
        specs = _make_child_specs(["alpha", "gamma"])

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [existing_alpha, existing_beta]
        executor._db_session.execute = AsyncMock(return_value=mock_result)

        with patch("app.domain.handlers.registry.handler_exists", return_value=True), \
             patch("app.domain.handlers.registry.get_handler") as mock_handler:
            mock_handler.return_value.get_child_documents.return_value = specs

            await executor._spawn_child_documents(
                state, {}, parent_id, "Test Plan", execution_id="exec-004"
            )

        # alpha: updated (version bumped)
        assert existing_alpha.version == 2
        # beta: superseded
        assert existing_beta.is_latest is False
        assert existing_beta.lifecycle_state == "stale"
        # gamma: created (add called once)
        assert executor._db_session.add.call_count == 1
        # commit called
        assert executor._db_session.commit.called

    @pytest.mark.asyncio
    async def test_emits_children_updated_sse_event(self, executor):
        """SSE event is published after spawning children."""
        state = FakeState()
        parent_id = uuid4()

        existing_alpha = FakeDocument("alpha")
        specs = _make_child_specs(["alpha", "gamma"])

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [existing_alpha]
        executor._db_session.execute = AsyncMock(return_value=mock_result)

        # Patch publish_event in the actual module globals loaded by the fixture
        mod_globals = type(executor)._spawn_child_documents.__globals__
        original_publish = mod_globals.get("publish_event")
        mock_publish = AsyncMock()
        mod_globals["publish_event"] = mock_publish

        try:
            with patch("app.domain.handlers.registry.handler_exists", return_value=True), \
                 patch("app.domain.handlers.registry.get_handler") as mock_handler:
                mock_handler.return_value.get_child_documents.return_value = specs

                await executor._spawn_child_documents(
                    state, {}, parent_id, "Test Plan", execution_id="exec-sse"
                )
        finally:
            mod_globals["publish_event"] = original_publish

        mock_publish.assert_called_once()
        call_args = mock_publish.call_args
        assert call_args[0][0] == state.project_id
        assert call_args[0][1] == "children_updated"
        event_data = call_args[0][2]
        assert event_data["parent_document_type"] == "implementation_plan"
        assert event_data["child_doc_type"] == "epic"
        assert "gamma" in event_data["created"]
        assert "alpha" in event_data["updated"]
        assert event_data["superseded"] == []

    @pytest.mark.asyncio
    async def test_no_sse_event_when_nothing_changes(self, executor):
        """No SSE event when handler returns empty specs."""
        mod_globals = type(executor)._spawn_child_documents.__globals__
        original_publish = mod_globals.get("publish_event")
        mock_publish = AsyncMock()
        mod_globals["publish_event"] = mock_publish

        state = FakeState()
        parent_id = uuid4()

        try:
            with patch("app.domain.handlers.registry.handler_exists", return_value=True), \
                 patch("app.domain.handlers.registry.get_handler") as mock_handler:
                mock_handler.return_value.get_child_documents.return_value = []

                await executor._spawn_child_documents(
                    state, {}, parent_id, "Test Plan"
                )
        finally:
            mod_globals["publish_event"] = original_publish

        mock_publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_unwraps_raw_envelope_before_extraction(self, executor):
        """Raw envelope content is unwrapped before passing to handler."""
        import json as _json

        state = FakeState()
        parent_id = uuid4()

        # Content in raw envelope format (as stored by LLM handler)
        inner_content = {
            "epics": [
                {"epic_id": "alpha", "name": "Alpha Epic"}
            ]
        }
        raw_envelope = {
            "raw": True,
            "content": f"```json\n{_json.dumps(inner_content)}\n```",
            "meta": {},
            "type": "implementation_plan",
        }

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        executor._db_session.execute = AsyncMock(return_value=mock_result)

        with patch("app.domain.handlers.registry.handler_exists", return_value=True), \
             patch("app.domain.handlers.registry.get_handler") as mock_handler:
            mock_handler.return_value.get_child_documents.return_value = _make_child_specs(["alpha"])

            await executor._spawn_child_documents(
                state, raw_envelope, parent_id, "Test Plan"
            )

        # Handler should have received the unwrapped content, not the envelope
        call_args = mock_handler.return_value.get_child_documents.call_args
        received_data = call_args[0][0]
        assert "epics" in received_data
        assert received_data["epics"][0]["epic_id"] == "alpha"
        assert "raw" not in received_data
