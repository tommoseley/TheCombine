"""
Tier-1 tests for fanout_service.py.

Tests EpicFeatureFanoutService and FeatureStoryFanoutService
with mocked internal methods (DB + PlanExecutor).
Pure in-memory — no real DB, no real LLM calls.

WS-BCP-005.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.domain.services.fanout_service import (
    EpicFeatureFanoutService,
    FeatureStoryFanoutService,
    _compute_structural_hash,
    _extract_scope_summary,
    _compute_source_hash_for_features,
)


# ---------------------------------------------------------------------------
# Fixtures: minimal backlog item builders
# ---------------------------------------------------------------------------

def epic(id="E001", title="Epic One", summary="The first epic", scope=None):
    return {
        "schema_version": "1.0.0",
        "id": id,
        "level": "EPIC",
        "title": title,
        "summary": summary,
        "priority_score": 100,
        "depends_on": [],
        "parent_id": None,
        "details": {
            "scope": scope or ["Core platform functionality"],
            "out_of_scope": ["Mobile apps"],
            "success_signals": ["System operational"],
            "major_risks": ["Technical complexity"],
        },
    }


def feature(id="F001", parent_id="E001", title="Feature One", summary="First feature"):
    return {
        "schema_version": "1.0.0",
        "id": id,
        "level": "FEATURE",
        "title": title,
        "summary": summary,
        "priority_score": 80,
        "depends_on": [],
        "parent_id": parent_id,
        "details": {
            "user_value": "Enables core workflow",
            "primary_flows": ["Create item", "View item"],
            "acceptance_criteria_outline": ["Items can be created"],
            "data_touched": ["items"],
            "nfr_notes": ["< 200ms response time"],
        },
    }


def story(id="S001", parent_id="F001", title="Story One", summary="First story"):
    return {
        "schema_version": "1.0.0",
        "id": id,
        "level": "STORY",
        "title": title,
        "summary": summary,
        "priority_score": 60,
        "depends_on": [],
        "parent_id": parent_id,
        "details": {
            "acceptance_criteria": ["Given X, When Y, Then Z"],
            "test_notes": ["Unit test the handler"],
            "edge_cases": ["Empty input"],
        },
    }


PROJECT_ID = "00000000-0000-0000-0000-000000000001"


# ---------------------------------------------------------------------------
# Service factories
# ---------------------------------------------------------------------------

def make_feature_fanout(
    epic_item=None,
    all_epics=None,
    existing_features=None,
    intent_summary=None,
    dcw_outcome="stabilized",
    produced_items=None,
):
    """Create an EpicFeatureFanoutService with mocked internals."""
    svc = EpicFeatureFanoutService(
        db_session=MagicMock(),
        plan_executor=MagicMock(),
    )

    svc._load_backlog_item = AsyncMock(return_value=epic_item)
    svc._load_backlog_items_by_level = AsyncMock(return_value=all_epics or [])
    svc._load_backlog_items_by_parent = AsyncMock(return_value=existing_features or [])
    svc._load_intent_summary = AsyncMock(return_value=intent_summary or {"raw_intent": "Build an app"})
    svc._load_architecture_summary = AsyncMock(return_value=None)

    svc._run_dcw = AsyncMock(return_value={
        "terminal_outcome": dcw_outcome,
        "execution_id": "exec-test123",
        "document_id": "dcw-doc-id" if dcw_outcome == "stabilized" else None,
    })

    # Default: produced items from DCW
    if produced_items is None and dcw_outcome == "stabilized":
        produced_items = [feature("F001"), feature("F002")]
    svc._load_latest_document = AsyncMock(return_value={
        "items": produced_items,
    } if produced_items else None)

    return svc


def make_story_fanout(
    epic_item=None,
    target_features=None,
    existing_stories=None,
    intent_summary=None,
    dcw_outcome="stabilized",
    produced_items=None,
):
    """Create a FeatureStoryFanoutService with mocked internals."""
    svc = FeatureStoryFanoutService(
        db_session=MagicMock(),
        plan_executor=MagicMock(),
    )

    # _load_backlog_item called for epic_id and optionally feature_id
    async def mock_load_item(project_id, item_id):
        if item_id and item_id.startswith("E"):
            return epic_item
        # Return the matching feature from target_features
        if target_features:
            for f in target_features:
                if f["id"] == item_id:
                    return f
        return None

    svc._load_backlog_item = AsyncMock(side_effect=mock_load_item)
    svc._load_backlog_items_by_parent = AsyncMock(return_value=existing_stories or [])
    svc._load_intent_summary = AsyncMock(return_value=intent_summary or {"raw_intent": "Build an app"})
    svc._load_architecture_summary = AsyncMock(return_value=None)

    svc._run_dcw = AsyncMock(return_value={
        "terminal_outcome": dcw_outcome,
        "execution_id": "exec-test456",
        "document_id": "dcw-doc-id" if dcw_outcome == "stabilized" else None,
    })

    if produced_items is None and dcw_outcome == "stabilized":
        produced_items = [story("S001"), story("S002")]
    svc._load_latest_document = AsyncMock(return_value={
        "items": produced_items,
    } if produced_items else None)

    return svc


# ===========================================================================
# EpicFeatureFanoutService Tests
# ===========================================================================

class TestEpicFeatureFanoutHappyPath:

    @pytest.mark.asyncio
    async def test_first_run_all_adds(self):
        """First run with no existing features — all items are adds."""
        svc = make_feature_fanout(
            epic_item=epic(),
            all_epics=[epic(), epic("E002", title="Epic Two")],
            existing_features=[],
            produced_items=[feature("F001"), feature("F002")],
        )

        result = await svc.run(PROJECT_ID, "E001")

        assert result.status == "completed"
        assert len(result.items) == 2
        assert result.reconciliation is not None
        assert len(result.reconciliation.adds) == 2
        assert len(result.reconciliation.keeps) == 0
        assert len(result.reconciliation.drops) == 0
        assert not result.has_drops

    @pytest.mark.asyncio
    async def test_re_run_all_keeps(self):
        """Re-run with identical IDs — all items are keeps."""
        existing = [feature("F001"), feature("F002")]
        svc = make_feature_fanout(
            epic_item=epic(),
            existing_features=existing,
            produced_items=[feature("F001"), feature("F002")],
        )

        result = await svc.run(PROJECT_ID, "E001")

        assert result.status == "completed"
        assert len(result.reconciliation.keeps) == 2
        assert len(result.reconciliation.adds) == 0
        assert len(result.reconciliation.drops) == 0

    @pytest.mark.asyncio
    async def test_re_run_with_drops_needs_confirmation(self):
        """Re-run where some items are dropped — status is needs_confirmation."""
        existing = [feature("F001"), feature("F002"), feature("F003")]
        svc = make_feature_fanout(
            epic_item=epic(),
            existing_features=existing,
            produced_items=[feature("F002"), feature("F004")],
        )

        result = await svc.run(PROJECT_ID, "E001")

        assert result.status == "needs_confirmation"
        assert result.has_drops
        assert len(result.reconciliation.keeps) == 1  # F002
        assert len(result.reconciliation.adds) == 1   # F004
        assert len(result.reconciliation.drops) == 2   # F001, F003

    @pytest.mark.asyncio
    async def test_source_hash_populated(self):
        """Result includes source_hash for staleness detection."""
        svc = make_feature_fanout(
            epic_item=epic(),
            produced_items=[feature("F001")],
        )

        result = await svc.run(PROJECT_ID, "E001")

        assert result.source_hash is not None
        assert len(result.source_hash) == 64

    @pytest.mark.asyncio
    async def test_run_id_format(self):
        """Run IDs follow the run-{hex} format."""
        svc = make_feature_fanout(
            epic_item=epic(),
            produced_items=[feature("F001")],
        )

        result = await svc.run(PROJECT_ID, "E001")

        assert result.run_id.startswith("run-")
        assert len(result.run_id) == 16


class TestEpicFeatureFanoutFailures:

    @pytest.mark.asyncio
    async def test_epic_not_found(self):
        """Fails immediately if epic doesn't exist."""
        svc = make_feature_fanout(epic_item=None)

        result = await svc.run(PROJECT_ID, "E999")

        assert result.status == "failed"
        assert result.errors["error"] == "epic_not_found"

    @pytest.mark.asyncio
    async def test_dcw_failure(self):
        """Fails if the feature_set_generator DCW fails."""
        svc = make_feature_fanout(
            epic_item=epic(),
            dcw_outcome="blocked",
        )

        result = await svc.run(PROJECT_ID, "E001")

        assert result.status == "failed"
        assert result.errors["error"] == "generation_failed"
        assert result.execution_id == "exec-test123"

    @pytest.mark.asyncio
    async def test_no_items_produced(self):
        """Fails if DCW produces no items."""
        svc = make_feature_fanout(
            epic_item=epic(),
            dcw_outcome="stabilized",
            produced_items=None,
        )
        svc._load_latest_document = AsyncMock(return_value=None)

        result = await svc.run(PROJECT_ID, "E001")

        assert result.status == "failed"
        assert result.errors["error"] == "no_items_produced"

    @pytest.mark.asyncio
    async def test_validation_failure(self):
        """Fails if produced features have invalid dependencies."""
        bad_feature = feature("F001")
        bad_feature["depends_on"] = ["X999"]  # Non-existent
        svc = make_feature_fanout(
            epic_item=epic(),
            produced_items=[bad_feature],
        )

        result = await svc.run(PROJECT_ID, "E001")

        assert result.status == "failed"
        assert result.errors["error"] == "validation_failed"
        assert result.validation_errors is not None
        assert len(result.validation_errors["dependency_errors"]) >= 1


