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


# ---------------------------------------------------------------------------
# Pure functions (extracted for testability — WS-CRAP-004)
# ---------------------------------------------------------------------------

def is_duplicate_constraint(
    constraint: Any,
    pinned_keywords: set,
    threshold: int,
) -> bool:
    """Check if a constraint duplicates pinned constraints.

    Pure function — no I/O, no side effects.

    Args:
        constraint: The LLM constraint (string or dict)
        pinned_keywords: Keywords from pinned constraints
        threshold: Minimum keyword matches to consider duplicate

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


def build_pinned_constraints(invariants: list) -> tuple:
    """Build pinned constraints and keyword set from invariants.

    Pure function — no I/O, no side effects.

    Args:
        invariants: List of binding invariant dicts

    Returns:
        Tuple of (pinned_constraints list, pinned_keywords set)
    """
    pinned_constraints = []
    pinned_keywords = set()

    for inv in invariants:
        constraint_id = inv.get("id", "UNKNOWN")
        answer_label = inv.get("user_answer_label") or str(inv.get("user_answer", ""))

        if not answer_label:
            continue

        normalized = inv.get("normalized_text")
        constraint_text = normalized if normalized else answer_label

        pinned_constraints.append({
            "text": constraint_text,
            "source": "user_clarification",
            "constraint_id": constraint_id,
            "binding": True,
        })

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

    return pinned_constraints, pinned_keywords


def pin_invariants(
    document: dict,
    invariants: list,
    *,
    deduplicate: bool = True,
    keyword_threshold: int = 2,
) -> dict:
    """Pin binding invariants into document's known_constraints.

    Pure function — no I/O, no logging, no side effects.
    Deep-copies document internally to avoid mutation.

    Args:
        document: Document dict to pin into
        invariants: List of binding invariant dicts
        deduplicate: Whether to remove LLM constraints that duplicate pinned
        keyword_threshold: Minimum keyword matches for duplicate detection

    Returns:
        Modified document dict with pinned constraints prepended
    """
    pinned = copy.deepcopy(document)

    llm_constraints = pinned.get("known_constraints", [])
    if not isinstance(llm_constraints, list):
        llm_constraints = []

    pinned_constraints, pinned_keywords = build_pinned_constraints(invariants)

    if deduplicate and pinned_keywords:
        filtered_llm = [
            kc for kc in llm_constraints
            if not is_duplicate_constraint(kc, pinned_keywords, keyword_threshold)
        ]
    else:
        filtered_llm = llm_constraints

    pinned["known_constraints"] = pinned_constraints + filtered_llm
    return pinned


# ---------------------------------------------------------------------------
# Handler class
# ---------------------------------------------------------------------------

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
        """Execute the invariant pinning operation."""
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

        if not invariants:
            return MechResult.ok(output=document)

        if not isinstance(invariants, list):
            return MechResult.fail(
                error="Input 'invariants' must be a list",
                error_code="invalid_input",
            )

        deduplicate = config.get("deduplicate", True)
        keyword_threshold = config.get("keyword_match_threshold", 2)

        try:
            result = pin_invariants(
                document,
                invariants,
                deduplicate=deduplicate,
                keyword_threshold=keyword_threshold,
            )
            return MechResult.ok(output=result)

        except Exception as e:
            logger.exception(f"Invariant pinning failed: {e}")
            return MechResult.fail(
                error=str(e),
                error_code="execution_error",
            )
