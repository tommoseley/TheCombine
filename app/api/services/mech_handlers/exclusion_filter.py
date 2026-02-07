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
        """Execute the exclusion filtering operation.

        Args:
            config: Operation configuration with:
                - filter_recommendations: bool (default True)
                - filter_decision_points: bool (default True)
            context: Execution context with inputs:
                - document: Document to filter
                - invariants: List of invariants with canonical_tags

        Returns:
            MechResult with output containing the filtered document
        """
        # Get inputs
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

        # Handle missing invariants
        if not invariants:
            return MechResult.ok(output=document)

        # Get config options
        filter_recommendations = config.get("filter_recommendations", True)
        filter_decision_points = config.get("filter_decision_points", True)

        try:
            # Build exclusion list from invariants
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

            # If no exclusions, return unchanged
            if not exclusions:
                return MechResult.ok(output=document)

            # Work on a copy
            filtered = copy.deepcopy(document)
            removed_count = 0

            # Filter recommendations
            if filter_recommendations:
                recommendations = filtered.get("recommendations_for_pm", [])
                if recommendations:
                    original_count = len(recommendations)
                    filtered_recs = self._filter_items(
                        recommendations, exclusions, "recommendation"
                    )
                    filtered["recommendations_for_pm"] = filtered_recs
                    removed_count += original_count - len(filtered_recs)

            # Filter decision points (against ALL bindings, not just exclusions)
            if filter_decision_points and all_bindings:
                decision_points = filtered.get("early_decision_points", [])
                if decision_points:
                    original_count = len(decision_points)
                    filtered_dps = self._filter_decision_points(
                        decision_points, all_bindings
                    )
                    filtered["early_decision_points"] = filtered_dps
                    removed_count += original_count - len(filtered_dps)

            if removed_count > 0:
                logger.info(f"Exclusion filter: removed {removed_count} items")

            return MechResult.ok(output=filtered)

        except Exception as e:
            logger.exception(f"Exclusion filtering failed: {e}")
            return MechResult.fail(
                error=str(e),
                error_code="execution_error",
            )

    def _filter_items(
        self,
        items: List[Any],
        exclusions: List[Dict[str, Any]],
        text_field: str,
    ) -> List[Any]:
        """Filter items that mention excluded tags.

        Args:
            items: List of items to filter
            exclusions: Exclusion bindings with tags
            text_field: Field name to extract text from (for dicts)

        Returns:
            Filtered list of items
        """
        filtered = []

        for item in items:
            # Extract text
            if isinstance(item, dict):
                item_text = item.get(text_field, "")
            else:
                item_text = str(item)

            item_lower = item_text.lower()

            # Check if any exclusion tag is mentioned
            should_remove = False
            for excl in exclusions:
                for tag in excl["tags"]:
                    if tag in item_lower:
                        logger.debug(
                            f"Removing item mentioning excluded '{tag}'"
                        )
                        should_remove = True
                        break
                if should_remove:
                    break

            if not should_remove:
                filtered.append(item)

        return filtered

    def _filter_decision_points(
        self,
        decision_points: List[Any],
        bindings: List[Dict[str, Any]],
    ) -> List[Any]:
        """Filter decision points overlapping any binding.

        Args:
            decision_points: List of decision point objects
            bindings: All binding invariants with tags

        Returns:
            Filtered list of decision points
        """
        filtered = []

        for dp in decision_points:
            # Serialize to JSON for comprehensive text matching
            if isinstance(dp, dict):
                dp_text = json.dumps(dp).lower()
            else:
                dp_text = str(dp).lower()

            # Check if any binding tag is mentioned
            should_remove = False
            for binding in bindings:
                for tag in binding["tags"]:
                    if tag in dp_text:
                        logger.debug(
                            f"Removing decision point overlapping '{binding['id']}'"
                        )
                        should_remove = True
                        break
                if should_remove:
                    break

            if not should_remove:
                filtered.append(dp)

        return filtered