class TestEpicFeatureFanoutContext:

    @pytest.mark.asyncio
    async def test_sibling_boundary_summary_excludes_target(self):
        """Sibling summary should not include the target epic."""
        e1 = epic("E001", title="First")
        e2 = epic("E002", title="Second")
        svc = make_feature_fanout(
            epic_item=e1,
            all_epics=[e1, e2],
            produced_items=[feature("F001")],
        )

        await svc.run(PROJECT_ID, "E001")

        # Check that _run_dcw was called with sibling summary
        call_args = svc._run_dcw.call_args
        input_docs = call_args.kwargs.get("input_documents") or call_args[1].get("input_documents")
        sibling_summary = input_docs["sibling_epic_boundary_summary"]
        sibling_ids = [s["epic_id"] for s in sibling_summary]
        assert "E001" not in sibling_ids
        assert "E002" in sibling_ids

    @pytest.mark.asyncio
    async def test_dcw_receives_epic_as_input(self):
        """DCW input_documents should include the target epic."""
        e1 = epic("E001")
        svc = make_feature_fanout(
            epic_item=e1,
            produced_items=[feature("F001")],
        )

        await svc.run(PROJECT_ID, "E001")

        call_args = svc._run_dcw.call_args
        input_docs = call_args.kwargs.get("input_documents") or call_args[1].get("input_documents")
        assert input_docs["epic_backlog_item"]["id"] == "E001"


