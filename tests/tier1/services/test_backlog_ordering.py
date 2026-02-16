"""
Tier-1 tests for backlog_ordering.py.

Pure in-memory, no DB, no LLM.
Tests order_backlog, compute_waves, compute_backlog_hash, derive_execution_plan.

WS-BCP-002.
"""

import pytest

from app.domain.services.backlog_ordering import (
    order_backlog,
    compute_waves,
    compute_backlog_hash,
    derive_execution_plan,
)


# ---------------------------------------------------------------------------
# Fixtures: reusable backlog item builders
# ---------------------------------------------------------------------------

def epic(id, depends_on=None, priority=50):
    return {
        "id": id, "level": "EPIC", "title": f"Epic {id}",
        "description": f"Description for {id}", "priority_score": priority,
        "depends_on": depends_on or [], "parent_id": None,
    }

def feature(id, parent_id, depends_on=None, priority=30):
    return {
        "id": id, "level": "FEATURE", "title": f"Feature {id}",
        "description": f"Description for {id}", "priority_score": priority,
        "depends_on": depends_on or [], "parent_id": parent_id,
    }

def story(id, parent_id, depends_on=None, priority=10):
    return {
        "id": id, "level": "STORY", "title": f"Story {id}",
        "description": f"Description for {id}", "priority_score": priority,
        "depends_on": depends_on or [], "parent_id": parent_id,
    }


# ===========================================================================
# Task 6: Topological Sort
# ===========================================================================

class TestOrderBacklog:

    def test_linear_chain(self):
        """A→B→C should produce [A, B, C]."""
        items = [
            epic("E001", priority=10),
            epic("E002", depends_on=["E001"], priority=10),
            epic("E003", depends_on=["E002"], priority=10),
        ]
        result = order_backlog(items)
        assert result == ["E001", "E002", "E003"]

    def test_priority_ordering_within_tier(self):
        """Same tier: higher priority first."""
        items = [
            epic("E001", priority=30),
            epic("E002", priority=100),
            epic("E003", priority=50),
        ]
        result = order_backlog(items)
        assert result == ["E002", "E003", "E001"]

    def test_tiebreak_by_id(self):
        """Same priority: alphabetical by ID."""
        items = [
            epic("E003", priority=50),
            epic("E001", priority=50),
            epic("E002", priority=50),
        ]
        result = order_backlog(items)
        assert result == ["E001", "E002", "E003"]

    def test_no_dependencies_sorted_by_priority(self):
        """All independent items, sorted by priority DESC then ID ASC."""
        items = [
            epic("E001", priority=10),
            feature("F001", "E001", priority=50),
            story("S001", "F001", priority=30),
        ]
        result = order_backlog(items)
        assert result == ["F001", "S001", "E001"]

    def test_diamond_dependency(self):
        """A→B, A→C, B→D, C→D."""
        items = [
            epic("E001", priority=100),
            epic("E002", depends_on=["E001"], priority=80),
            epic("E003", depends_on=["E001"], priority=60),
            epic("E004", depends_on=["E002", "E003"], priority=40),
        ]
        result = order_backlog(items)
        assert result == ["E001", "E002", "E003", "E004"]

    def test_deterministic_output(self):
        """Same input always produces same output."""
        items = [
            epic("E001", priority=50),
            epic("E002", priority=50),
            epic("E003", depends_on=["E001"], priority=50),
        ]
        result1 = order_backlog(items)
        result2 = order_backlog(items)
        assert result1 == result2

    def test_single_item(self):
        items = [epic("E001")]
        result = order_backlog(items)
        assert result == ["E001"]

    def test_mixed_levels_with_deps(self):
        """Cross-level dependencies are respected."""
        items = [
            epic("E001", priority=100),
            feature("F001", "E001", depends_on=["E001"], priority=50),
            story("S001", "F001", depends_on=["F001"], priority=10),
        ]
        result = order_backlog(items)
        assert result == ["E001", "F001", "S001"]

    def test_cycle_raises_error(self):
        """Cycle should raise ValueError (programming error)."""
        items = [
            epic("E001", depends_on=["E002"]),
            epic("E002", depends_on=["E001"]),
        ]
        with pytest.raises(ValueError, match="Cycle detected"):
            order_backlog(items)

    def test_deps_referencing_missing_id_ignored(self):
        """depends_on referencing an ID not in items is silently skipped in ordering.

        This is valid because dependency validation happens separately
        (validate_dependencies). The ordering engine only cares about
        edges between items that exist.
        """
        items = [
            epic("E001", depends_on=["X999"]),
            epic("E002"),
        ]
        result = order_backlog(items)
        # Both have 0 in-degree for known items, sorted by priority then ID
        assert result == ["E001", "E002"]


