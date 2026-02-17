"""
Tier-1 tests for graph_validator.py.

Pure in-memory, no DB, no LLM.
Tests validate_dependencies, validate_hierarchy, detect_dependency_cycles,
and the composite validate_backlog.

WS-BCP-002.
"""

import pytest

from app.domain.services.graph_validator import (
    validate_dependencies,
    validate_hierarchy,
    detect_dependency_cycles,
    validate_backlog,
    DependencyResult,
    HierarchyResult,
    CycleResult,
    BacklogValidationResult,
)


# ---------------------------------------------------------------------------
# Fixtures: reusable backlog item builders
# ---------------------------------------------------------------------------

def epic(id, depends_on=None, priority=50):
    return {
        "schema_version": "1.0.0",
        "id": id, "level": "EPIC", "title": f"Epic {id}",
        "summary": f"Summary for {id}", "priority_score": priority,
        "depends_on": depends_on or [], "parent_id": None,
    }

def feature(id, parent_id, depends_on=None, priority=30):
    return {
        "schema_version": "1.0.0",
        "id": id, "level": "FEATURE", "title": f"Feature {id}",
        "summary": f"Summary for {id}", "priority_score": priority,
        "depends_on": depends_on or [], "parent_id": parent_id,
    }

def story(id, parent_id, depends_on=None, priority=10):
    return {
        "schema_version": "1.0.0",
        "id": id, "level": "STORY", "title": f"Story {id}",
        "summary": f"Summary for {id}", "priority_score": priority,
        "depends_on": depends_on or [], "parent_id": parent_id,
    }


def valid_backlog():
    """A well-formed backlog for baseline tests."""
    return [
        epic("E001", priority=100),
        epic("E002", depends_on=["E001"], priority=80),
        feature("F001", "E001", priority=50),
        feature("F002", "E002", depends_on=["F001"], priority=40),
        story("S001", "F001", priority=20),
        story("S002", "F002", depends_on=["S001"], priority=10),
    ]


# ===========================================================================
# Task 4a: Dependency Validation
# ===========================================================================

class TestValidateDependencies:

    def test_valid_dependencies(self):
        items = valid_backlog()
        result = validate_dependencies(items)
        assert result.valid is True
        assert result.errors == []

    def test_empty_depends_on(self):
        items = [epic("E001"), feature("F001", "E001")]
        result = validate_dependencies(items)
        assert result.valid is True
        assert result.errors == []

    def test_missing_reference(self):
        items = [
            epic("E001", depends_on=["E999"]),
        ]
        result = validate_dependencies(items)
        assert result.valid is False
        assert len(result.errors) == 1
        assert result.errors[0].item_id == "E001"
        assert result.errors[0].error_type == "missing_reference"
        assert "E999" in result.errors[0].detail

    def test_self_reference(self):
        items = [
            epic("E001", depends_on=["E001"]),
        ]
        result = validate_dependencies(items)
        assert result.valid is False
        assert len(result.errors) == 1
        assert result.errors[0].item_id == "E001"
        assert result.errors[0].error_type == "self_reference"

    def test_multiple_errors_all_reported(self):
        items = [
            epic("E001", depends_on=["E001", "E999"]),
            feature("F001", "E001", depends_on=["X001"]),
        ]
        result = validate_dependencies(items)
        assert result.valid is False
        assert len(result.errors) == 3
        error_types = {(e.item_id, e.error_type) for e in result.errors}
        assert ("E001", "self_reference") in error_types
        assert ("E001", "missing_reference") in error_types
        assert ("F001", "missing_reference") in error_types

    def test_cross_level_dependency_valid(self):
        """A FEATURE depending on an EPIC is valid (dependency, not hierarchy)."""
        items = [
            epic("E001"),
            feature("F001", "E001", depends_on=["E001"]),
        ]
        result = validate_dependencies(items)
        assert result.valid is True

    def test_single_item_no_deps(self):
        items = [epic("E001")]
        result = validate_dependencies(items)
        assert result.valid is True


# ===========================================================================
# Task 4b: Hierarchy Validation
# ===========================================================================

