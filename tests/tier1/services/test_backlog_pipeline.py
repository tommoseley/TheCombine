"""
Tier-1 tests for backlog_pipeline.py.

Tests the pipeline service with mocked internal methods (DB + PlanExecutor).
Pure in-memory — no real DB, no real LLM calls.

WS-BCP-004.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.domain.services.backlog_pipeline import (
    BacklogPipelineService,
    PipelineResult,
    compute_intent_hash,
    compute_plan_hash,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_intent_content():
    return {
        "raw_intent": "Build a task management app",
        "constraints": None,
        "success_criteria": None,
        "context": None,
        "schema_version": "1.0.0",
    }


def make_backlog_items():
    return [
        {
            "schema_version": "1.0.0",
            "id": "E001", "level": "EPIC", "title": "Core Platform",
            "summary": "Foundation", "priority_score": 100,
            "depends_on": [], "parent_id": None,
        },
        {
            "schema_version": "1.0.0",
            "id": "F001", "level": "FEATURE", "title": "Task CRUD",
            "summary": "Basic operations", "priority_score": 80,
            "depends_on": ["E001"], "parent_id": "E001",
        },
        {
            "schema_version": "1.0.0",
            "id": "S001", "level": "STORY", "title": "Create task",
            "summary": "As a user...", "priority_score": 60,
            "depends_on": ["F001"], "parent_id": "F001",
        },
    ]


def make_backlog_content():
    return {
        "intent_id": "test-intent-id",
        "items": make_backlog_items(),
    }


def make_service(mock_executor=None, intent_content=None, backlog_content=None):
    """Create a BacklogPipelineService with mocked internal DB methods.

    Instead of mocking SQLAlchemy queries, we patch the service's
    private methods directly. This avoids fragile query-string matching.

    The _run_dcw method is also mocked since it contains raw DB queries
    for document ID lookup. We test pipeline orchestration, not DCW internals.
    """
    svc = BacklogPipelineService(db_session=MagicMock(), plan_executor=mock_executor or MagicMock())

    # Patch internal methods
    svc._load_intent = AsyncMock(return_value=intent_content)
    svc._load_latest_document = AsyncMock(return_value=backlog_content)
    svc._find_execution_plan_by_hash = AsyncMock(return_value=None)
    svc._persist_document = AsyncMock(return_value="new-doc-id")
    svc._persist_pipeline_run = AsyncMock(return_value="run-doc-id")

    # Mock _run_dcw: returns stabilized by default
    svc._run_dcw = AsyncMock(return_value={
        "terminal_outcome": "stabilized",
        "execution_id": "exec-test123",
        "document_id": "dcw-doc-id",
    })

    return svc


# ===========================================================================
# Hash Function Tests
# ===========================================================================

class TestComputeIntentHash:

    def test_same_content_same_hash(self):
        content = make_intent_content()
        h1 = compute_intent_hash(content)
        h2 = compute_intent_hash(content)
        assert h1 == h2

    def test_different_content_different_hash(self):
        c1 = make_intent_content()
        c2 = make_intent_content()
        c2["raw_intent"] = "Something completely different"
        assert compute_intent_hash(c1) != compute_intent_hash(c2)

    def test_hash_is_64_hex(self):
        h = compute_intent_hash(make_intent_content())
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_key_order_irrelevant(self):
        """JSON is sorted, so key order in input dict doesn't matter."""
        c1 = {"raw_intent": "test", "constraints": None}
        c2 = {"constraints": None, "raw_intent": "test"}
        assert compute_intent_hash(c1) == compute_intent_hash(c2)


class TestComputePlanHash:

    def test_same_input_same_hash(self):
        ids = ["E001", "F001", "S001"]
        waves = [["E001"], ["F001"], ["S001"]]
        h1 = compute_plan_hash(ids, waves)
        h2 = compute_plan_hash(ids, waves)
        assert h1 == h2

    def test_different_order_different_hash(self):
        ids1 = ["E001", "F001"]
        ids2 = ["F001", "E001"]
        waves = [["E001", "F001"]]
        assert compute_plan_hash(ids1, waves) != compute_plan_hash(ids2, waves)

    def test_hash_is_64_hex(self):
        h = compute_plan_hash(["E001"], [["E001"]])
        assert len(h) == 64

    def test_deterministic(self):
        """Same inputs always produce same hash."""
        ids = ["E001", "E002", "F001"]
        waves = [["E001", "E002"], ["F001"]]
        results = [compute_plan_hash(ids, waves) for _ in range(5)]
        assert len(set(results)) == 1


