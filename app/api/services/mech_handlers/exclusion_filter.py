"""Exclusion Filter Handler.

Per WS-ADR-047-004 Phase 2: Specialized handler for filtering document
sections that mention excluded topics.

This handler extracts the filtering logic from plan_executor.py's
_filter_excluded_topics method.
"""

import copy
import json
import logging
from typing import Any, Dict, List

from app.api.services.mech_handlers.base import (
    ExecutionContext,
    MechHandler,
    MechResult,
)
from app.api.services.mech_handlers.registry import register_handler

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pure functions (extracted for testability — WS-CRAP-004)
# ---------------------------------------------------------------------------

def build_exclusion_bindings(invariants: list) -> tuple:
    """Build exclusion and binding lists from invariants.

    Pure function — no I/O, no side effects.

    Args:
        invariants: List of invariant dicts with canonical_tags

    Returns:
        Tuple of (exclusions list, all_bindings list)
    """
    exclusions = []
    all_bindings = []

    for inv in invariants:
        tags = inv.get("canonical_tags", [])
        if not tags:
            continue

        binding_info = {
            "id": inv.get("id", "UNKNOWN"),
            "tags": [t.lower() for t in tags],
            "kind": inv.get("invariant_kind", "requirement"),
        }

        all_bindings.append(binding_info)

        if inv.get("invariant_kind") == "exclusion":
            exclusions.append(binding_info)

    return exclusions, all_bindings


def filter_items_by_tags(
    items: List[Any],
    exclusions: List[Dict[str, Any]],
    text_field: str,
) -> List[Any]:
    """Filter items that mention excluded tags.

    Pure function — no I/O, no side effects.

    Args:
        items: List of items to filter
        exclusions: Exclusion bindings with tags
        text_field: Field name to extract text from (for dicts)

    Returns:
        Filtered list of items
    """
    filtered = []

    for item in items:
        if isinstance(item, dict):
            item_text = item.get(text_field, "")
        else:
            item_text = str(item)

        item_lower = item_text.lower()

        should_remove = False
        for excl in exclusions:
            for tag in excl["tags"]:
                if tag in item_lower:
                    should_remove = True
                    break
            if should_remove:
                break

        if not should_remove:
            filtered.append(item)

    return filtered


def filter_decision_points_by_tags(
    decision_points: List[Any],
    bindings: List[Dict[str, Any]],
) -> List[Any]:
    """Filter decision points overlapping any binding.

    Pure function — no I/O, no side effects.

    Args:
        decision_points: List of decision point objects
        bindings: All binding invariants with tags

    Returns:
        Filtered list of decision points
    """
    filtered = []

    for dp in decision_points:
        if isinstance(dp, dict):
            dp_text = json.dumps(dp).lower()
        else:
            dp_text = str(dp).lower()

        should_remove = False
        for binding in bindings:
            for tag in binding["tags"]:
                if tag in dp_text:
                    should_remove = True
                    break
            if should_remove:
                break

        if not should_remove:
            filtered.append(dp)

    return filtered


def apply_exclusion_filter(
    document: dict,
    invariants: list,
    *,
    filter_recommendations: bool = True,
    filter_decision_points_flag: bool = True,
) -> tuple:
    """Apply exclusion filtering to a document.

    Pure function — no I/O, no logging, no side effects.
    Deep-copies document internally to avoid mutation.

    Args:
        document: Document dict to filter
        invariants: List of invariant dicts
        filter_recommendations: Whether to filter recommendations
        filter_decision_points_flag: Whether to filter decision points

    Returns:
        Tuple of (filtered_document dict, removed_count int)
    """
    exclusions, all_bindings = build_exclusion_bindings(invariants)

    if not exclusions:
        return copy.deepcopy(document), 0

    filtered = copy.deepcopy(document)
    removed_count = 0

    if filter_recommendations:
        recommendations = filtered.get("recommendations_for_pm", [])
        if recommendations:
            original_count = len(recommendations)
            filtered_recs = filter_items_by_tags(
                recommendations, exclusions, "recommendation"
            )
            filtered["recommendations_for_pm"] = filtered_recs
            removed_count += original_count - len(filtered_recs)

    if filter_decision_points_flag and all_bindings:
        decision_points = filtered.get("early_decision_points", [])
        if decision_points:
            original_count = len(decision_points)
            filtered_dps = filter_decision_points_by_tags(
                decision_points, all_bindings
            )
            filtered["early_decision_points"] = filtered_dps
            removed_count += original_count - len(filtered_dps)

    return filtered, removed_count


# ---------------------------------------------------------------------------
# Handler class
# ---------------------------------------------------------------------------

@register_handler
class ExclusionFilterHandler(MechHandler):
    """Handler for exclusion_filter operations.

    Filters document sections (recommendations, decision points)
    that mention excluded topics based on invariant canonical tags.
    """

    operation_type = "exclusion_filter"

    async def execute(
        self,
        config: Dict[str, Any],
        context: ExecutionContext,
    ) -> MechResult:
        """Execute the exclusion filtering operation."""
        document = context.get_input("document")
        invariants = context.get_input("invariants")

        if document is None:
            return MechResult.fail(
                error="Missing required input: document",
                error_code="missing_input",
            )

        if not isinstance(document, dict):
            return MechResult.fail(
                error="Input 'document' must be a dict",
                error_code="invalid_input",
            )

        if not invariants:
            return MechResult.ok(output=document)

        fr = config.get("filter_recommendations", True)
        fdp = config.get("filter_decision_points", True)

        try:
            result, removed_count = apply_exclusion_filter(
                document,
                invariants,
                filter_recommendations=fr,
                filter_decision_points_flag=fdp,
            )

            if removed_count > 0:
                logger.info(f"Exclusion filter: removed {removed_count} items")

            return MechResult.ok(output=result)

        except Exception as e:
            logger.exception(f"Exclusion filtering failed: {e}")
            return MechResult.fail(
                error=str(e),
                error_code="execution_error",
            )