# ===========================================================================
# FeatureStoryFanoutService Tests
# ===========================================================================

class TestFeatureStoryFanoutHappyPath:

    @pytest.mark.asyncio
    async def test_per_feature_first_run(self):
        """Generate stories for a single feature — first run, all adds."""
        svc = make_story_fanout(
            epic_item=epic(),
            target_features=[feature("F001")],
            existing_stories=[],
            produced_items=[story("S001"), story("S002")],
        )

        result = await svc.run(PROJECT_ID, "E001", feature_id="F001")

        assert result.status == "completed"
        assert result.source_id == "F001"
        assert result.source_type == "feature"
        assert len(result.items) == 2
        assert len(result.reconciliation.adds) == 2
        assert len(result.reconciliation.keeps) == 0

    @pytest.mark.asyncio
    async def test_per_epic_first_run(self):
        """Generate stories for all features under an epic — first run."""
        features = [feature("F001"), feature("F002")]
        svc = make_story_fanout(
            epic_item=epic(),
            target_features=features,
            existing_stories=[],
            produced_items=[story("S001", parent_id="F001"), story("S002", parent_id="F002")],
        )
        # When no feature_id, load features by parent
        svc._load_backlog_items_by_parent = AsyncMock(return_value=[])

        # Override: first call returns features, subsequent calls return empty stories
        call_count = 0
        async def mock_load_by_parent(project_id, parent_id):
            nonlocal call_count
            call_count += 1
            if parent_id == "E001":
                return features
            return []  # No existing stories
        svc._load_backlog_items_by_parent = AsyncMock(side_effect=mock_load_by_parent)

        result = await svc.run(PROJECT_ID, "E001")

        assert result.status == "completed"
        assert result.source_id == "E001"
        assert result.source_type == "epic"

    @pytest.mark.asyncio
    async def test_re_run_with_drops(self):
        """Re-run where stories are dropped — needs confirmation."""
        existing = [story("S001"), story("S002"), story("S003")]
        svc = make_story_fanout(
            epic_item=epic(),
            target_features=[feature("F001")],
            existing_stories=existing,
            produced_items=[story("S002"), story("S004")],
        )
        # Override: return existing stories for F001, not empty
        async def mock_load_by_parent(project_id, parent_id):
            if parent_id == "F001":
                return existing
            return []
        svc._load_backlog_items_by_parent = AsyncMock(side_effect=mock_load_by_parent)

        result = await svc.run(PROJECT_ID, "E001", feature_id="F001")

        assert result.status == "needs_confirmation"
        assert result.has_drops
        assert len(result.reconciliation.drops) == 2  # S001, S003

    @pytest.mark.asyncio
    async def test_source_hash_for_single_feature(self):
        """Source hash computed from target feature(s)."""
        svc = make_story_fanout(
            epic_item=epic(),
            target_features=[feature("F001")],
            produced_items=[story("S001")],
        )

        result = await svc.run(PROJECT_ID, "E001", feature_id="F001")

        assert result.source_hash is not None
        assert len(result.source_hash) == 64