class TestValidateHierarchy:

    def test_valid_hierarchy(self):
        items = valid_backlog()
        result = validate_hierarchy(items)
        assert result.valid is True
        assert result.errors == []

    def test_epic_with_parent_id(self):
        items = [
            {"id": "E001", "level": "EPIC", "title": "Bad Epic",
             "summary": "x", "priority_score": 50,
             "depends_on": [], "parent_id": "E002"},
            epic("E002"),
        ]
        result = validate_hierarchy(items)
        assert result.valid is False
        err = [e for e in result.errors if e.error_type == "hierarchy_violation"]
        assert len(err) == 1
        assert err[0].item_id == "E001"

    def test_feature_with_null_parent(self):
        items = [
            epic("E001"),
            {"id": "F001", "level": "FEATURE", "title": "Orphan",
             "summary": "x", "priority_score": 30,
             "depends_on": [], "parent_id": None},
        ]
        result = validate_hierarchy(items)
        assert result.valid is False
        err = [e for e in result.errors if e.error_type == "orphaned_item"]
        assert len(err) == 1
        assert err[0].item_id == "F001"

    def test_story_with_null_parent(self):
        items = [
            epic("E001"),
            feature("F001", "E001"),
            {"id": "S001", "level": "STORY", "title": "Orphan Story",
             "summary": "x", "priority_score": 10,
             "depends_on": [], "parent_id": None},
        ]
        result = validate_hierarchy(items)
        assert result.valid is False
        err = [e for e in result.errors if e.error_type == "orphaned_item"]
        assert len(err) == 1
        assert err[0].item_id == "S001"

    def test_story_parented_to_epic(self):
        """STORY must parent to FEATURE, not EPIC."""
        items = [
            epic("E001"),
            story("S001", "E001"),
        ]
        result = validate_hierarchy(items)
        assert result.valid is False
        err = [e for e in result.errors if e.error_type == "invalid_level_transition"]
        assert len(err) == 1
        assert err[0].item_id == "S001"
        assert "EPIC" in err[0].detail

    def test_feature_parented_to_feature(self):
        """FEATURE must parent to EPIC, not another FEATURE."""
        items = [
            epic("E001"),
            feature("F001", "E001"),
            feature("F002", "F001"),  # Invalid: FEATURE -> FEATURE
        ]
        result = validate_hierarchy(items)
        assert result.valid is False
        err = [e for e in result.errors if e.error_type == "invalid_level_transition"]
        assert len(err) == 1
        assert err[0].item_id == "F002"

    def test_feature_parented_to_story(self):
        """FEATURE must parent to EPIC, not STORY."""
        items = [
            epic("E001"),
            feature("F001", "E001"),
            story("S001", "F001"),
            feature("F002", "S001"),  # Invalid: FEATURE -> STORY
        ]
        result = validate_hierarchy(items)
        assert result.valid is False
        err = [e for e in result.errors if e.error_type == "invalid_level_transition"]
        assert len(err) == 1
        assert err[0].item_id == "F002"

    def test_parent_not_found(self):
        items = [
            feature("F001", "E999"),  # E999 doesn't exist
        ]
        result = validate_hierarchy(items)
        assert result.valid is False
        err = [e for e in result.errors if e.error_type == "parent_not_found"]
        assert len(err) == 1
        assert err[0].item_id == "F001"
        assert "E999" in err[0].detail

    def test_deeply_nested_valid_tree(self):
        """Multiple EPICs, each with features and stories."""
        items = [
            epic("E001", priority=100),
            epic("E002", priority=80),
            feature("F001", "E001"),
            feature("F002", "E001"),
            feature("F003", "E002"),
            story("S001", "F001"),
            story("S002", "F001"),
            story("S003", "F002"),
            story("S004", "F003"),
        ]
        result = validate_hierarchy(items)
        assert result.valid is True

    def test_parent_cycle_two_nodes(self):
        """A→B→A via parent_id."""
        items = [
            {"id": "F001", "level": "FEATURE", "title": "F1",
             "summary": "x", "priority_score": 30,
             "depends_on": [], "parent_id": "F002"},
            {"id": "F002", "level": "FEATURE", "title": "F2",
             "summary": "x", "priority_score": 30,
             "depends_on": [], "parent_id": "F001"},
        ]
        result = validate_hierarchy(items)
        assert result.valid is False
        cycle_errors = [e for e in result.errors if e.error_type == "parent_cycle"]
        assert len(cycle_errors) >= 1

    def test_multiple_errors_all_reported(self):
        """Orphan + missing parent in same backlog."""
        items = [
            epic("E001"),
            {"id": "F001", "level": "FEATURE", "title": "Orphan",
             "summary": "x", "priority_score": 30,
             "depends_on": [], "parent_id": None},
            feature("F002", "E999"),  # Missing parent
        ]
        result = validate_hierarchy(items)
        assert result.valid is False
        assert len(result.errors) >= 2
        error_types = {e.error_type for e in result.errors}
        assert "orphaned_item" in error_types
        assert "parent_not_found" in error_types


