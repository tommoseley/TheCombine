"""
Graph validation for backlog items.

Single authority for dependency existence, hierarchy rules, and cycle detection (DQ-2).
All functions are pure — no DB, no LLM, no side effects.

WS-BCP-002: Tasks 4a, 4b, 5.
"""

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class DependencyError:
    """A single dependency validation failure."""
    item_id: str
    error_type: str  # "missing_reference" | "self_reference"
    detail: str


@dataclass
class DependencyResult:
    """Result of dependency validation."""
    valid: bool
    errors: list[DependencyError] = field(default_factory=list)


@dataclass
class HierarchyError:
    """A single hierarchy validation failure."""
    item_id: str
    error_type: str  # "hierarchy_violation" | "invalid_level_transition" | "orphaned_item" | "parent_not_found" | "parent_cycle"
    detail: str


@dataclass
class HierarchyResult:
    """Result of hierarchy validation."""
    valid: bool
    errors: list[HierarchyError] = field(default_factory=list)


@dataclass
class CycleTrace:
    """A detected dependency cycle."""
    cycle: list[str]  # e.g., ["E001", "F002", "S003", "E001"]


@dataclass
class CycleResult:
    """Result of dependency cycle detection."""
    has_cycles: bool
    cycles: list[CycleTrace] = field(default_factory=list)


@dataclass
class BacklogValidationResult:
    """Composite result of all backlog validations."""
    valid: bool
    dependency_errors: list[DependencyError] = field(default_factory=list)
    hierarchy_errors: list[HierarchyError] = field(default_factory=list)
    cycle_traces: list[CycleTrace] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Canonical hierarchy rules (single source of truth)
# ---------------------------------------------------------------------------

# EPIC: parent_id must be null
# FEATURE: parent_id must reference an item with level EPIC
# STORY: parent_id must reference an item with level FEATURE

VALID_PARENT_LEVELS = {
    "FEATURE": "EPIC",
    "STORY": "FEATURE",
}


# ---------------------------------------------------------------------------
# Task 4a: Dependency validation
# ---------------------------------------------------------------------------

def validate_dependencies(items: list[dict]) -> DependencyResult:
    """
    Validate that all depends_on references exist and no self-references.

    Returns all errors (not just the first). Fail hard — no silent correction.
    """
    all_ids = {item["id"] for item in items}
    errors: list[DependencyError] = []

    for item in items:
        item_id = item["id"]
        depends_on = item.get("depends_on", [])

        for dep_id in depends_on:
            if dep_id == item_id:
                errors.append(DependencyError(
                    item_id=item_id,
                    error_type="self_reference",
                    detail=f"{item_id} depends on itself",
                ))
            elif dep_id not in all_ids:
                errors.append(DependencyError(
                    item_id=item_id,
                    error_type="missing_reference",
                    detail=f"{item_id} depends on {dep_id} which does not exist",
                ))

    return DependencyResult(valid=len(errors) == 0, errors=errors)


# ---------------------------------------------------------------------------
# Task 4b: Hierarchy validation
# ---------------------------------------------------------------------------

def validate_hierarchy(items: list[dict]) -> HierarchyResult:
    """
    Validate hierarchy rules: EPIC→null, FEATURE→EPIC, STORY→FEATURE.

    Also detects orphaned items, missing parents, and parent cycles.
    Returns all errors. Fail hard — no silent correction.
    """
    items_by_id = {item["id"]: item for item in items}
    errors: list[HierarchyError] = []

    for item in items:
        item_id = item["id"]
        level = item["level"]
        parent_id = item.get("parent_id")

        # EPIC must have null parent
        if level == "EPIC":
            if parent_id is not None:
                errors.append(HierarchyError(
                    item_id=item_id,
                    error_type="hierarchy_violation",
                    detail=f"EPIC {item_id} must have null parent_id, got {parent_id}",
                ))
            continue

        # FEATURE and STORY must have non-null parent
        if parent_id is None:
            errors.append(HierarchyError(
                item_id=item_id,
                error_type="orphaned_item",
                detail=f"{level} {item_id} has null parent_id",
            ))
            continue

        # Parent must exist
        parent = items_by_id.get(parent_id)
        if parent is None:
            errors.append(HierarchyError(
                item_id=item_id,
                error_type="parent_not_found",
                detail=f"{level} {item_id} references parent {parent_id} which does not exist",
            ))
            continue

        # Parent must be the correct level
        expected_parent_level = VALID_PARENT_LEVELS.get(level)
        actual_parent_level = parent["level"]
        if actual_parent_level != expected_parent_level:
            errors.append(HierarchyError(
                item_id=item_id,
                error_type="invalid_level_transition",
                detail=f"{level} {item_id} has parent {parent_id} (level {actual_parent_level}), expected {expected_parent_level}",
            ))

    # Detect parent cycles (separate pass)
    _detect_parent_cycles(items_by_id, errors)

    return HierarchyResult(valid=len(errors) == 0, errors=errors)