class TestFeatureStoryFanoutFailures:

    @pytest.mark.asyncio
    async def test_epic_not_found(self):
        """Fails if parent epic doesn't exist."""
        svc = make_story_fanout(epic_item=None)

        result = await svc.run(PROJECT_ID, "E999", feature_id="F001")

        assert result.status == "failed"
        assert result.errors["error"] == "epic_not_found"

    @pytest.mark.asyncio
    async def test_feature_not_found(self):
        """Fails if specific feature doesn't exist."""
        svc = make_story_fanout(
            epic_item=epic(),
            target_features=[],
        )

        result = await svc.run(PROJECT_ID, "E001", feature_id="F999")

        assert result.status == "failed"
        assert result.errors["error"] == "feature_not_found"

    @pytest.mark.asyncio
    async def test_no_features_for_epic(self):
        """Fails if epic has no features (per-epic mode)."""
        svc = make_story_fanout(
            epic_item=epic(),
            target_features=[],
        )
        svc._load_backlog_items_by_parent = AsyncMock(return_value=[])

        result = await svc.run(PROJECT_ID, "E001")

        assert result.status == "failed"
        assert result.errors["error"] == "no_features"

    @pytest.mark.asyncio
    async def test_dcw_failure(self):
        """Fails if the story_set_generator DCW fails."""
        svc = make_story_fanout(
            epic_item=epic(),
            target_features=[feature("F001")],
            dcw_outcome="blocked",
        )

        result = await svc.run(PROJECT_ID, "E001", feature_id="F001")

        assert result.status == "failed"
        assert result.errors["error"] == "generation_failed"

    @pytest.mark.asyncio
    async def test_validation_failure(self):
        """Fails if produced stories have invalid dependencies."""
        bad_story = story("S001")
        bad_story["depends_on"] = ["X999"]
        svc = make_story_fanout(
            epic_item=epic(),
            target_features=[feature("F001")],
            produced_items=[bad_story],
        )

        result = await svc.run(PROJECT_ID, "E001", feature_id="F001")

        assert result.status == "failed"
        assert result.errors["error"] == "validation_failed"


