"""
SetReconciler — ID-only reconciliation for backlog item sets.

Pure mechanical component used by EpicFeatureFanoutPOW and
FeatureStoryFanoutPOW to reconcile existing child sets with
newly generated candidate sets on re-runs.

Matching policy: ID-only. No fuzzy title matching.
- Matching ID → KEEP (details may update)
- New ID (candidate only) → ADD
- Missing ID (existing only) → DROP

WS-BCP-005.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ReconciliationResult:
    """Result of reconciling existing items against candidate items."""
    keeps: List[Dict[str, Any]] = field(default_factory=list)
    adds: List[Dict[str, Any]] = field(default_factory=list)
    drops: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def has_drops(self) -> bool:
        return len(self.drops) > 0

    @property
    def summary(self) -> Dict[str, int]:
        return {
            "keeps": len(self.keeps),
            "adds": len(self.adds),
            "drops": len(self.drops),
        }


def reconcile(
    existing_items: List[Dict[str, Any]],
    candidate_items: List[Dict[str, Any]],
) -> ReconciliationResult:
    """Reconcile an existing child set with a newly generated candidate set.

    Args:
        existing_items: Currently persisted backlog items under a parent.
        candidate_items: Newly generated backlog items from a DCW run.

    Returns:
        ReconciliationResult with keeps, adds, and drops.

    Both lists are matched by the "id" field only.
    Order of items in either list does not affect the result.
    """
    existing_by_id = {item["id"]: item for item in existing_items}
    candidate_by_id = {item["id"]: item for item in candidate_items}

    existing_ids = set(existing_by_id.keys())
    candidate_ids = set(candidate_by_id.keys())

    keep_ids = existing_ids & candidate_ids
    add_ids = candidate_ids - existing_ids
    drop_ids = existing_ids - candidate_ids

    # Keeps: return the candidate version (details may have updated)
    keeps = [candidate_by_id[id_] for id_ in sorted(keep_ids)]
    # Adds: new items from the candidate set
    adds = [candidate_by_id[id_] for id_ in sorted(add_ids)]
    # Drops: existing items not in the candidate set
    drops = [existing_by_id[id_] for id_ in sorted(drop_ids)]

    return ReconciliationResult(keeps=keeps, adds=adds, drops=drops)
