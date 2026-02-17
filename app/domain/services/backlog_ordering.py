"""
Deterministic ordering engine for validated backlogs.

"LLMs generate. Machines order."

All functions are pure — no DB, no LLM, no side effects.
Same input always produces same output.

WS-BCP-002: Tasks 6, 7.
"""

import hashlib
import json
from collections import deque
from typing import Optional


# ---------------------------------------------------------------------------
# Task 6: Topological sort with priority tie-breaking
# ---------------------------------------------------------------------------

def order_backlog(items: list[dict]) -> list[str]:
    """
    Topological sort by depends_on, with priority tie-breaking.

    Algorithm:
    1. Build adjacency graph from depends_on edges
    2. Kahn's algorithm for topological sort
    3. Within same topological tier, sort by priority_score DESC
    4. Tie-break by id ASC (lexicographic)

    Precondition: caller has validated no dependency cycles exist.
    Raises ValueError if a cycle is detected (programming error).

    Returns: list of item IDs in execution order.
    """
    items_by_id = {item["id"]: item for item in items}
    all_ids = set(items_by_id.keys())

    # Build in-degree map and adjacency (dependents)
    in_degree: dict[str, int] = {nid: 0 for nid in all_ids}
    dependents: dict[str, list[str]] = {nid: [] for nid in all_ids}

    for item in items:
        item_id = item["id"]
        for dep_id in item.get("depends_on", []):
            if dep_id in all_ids:
                in_degree[item_id] += 1
                dependents[dep_id].append(item_id)

    # Kahn's algorithm with priority-sorted tiers
    result: list[str] = []
    # Start with all zero in-degree nodes
    ready = [nid for nid in all_ids if in_degree[nid] == 0]
    ready = _sort_by_priority(ready, items_by_id)

    while ready:
        # Process this entire tier
        next_ready: list[str] = []
        for nid in ready:
            result.append(nid)
            for dep in dependents[nid]:
                in_degree[dep] -= 1
                if in_degree[dep] == 0:
                    next_ready.append(dep)

        ready = _sort_by_priority(next_ready, items_by_id)

    if len(result) != len(all_ids):
        raise ValueError(
            f"Cycle detected during topological sort: "
            f"processed {len(result)} of {len(all_ids)} items"
        )

    return result


# ---------------------------------------------------------------------------
# Wave grouping (Kahn-style tiers)
# ---------------------------------------------------------------------------

def compute_waves(items: list[dict]) -> list[list[str]]:
    """
    Compute wave tiers using Kahn's algorithm.

    Wave 0 = all nodes with in-degree 0 (no dependencies)
    Wave 1 = all nodes with in-degree 0 after removing Wave 0
    Repeat until all nodes assigned.

    Within each wave: sort by priority_score DESC, tie-break by id ASC.

    Invariant: flattened waves == order_backlog output.

    Precondition: no dependency cycles.
    """
    items_by_id = {item["id"]: item for item in items}
    all_ids = set(items_by_id.keys())

    # Build in-degree map and adjacency
    in_degree: dict[str, int] = {nid: 0 for nid in all_ids}
    dependents: dict[str, list[str]] = {nid: [] for nid in all_ids}

    for item in items:
        item_id = item["id"]
        for dep_id in item.get("depends_on", []):
            if dep_id in all_ids:
                in_degree[item_id] += 1
                dependents[dep_id].append(item_id)

    waves: list[list[str]] = []
    remaining = set(all_ids)

    while remaining:
        # Current wave = all nodes with in-degree 0
        wave = [nid for nid in remaining if in_degree[nid] == 0]
        if not wave:
            raise ValueError("Cycle detected during wave computation")

        wave = _sort_by_priority(wave, items_by_id)
        waves.append(wave)

        # Remove this wave's nodes and update in-degrees
        for nid in wave:
            remaining.remove(nid)
            for dep in dependents[nid]:
                in_degree[dep] -= 1

    return waves


# ---------------------------------------------------------------------------
# backlog_hash computation
# ---------------------------------------------------------------------------

def compute_backlog_hash(items: list[dict]) -> str:
    """
    SHA-256 of structural backlog fields only.

    Algorithm:
    1. Sort items by id ASC
    2. For each item, extract structure-only tuple:
       (id, level, int(priority_score), sorted(depends_on), parent_id)
    3. Serialize as canonical JSON (sorted keys, no whitespace)
    4. SHA-256 the serialized string

    Included (base fields): id, level, priority_score, depends_on, parent_id
    Excluded (hash boundary invariant): title, summary, details, lineage fields
    """
    sorted_items = sorted(items, key=lambda x: x["id"])

    structural = []
    for item in sorted_items:
        structural.append({
            "id": item["id"],
            "level": item["level"],
            "priority_score": int(item["priority_score"]),
            "depends_on": sorted(item.get("depends_on", [])),
            "parent_id": item.get("parent_id"),
        })

    canonical = json.dumps(structural, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Task 7: ExecutionPlan derivation
# ---------------------------------------------------------------------------

def derive_execution_plan(
    items: list[dict],
    intent_id: str,
    run_id: str,
) -> dict:
    """
    Derive a complete ExecutionPlan from validated backlog items.

    Mechanical function — never LLM-authored.

    Precondition: items have passed all graph validation
    (validate_dependencies, validate_hierarchy, detect_dependency_cycles).
    """
    ordered_ids = order_backlog(items)
    waves = compute_waves(items)
    backlog_hash = compute_backlog_hash(items)

    return {
        "backlog_hash": backlog_hash,
        "intent_id": intent_id,
        "run_id": run_id,
        "ordered_backlog_ids": ordered_ids,
        "waves": waves,
        "generator_version": "1.0.0",
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _sort_by_priority(ids: list[str], items_by_id: dict[str, dict]) -> list[str]:
    """Sort IDs by priority_score DESC, then id ASC."""
    return sorted(
        ids,
        key=lambda nid: (-items_by_id[nid].get("priority_score", 0), nid),
    )