class TestFeatureStoryFanoutContext:

    @pytest.mark.asyncio
    async def test_existing_story_titles_passed_on_rerun(self):
        """On re-run, existing story titles are passed to DCW."""
        existing = [story("S001", title="Auth setup"), story("S002", title="Login flow")]
        svc = make_story_fanout(
            epic_item=epic(),
            target_features=[feature("F001")],
            existing_stories=existing,
            produced_items=[story("S001"), story("S003")],
        )
        async def mock_load_by_parent(project_id, parent_id):
            if parent_id == "F001":
                return existing
            return []
        svc._load_backlog_items_by_parent = AsyncMock(side_effect=mock_load_by_parent)

        await svc.run(PROJECT_ID, "E001", feature_id="F001")

        call_args = svc._run_dcw.call_args
        input_docs = call_args.kwargs.get("input_documents") or call_args[1].get("input_documents")
        assert "existing_sibling_story_titles" in input_docs
        titles = input_docs["existing_sibling_story_titles"]
        assert len(titles) == 2
        assert titles[0]["id"] == "S001"

    @pytest.mark.asyncio
    async def test_parent_epic_summary_passed(self):
        """DCW receives parent epic summary."""
        e1 = epic("E001", title="Backend API")
        svc = make_story_fanout(
            epic_item=e1,
            target_features=[feature("F001")],
            produced_items=[story("S001")],
        )

        await svc.run(PROJECT_ID, "E001", feature_id="F001")

        call_args = svc._run_dcw.call_args
        input_docs = call_args.kwargs.get("input_documents") or call_args[1].get("input_documents")
        assert input_docs["parent_epic_summary"]["id"] == "E001"
        assert input_docs["parent_epic_summary"]["title"] == "Backend API"


# ===========================================================================
# Utility Function Tests
# ===========================================================================

class TestStructuralHash:

    def test_same_item_same_hash(self):
        h1 = _compute_structural_hash(feature("F001"))
        h2 = _compute_structural_hash(feature("F001"))
        assert h1 == h2

    def test_different_id_different_hash(self):
        h1 = _compute_structural_hash(feature("F001"))
        h2 = _compute_structural_hash(feature("F002"))
        assert h1 != h2

    def test_details_change_same_hash(self):
        """Hash boundary invariant: details are excluded."""
        f1 = feature("F001")
        f2 = feature("F001")
        f2["details"]["user_value"] = "Completely different value"
        assert _compute_structural_hash(f1) == _compute_structural_hash(f2)

    def test_title_change_same_hash(self):
        """Hash boundary invariant: title is excluded."""
        f1 = feature("F001")
        f2 = feature("F001")
        f2["title"] = "Totally different title"
        assert _compute_structural_hash(f1) == _compute_structural_hash(f2)

    def test_priority_change_different_hash(self):
        """Priority is a base field — changes the hash."""
        f1 = feature("F001")
        f2 = feature("F001")
        f2["priority_score"] = 99
        assert _compute_structural_hash(f1) != _compute_structural_hash(f2)

    def test_depends_on_order_irrelevant(self):
        """depends_on is sorted before hashing."""
        f1 = feature("F001")
        f1["depends_on"] = ["F002", "F003"]
        f2 = feature("F001")
        f2["depends_on"] = ["F003", "F002"]
        assert _compute_structural_hash(f1) == _compute_structural_hash(f2)

    def test_hash_is_64_hex(self):
        h = _compute_structural_hash(feature("F001"))
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


class TestExtractScopeSummary:

    def test_single_scope_item(self):
        e = epic("E001", scope=["Authentication system"])
        assert _extract_scope_summary(e) == "Authentication system"

    def test_multiple_scope_items(self):
        e = epic("E001", scope=["Auth system", "User management", "Roles"])
        result = _extract_scope_summary(e)
        assert "Auth system" in result
        assert "User management" in result

    def test_no_scope_falls_back_to_summary(self):
        e = epic("E001")
        e["details"]["scope"] = []
        assert _extract_scope_summary(e) == "The first epic"

    def test_no_details(self):
        e = {"id": "E001", "summary": "Fallback", "details": {}}
        assert _extract_scope_summary(e) == "Fallback"


class TestComputeSourceHashForFeatures:

    def test_single_feature_deterministic(self):
        h1 = _compute_source_hash_for_features([feature("F001")])
        h2 = _compute_source_hash_for_features([feature("F001")])
        assert h1 == h2

    def test_order_irrelevant(self):
        """Hash should be the same regardless of feature order."""
        h1 = _compute_source_hash_for_features([feature("F001"), feature("F002")])
        h2 = _compute_source_hash_for_features([feature("F002"), feature("F001")])
        assert h1 == h2

    def test_different_features_different_hash(self):
        h1 = _compute_source_hash_for_features([feature("F001")])
        h2 = _compute_source_hash_for_features([feature("F002")])
        assert h1 != h2
