"""Invariant Pinner Handler.

Per WS-ADR-047-004 Phase 2: Specialized handler for pinning binding
invariants into document known_constraints, with duplicate detection.

This handler extracts the pinning logic from plan_executor.py's
_pin_invariants_to_known_constraints method.
"""

import copy
import logging
from typing import Any, Dict

from app.api.services.mech_handlers.base import (
    ExecutionContext,
    MechHandler,
    MechResult,
)
from app.api.services.mech_handlers.registry import register_handler

logger = logging.getLogger(__name__)


@register_handler
class InvariantPinnerHandler(MechHandler):
    """Handler for invariant_pinner operations.

    Pins binding invariants into document's known_constraints[],
    removing LLM-generated constraints that duplicate pinned ones.
    """

    operation_type = "invariant_pinner"

    async def execute(
        self,
        config: Dict[str, Any],
        context: ExecutionContext,
    ) -> MechResult:
        """Execute the invariant pinning operation.

        Args:
            config: Operation configuration with:
                - deduplicate: bool (default True)
                - keyword_match_threshold: int (default 2)
            context: Execution context with inputs:
                - document: Document to pin invariants into
                - invariants: List of binding invariants

        Returns:
            MechResult with output containing the modified document
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

        # Handle missing or empty invariants
        if not invariants:
            return MechResult.ok(output=document)

        if not isinstance(invariants, list):
            return MechResult.fail(
                error="Input 'invariants' must be a list",
                error_code="invalid_input",
            )

        # Get config options
        deduplicate = config.get("deduplicate", True)
        keyword_threshold = config.get("keyword_match_threshold", 2)

        try:
            # Work on a copy to avoid mutating the original
            pinned = copy.deepcopy(document)

            # Get existing LLM-generated constraints
            llm_constraints = pinned.get("known_constraints", [])
            if not isinstance(llm_constraints, list):
                llm_constraints = []

            # Build canonical pinned constraints from invariants
            pinned_constraints = []
            pinned_keywords = set()

            for inv in invariants:
                constraint_id = inv.get("id", "UNKNOWN")
                answer_label = inv.get("user_answer_label") or str(inv.get("user_answer", ""))

                if not answer_label:
                    continue

                # Use normalized_text if available
                normalized = inv.get("normalized_text")
                constraint_text = normalized if normalized else answer_label

                # Add as structured constraint
                pinned_constraints.append({
                    "text": constraint_text,
                    "source": "user_clarification",
                    "constraint_id": constraint_id,
                    "binding": True,
                })

                # Build keywords for duplicate detection
                for word in answer_label.lower().split():
                    if len(word) > 3:
                        pinned_keywords.add(word)
                if normalized:
                    for word in normalized.lower().split():
                        if len(word) > 3:
                            pinned_keywords.add(word)
                for part in constraint_id.split("_"):
                    if len(part) > 2:
                        pinned_keywords.add(part.lower())

            # Filter duplicates if enabled
            if deduplicate and pinned_keywords:
                filtered_llm = []
                removed_count = 0

                for kc in llm_constraints:
                    if self._is_duplicate(kc, pinned_keywords, keyword_threshold):
                        removed_count += 1
                        logger.debug(f"Removed duplicate LLM constraint: {kc}")
                    else:
                        filtered_llm.append(kc)

                logger.info(
                    f"Invariant pinner: {len(pinned_constraints)} pinned, "
                    f"{removed_count} duplicates removed, {len(filtered_llm)} LLM kept"
                )
            else:
                filtered_llm = llm_constraints

            # Final list: pinned first, then filtered LLM
            pinned["known_constraints"] = pinned_constraints + filtered_llm

            return MechResult.ok(output=pinned)

        except Exception as e:
            logger.exception(f"Invariant pinning failed: {e}")
            return MechResult.fail(
                error=str(e),
                error_code="execution_error",
            )

    def _is_duplicate(
        self,
        constraint: Any,
        pinned_keywords: set,
        threshold: int,
    ) -> bool:
        """Check if a constraint duplicates pinned constraints.

        Args:
            constraint: The LLM constraint (string or dict)
            pinned_keywords: Keywords from pinned constraints
            threshold: Minimum matches to consider duplicate

        Returns:
            True if constraint is a duplicate
        """
        if isinstance(constraint, str):
            text = constraint.lower()
        elif isinstance(constraint, dict):
            text = " ".join([
                str(constraint.get("text", "")),
                str(constraint.get("constraint", "")),
                str(constraint.get("description", "")),
            ]).lower()
        else:
            return False

        matches = sum(1 for kw in pinned_keywords if kw in text)
        return matches >= threshold