# ===========================================================================
# Task 5: Dependency Cycle Detection
# ===========================================================================

class TestDetectDependencyCycles:

    def test_acyclic_graph(self):
        items = valid_backlog()
        result = detect_dependency_cycles(items)
        assert result.has_cycles is False
        assert result.cycles == []

    def test_simple_cycle_two_nodes(self):
        items = [
            epic("E001", depends_on=["E002"]),
            epic("E002", depends_on=["E001"]),
        ]
        result = detect_dependency_cycles(items)
        assert result.has_cycles is True
        assert len(result.cycles) >= 1
        # The cycle should contain both E001 and E002
        all_cycle_ids = set()
        for trace in result.cycles:
            all_cycle_ids.update(trace.cycle)
        assert "E001" in all_cycle_ids
        assert "E002" in all_cycle_ids

    def test_multi_node_cycle(self):
        items = [
            epic("E001", depends_on=["E003"]),
            epic("E002", depends_on=["E001"]),
            epic("E003", depends_on=["E002"]),
        ]
        result = detect_dependency_cycles(items)
        assert result.has_cycles is True
        assert len(result.cycles) >= 1

    def test_large_acyclic_dag(self):
        """10+ nodes, no cycles."""
        items = [
            epic("E001"),
            epic("E002", depends_on=["E001"]),
            epic("E003", depends_on=["E001"]),
            feature("F001", "E001", depends_on=["E002"]),
            feature("F002", "E002", depends_on=["E003"]),
            feature("F003", "E003"),
            story("S001", "F001", depends_on=["F001"]),
            story("S002", "F001", depends_on=["F001", "F002"]),
            story("S003", "F002", depends_on=["F003"]),
            story("S004", "F003"),
            story("S005", "F003", depends_on=["S004"]),
        ]
        result = detect_dependency_cycles(items)
        assert result.has_cycles is False

    def test_single_item_no_deps(self):
        items = [epic("E001")]
        result = detect_dependency_cycles(items)
        assert result.has_cycles is False

    def test_deterministic_output(self):
        """Same input produces same cycle trace."""
        items = [
            epic("E001", depends_on=["E002"]),
            epic("E002", depends_on=["E001"]),
        ]
        result1 = detect_dependency_cycles(items)
        result2 = detect_dependency_cycles(items)
        assert result1.cycles[0].cycle == result2.cycles[0].cycle


# ===========================================================================
# Composite: validate_backlog
# ===========================================================================

class TestValidateBacklog:

    def test_all_valid(self):
        items = valid_backlog()
        result = validate_backlog(items)
        assert result.valid is True
        assert result.dependency_errors == []
        assert result.hierarchy_errors == []
        assert result.cycle_traces == []

    def test_dependency_error_only(self):
        items = [
            epic("E001", depends_on=["E999"]),
        ]
        result = validate_backlog(items)
        assert result.valid is False
        assert len(result.dependency_errors) == 1
        assert result.hierarchy_errors == []
        assert result.cycle_traces == []

    def test_hierarchy_error_only(self):
        items = [
            epic("E001"),
            story("S001", "E001"),  # STORY→EPIC invalid
        ]
        result = validate_backlog(items)
        assert result.valid is False
        assert result.dependency_errors == []
        assert len(result.hierarchy_errors) == 1

    def test_cycle_only(self):
        items = [
            epic("E001", depends_on=["E002"]),
            epic("E002", depends_on=["E001"]),
        ]
        result = validate_backlog(items)
        assert result.valid is False
        assert len(result.cycle_traces) >= 1

    def test_mixed_errors_all_reported(self):
        """All three validators find errors — all reported."""
        items = [
            epic("E001", depends_on=["E002", "X001"]),  # X001 missing
            epic("E002", depends_on=["E001"]),  # cycle with E001
            story("S001", "E001"),  # STORY→EPIC invalid
        ]
        result = validate_backlog(items)
        assert result.valid is False
        assert len(result.dependency_errors) >= 1  # X001 missing
        assert len(result.hierarchy_errors) >= 1  # S001 invalid parent level
        assert len(result.cycle_traces) >= 1  # E001↔E002 cycle