# ===========================================================================
# Pipeline Service Tests
# ===========================================================================

class TestBacklogPipelineService:

    @pytest.mark.asyncio
    async def test_intent_not_found(self):
        """Pipeline fails immediately if IntentPacket doesn't exist."""
        service = make_service(intent_content=None)
        result = await service.run(
            project_id="00000000-0000-0000-0000-000000000001",
            intent_id="00000000-0000-0000-0000-000000000099",
        )
        assert result.status == "failed"
        assert result.stage_reached == "load_intent"
        assert "intent_not_found" in result.errors["error"]

    @pytest.mark.asyncio
    async def test_generation_failure(self):
        """Pipeline fails if backlog generation DCW is blocked."""
        service = make_service(
            intent_content=make_intent_content(),
            backlog_content=None,
        )
        # Override _run_dcw to return blocked
        service._run_dcw = AsyncMock(return_value={
            "terminal_outcome": "blocked",
            "execution_id": "exec-test123",
            "document_id": None,
        })
        result = await service.run(
            project_id="00000000-0000-0000-0000-000000000001",
            intent_id="00000000-0000-0000-0000-000000000099",
        )
        assert result.status == "failed"
        assert result.stage_reached == "generation"
        assert result.errors["error"] == "backlog_generation_failed"

    @pytest.mark.asyncio
    async def test_validation_failure(self):
        """Pipeline fails with structured errors if graph validation fails."""
        # Backlog with invalid dependency (X999 doesn't exist)
        bad_items = [
            {
                "schema_version": "1.0.0",
                "id": "E001", "level": "EPIC", "title": "Epic",
                "summary": "x", "priority_score": 100,
                "depends_on": ["X999"], "parent_id": None,
            },
        ]
        service = make_service(
            intent_content=make_intent_content(),
            backlog_content={"intent_id": "i1", "items": bad_items},
        )
        result = await service.run(
            project_id="00000000-0000-0000-0000-000000000001",
            intent_id="00000000-0000-0000-0000-000000000099",
        )
        assert result.status == "failed"
        assert result.stage_reached == "validation"
        assert result.errors["error"] == "graph_validation_failed"
        assert len(result.errors["dependency_errors"]) == 1
        assert result.errors["dependency_errors"][0]["error_type"] == "missing_reference"

    @pytest.mark.asyncio
    async def test_happy_path_skip_explanation(self):
        """Pipeline completes successfully with skip_explanation=True."""
        service = make_service(
            intent_content=make_intent_content(),
            backlog_content=make_backlog_content(),
        )
        result = await service.run(
            project_id="00000000-0000-0000-0000-000000000001",
            intent_id="00000000-0000-0000-0000-000000000099",
            skip_explanation=True,
        )
        assert result.status == "completed"
        assert result.stage_reached == "completed"
        assert result.backlog_hash is not None
        assert len(result.backlog_hash) == 64
        assert result.plan_id is not None
        assert result.explanation_id is None
        assert result.stages["explanation"].status == "skipped"

    @pytest.mark.asyncio
    async def test_happy_path_with_explanation(self):
        """Pipeline completes with explanation step."""
        service = make_service(
            intent_content=make_intent_content(),
            backlog_content=make_backlog_content(),
        )
        result = await service.run(
            project_id="00000000-0000-0000-0000-000000000001",
            intent_id="00000000-0000-0000-0000-000000000099",
            skip_explanation=False,
        )
        assert result.status == "completed"
        assert result.stages["generation"].status == "completed"
        assert result.stages["validation"].status == "completed"
        assert result.stages["derivation"].status == "completed"

    @pytest.mark.asyncio
    async def test_explanation_failure_doesnt_halt(self):
        """Pipeline still completes even if explanation DCW fails."""
        call_count = 0
        stabilized = {
            "terminal_outcome": "stabilized",
            "execution_id": "exec-test123",
            "document_id": "dcw-doc-id",
        }
        blocked = {
            "terminal_outcome": "blocked",
            "execution_id": "exec-test456",
            "document_id": None,
        }

        async def side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                return stabilized  # First call (backlog gen) succeeds
            return blocked  # Second call (explanation) fails

        service = make_service(
            intent_content=make_intent_content(),
            backlog_content=make_backlog_content(),
        )
        service._run_dcw = AsyncMock(side_effect=side_effect)

        result = await service.run(
            project_id="00000000-0000-0000-0000-000000000001",
            intent_id="00000000-0000-0000-0000-000000000099",
        )
        assert result.status == "completed"
        assert result.stages["explanation"].status == "failed"
        assert result.explanation_id is None

    @pytest.mark.asyncio
    async def test_replay_metadata_present(self):
        """Completed pipeline includes replay metadata with all hashes."""
        service = make_service(
            intent_content=make_intent_content(),
            backlog_content=make_backlog_content(),
        )
        result = await service.run(
            project_id="00000000-0000-0000-0000-000000000001",
            intent_id="00000000-0000-0000-0000-000000000099",
            skip_explanation=True,
        )
        meta = result.metadata
        assert "intent_hash" in meta
        assert "backlog_hash" in meta
        assert "plan_hash" in meta
        assert "generator_version" in meta
        assert len(meta["intent_hash"]) == 64
        assert len(meta["backlog_hash"]) == 64
        assert len(meta["plan_hash"]) == 64

    @pytest.mark.asyncio
    async def test_pipeline_run_document_persisted(self):
        """Pipeline persists a pipeline_run document."""
        service = make_service(
            intent_content=make_intent_content(),
            backlog_content=make_backlog_content(),
        )
        result = await service.run(
            project_id="00000000-0000-0000-0000-000000000001",
            intent_id="00000000-0000-0000-0000-000000000099",
            skip_explanation=True,
        )
        # _persist_pipeline_run should have been called
        service._persist_pipeline_run.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_run_id_format(self):
        """Run IDs follow the run-{hex} format."""
        service = make_service(
            intent_content=make_intent_content(),
            backlog_content=make_backlog_content(),
        )
        result = await service.run(
            project_id="00000000-0000-0000-0000-000000000001",
            intent_id="00000000-0000-0000-0000-000000000099",
            skip_explanation=True,
        )
        assert result.run_id.startswith("run-")
        assert len(result.run_id) == 16  # "run-" + 12 hex chars

    @pytest.mark.asyncio
    async def test_hierarchy_validation_failure(self):
        """Pipeline reports hierarchy errors in separate bucket."""
        # STORY parented to EPIC (invalid — should be FEATURE)
        bad_items = [
            {
                "schema_version": "1.0.0",
                "id": "E001", "level": "EPIC", "title": "Epic",
                "summary": "x", "priority_score": 100,
                "depends_on": [], "parent_id": None,
            },
            {
                "schema_version": "1.0.0",
                "id": "S001", "level": "STORY", "title": "Story",
                "summary": "x", "priority_score": 50,
                "depends_on": [], "parent_id": "E001",
            },
        ]
        service = make_service(
            intent_content=make_intent_content(),
            backlog_content={"intent_id": "i1", "items": bad_items},
        )
        result = await service.run(
            project_id="00000000-0000-0000-0000-000000000001",
            intent_id="00000000-0000-0000-0000-000000000099",
        )
        assert result.status == "failed"
        assert result.stage_reached == "validation"
        assert len(result.errors["hierarchy_errors"]) >= 1
        assert result.errors["hierarchy_errors"][0]["error_type"] == "invalid_level_transition"