# ===========================================================================
# Wave Grouping
# ===========================================================================

class TestComputeWaves:

    def test_all_independent_single_wave(self):
        items = [
            epic("E001", priority=30),
            epic("E002", priority=50),
            epic("E003", priority=10),
        ]
        waves = compute_waves(items)
        assert len(waves) == 1
        assert waves[0] == ["E002", "E001", "E003"]

    def test_linear_chain_one_per_wave(self):
        items = [
            epic("E001", priority=10),
            epic("E002", depends_on=["E001"], priority=10),
            epic("E003", depends_on=["E002"], priority=10),
        ]
        waves = compute_waves(items)
        assert len(waves) == 3
        assert waves[0] == ["E001"]
        assert waves[1] == ["E002"]
        assert waves[2] == ["E003"]

    def test_diamond_produces_three_waves(self):
        items = [
            epic("E001", priority=100),
            epic("E002", depends_on=["E001"], priority=80),
            epic("E003", depends_on=["E001"], priority=60),
            epic("E004", depends_on=["E002", "E003"], priority=40),
        ]
        waves = compute_waves(items)
        assert len(waves) == 3
        assert waves[0] == ["E001"]
        assert waves[1] == ["E002", "E003"]
        assert waves[2] == ["E004"]

    def test_within_wave_priority_ordering(self):
        """Within a wave, items sorted by priority DESC, then ID ASC."""
        items = [
            epic("E001", priority=10),
            epic("E002", priority=50),
            epic("E003", priority=50),
        ]
        waves = compute_waves(items)
        assert len(waves) == 1
        assert waves[0] == ["E002", "E003", "E001"]

    def test_flattened_waves_equals_order_backlog(self):
        """Invariant: flattened wave list must equal order_backlog output."""
        items = [
            epic("E001", priority=100),
            epic("E002", depends_on=["E001"], priority=80),
            epic("E003", depends_on=["E001"], priority=60),
            feature("F001", "E001", depends_on=["E002"], priority=50),
            feature("F002", "E002", depends_on=["E003"], priority=40),
            story("S001", "F001", depends_on=["F001", "F002"], priority=20),
        ]
        waves = compute_waves(items)
        flattened = [item_id for wave in waves for item_id in wave]
        ordered = order_backlog(items)
        assert flattened == ordered

    def test_single_item(self):
        items = [epic("E001")]
        waves = compute_waves(items)
        assert waves == [["E001"]]

    def test_cycle_raises_error(self):
        items = [
            epic("E001", depends_on=["E002"]),
            epic("E002", depends_on=["E001"]),
        ]
        with pytest.raises(ValueError, match="Cycle detected"):
            compute_waves(items)


# ===========================================================================
# Backlog Hash
# ===========================================================================