def _detect_parent_cycles(
    items_by_id: dict[str, dict],
    errors: list[HierarchyError],
) -> None:
    """Detect cycles in parent_id chains (A→B→A)."""
    visited: set[str] = set()

    for item_id in sorted(items_by_id.keys()):
        if item_id in visited:
            continue

        # Walk the parent chain
        chain: list[str] = []
        chain_set: set[str] = set()
        current = item_id

        while current is not None and current not in visited:
            if current in chain_set:
                # Found a cycle — extract it
                cycle_start = chain.index(current)
                cycle = chain[cycle_start:] + [current]
                errors.append(HierarchyError(
                    item_id=current,
                    error_type="parent_cycle",
                    detail=f"Parent cycle detected: {' -> '.join(cycle)}",
                ))
                break

            chain.append(current)
            chain_set.add(current)

            item = items_by_id.get(current)
            if item is None:
                break
            current = item.get("parent_id")

        visited.update(chain_set)


# ---------------------------------------------------------------------------
# Task 5: Dependency cycle detection
# ---------------------------------------------------------------------------

def detect_dependency_cycles(items: list[dict]) -> CycleResult:
    """
    Detect cycles in the depends_on graph using DFS.

    Scope: depends_on edges only. Parent cycles are owned by validate_hierarchy.
    Deterministic: processes nodes in sorted ID order.
    """
    adj: dict[str, list[str]] = {}
    all_ids: set[str] = set()

    for item in items:
        item_id = item["id"]
        all_ids.add(item_id)
        adj[item_id] = [d for d in item.get("depends_on", []) if d in {i["id"] for i in items}]

    # DFS-based cycle detection
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {nid: WHITE for nid in all_ids}
    parent_map: dict[str, Optional[str]] = {nid: None for nid in all_ids}
    cycles: list[CycleTrace] = []

    def dfs(node: str) -> None:
        color[node] = GRAY
        for neighbor in sorted(adj.get(node, [])):
            if neighbor not in color:
                continue
            if color[neighbor] == GRAY:
                # Back edge — extract cycle
                cycle = [neighbor]
                current = node
                while current != neighbor:
                    cycle.append(current)
                    current = parent_map[current]
                cycle.append(neighbor)
                cycle.reverse()
                cycles.append(CycleTrace(cycle=cycle))
            elif color[neighbor] == WHITE:
                parent_map[neighbor] = node
                dfs(neighbor)
        color[node] = BLACK

    for node in sorted(all_ids):
        if color[node] == WHITE:
            dfs(node)

    return CycleResult(has_cycles=len(cycles) > 0, cycles=cycles)


# ---------------------------------------------------------------------------
# Composite validator
# ---------------------------------------------------------------------------

def validate_backlog(items: list[dict]) -> BacklogValidationResult:
    """
    Run all three validators. Returns the complete picture — all errors
    from all validators, even if earlier ones fail.
    """
    dep_result = validate_dependencies(items)
    hier_result = validate_hierarchy(items)
    cycle_result = detect_dependency_cycles(items)

    return BacklogValidationResult(
        valid=dep_result.valid and hier_result.valid and not cycle_result.has_cycles,
        dependency_errors=dep_result.errors,
        hierarchy_errors=hier_result.errors,
        cycle_traces=cycle_result.cycles,
    )