# ===========================================================================
# Replay Invariant Tests
# ===========================================================================

class TestReplayInvariant:

    def test_same_intent_same_hash(self):
        """Same intent content always produces same hash."""
        content = make_intent_content()
        h1 = compute_intent_hash(content)
        h2 = compute_intent_hash(content)
        assert h1 == h2

    def test_derive_then_hash_deterministic(self):
        """derive_execution_plan → compute_plan_hash is stable across calls."""
        from app.domain.services.backlog_ordering import derive_execution_plan

        items = make_backlog_items()
        plan1 = derive_execution_plan(items, "i1", "r1")
        plan2 = derive_execution_plan(items, "i1", "r2")

        h1 = compute_plan_hash(plan1["ordered_backlog_ids"], plan1["waves"])
        h2 = compute_plan_hash(plan2["ordered_backlog_ids"], plan2["waves"])
        assert h1 == h2

    def test_different_run_id_same_plan_hash(self):
        """run_id is metadata — doesn't affect plan hash."""
        from app.domain.services.backlog_ordering import derive_execution_plan

        items = make_backlog_items()
        plan_a = derive_execution_plan(items, "intent-A", "run-A")
        plan_b = derive_execution_plan(items, "intent-B", "run-B")

        h_a = compute_plan_hash(plan_a["ordered_backlog_ids"], plan_a["waves"])
        h_b = compute_plan_hash(plan_b["ordered_backlog_ids"], plan_b["waves"])
        assert h_a == h_b
        assert plan_a["backlog_hash"] == plan_b["backlog_hash"]