class TestComputeBacklogHash:

    def test_same_input_same_hash(self):
        items = [
            epic("E001", priority=100),
            feature("F001", "E001", priority=50),
        ]
        h1 = compute_backlog_hash(items)
        h2 = compute_backlog_hash(items)
        assert h1 == h2

    def test_hash_is_64_hex_chars(self):
        items = [epic("E001")]
        h = compute_backlog_hash(items)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_changing_title_same_hash(self):
        items1 = [epic("E001", priority=50)]
        items1[0]["title"] = "Original Title"

        items2 = [epic("E001", priority=50)]
        items2[0]["title"] = "Completely Different Title"

        assert compute_backlog_hash(items1) == compute_backlog_hash(items2)

    def test_changing_description_same_hash(self):
        items1 = [epic("E001", priority=50)]
        items1[0]["description"] = "Original description"

        items2 = [epic("E001", priority=50)]
        items2[0]["description"] = "Totally rewritten description"

        assert compute_backlog_hash(items1) == compute_backlog_hash(items2)

    def test_changing_priority_different_hash(self):
        items1 = [epic("E001", priority=50)]
        items2 = [epic("E001", priority=51)]
        assert compute_backlog_hash(items1) != compute_backlog_hash(items2)

    def test_changing_depends_on_different_hash(self):
        items1 = [epic("E001"), epic("E002")]
        items2 = [epic("E001", depends_on=["E002"]), epic("E002")]
        assert compute_backlog_hash(items1) != compute_backlog_hash(items2)

    def test_changing_parent_id_different_hash(self):
        items1 = [
            epic("E001"), epic("E002"),
            feature("F001", "E001"),
        ]
        items2 = [
            epic("E001"), epic("E002"),
            feature("F001", "E002"),  # Different parent
        ]
        assert compute_backlog_hash(items1) != compute_backlog_hash(items2)

    def test_item_order_irrelevant(self):
        """Item order in the list shouldn't affect hash (sorted by ID internally)."""
        items1 = [
            epic("E002", priority=80),
            epic("E001", priority=100),
        ]
        items2 = [
            epic("E001", priority=100),
            epic("E002", priority=80),
        ]
        assert compute_backlog_hash(items1) == compute_backlog_hash(items2)

    def test_depends_on_order_irrelevant(self):
        """depends_on order shouldn't affect hash (sorted internally)."""
        items1 = [
            epic("E001"),
            epic("E002"),
            epic("E003", depends_on=["E002", "E001"]),
        ]
        items2 = [
            epic("E001"),
            epic("E002"),
            epic("E003", depends_on=["E001", "E002"]),
        ]
        assert compute_backlog_hash(items1) == compute_backlog_hash(items2)

    def test_integer_canonicalization(self):
        """priority_score is canonicalized to int — 50 and 50.0 produce same hash."""
        items1 = [epic("E001", priority=50)]
        items2 = [epic("E001", priority=50)]
        items2[0]["priority_score"] = 50.0  # Float
        assert compute_backlog_hash(items1) == compute_backlog_hash(items2)


# ===========================================================================
# Task 7: ExecutionPlan Derivation
# ===========================================================================

class TestDeriveExecutionPlan:

    def test_basic_derivation(self):
        items = [
            epic("E001", priority=100),
            epic("E002", depends_on=["E001"], priority=80),
            feature("F001", "E001", priority=50),
        ]
        plan = derive_execution_plan(items, intent_id="intent-123", run_id="run-456")

        assert plan["intent_id"] == "intent-123"
        assert plan["run_id"] == "run-456"
        assert plan["generator_version"] == "1.0.0"
        assert len(plan["backlog_hash"]) == 64
        assert len(plan["ordered_backlog_ids"]) == 3
        assert len(plan["waves"]) >= 1

    def test_deterministic_end_to_end(self):
        items = [
            epic("E001", priority=100),
            epic("E002", depends_on=["E001"], priority=80),
            feature("F001", "E001", depends_on=["E002"], priority=50),
        ]
        plan1 = derive_execution_plan(items, "i1", "r1")
        plan2 = derive_execution_plan(items, "i1", "r1")

        assert plan1["backlog_hash"] == plan2["backlog_hash"]
        assert plan1["ordered_backlog_ids"] == plan2["ordered_backlog_ids"]
        assert plan1["waves"] == plan2["waves"]

    def test_hash_matches_manual_computation(self):
        items = [epic("E001", priority=100)]
        plan = derive_execution_plan(items, "i1", "r1")
        expected_hash = compute_backlog_hash(items)
        assert plan["backlog_hash"] == expected_hash

    def test_flattened_waves_equals_ordered_ids(self):
        items = [
            epic("E001", priority=100),
            epic("E002", depends_on=["E001"], priority=80),
            epic("E003", depends_on=["E001"], priority=60),
            epic("E004", depends_on=["E002", "E003"], priority=40),
        ]
        plan = derive_execution_plan(items, "i1", "r1")
        flattened = [item_id for wave in plan["waves"] for item_id in wave]
        assert flattened == plan["ordered_backlog_ids"]

    def test_metadata_does_not_affect_hash(self):
        """Different intent_id/run_id → same backlog_hash."""
        items = [epic("E001", priority=50)]
        plan1 = derive_execution_plan(items, "intent-A", "run-A")
        plan2 = derive_execution_plan(items, "intent-B", "run-B")
        assert plan1["backlog_hash"] == plan2["backlog_hash"]
        assert plan1["ordered_backlog_ids"] == plan2["ordered_backlog_ids"]

    def test_all_required_fields_present(self):
        items = [epic("E001")]
        plan = derive_execution_plan(items, "i1", "r1")
        required = {"backlog_hash", "intent_id", "run_id",
                     "ordered_backlog_ids", "waves", "generator_version"}
        assert required == set(plan.keys())
