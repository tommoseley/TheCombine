"""Pure data transformation for constraint pinning and duplicate detection.

Extracted from plan_executor._pin_invariants_to_known_constraints() for
testability (WS-CRAP-007). No I/O, no DB, no logging.
"""

import copy
from typing import Any, Dict, List, Set, Tuple


def build_pinned_constraints(
    invariants: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], Set[str]]:
    """Build canonical pinned constraints from PGC invariants.

    Args:
        invariants: List of binding invariants from context_state

    Returns:
        Tuple of (pinned_constraints list, pinned_keywords set for dedup)
    """
    pinned_constraints = []
    pinned_keywords: Set[str] = set()

    for inv in invariants:
        constraint_id = inv.get("id", "UNKNOWN")
        answer_label = inv.get("user_answer_label") or str(inv.get("user_answer", ""))

        if not answer_label:
            continue

        # Use normalized_text if available, otherwise clean format
        normalized = inv.get("normalized_text")
        constraint_text = normalized if normalized else answer_label

        # Add as structured constraint with clean text
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
        # Add constraint ID parts (e.g., PLATFORM -> platform, TARGET -> target)
        for part in constraint_id.split("_"):
            if len(part) > 2:
                pinned_keywords.add(part.lower())

    return pinned_constraints, pinned_keywords


def is_duplicate_of_pinned(
    constraint: Any,
    pinned_keywords: Set[str],
) -> bool:
    """Check if an LLM constraint duplicates a pinned constraint.

    Uses keyword overlap: if 2+ pinned keywords appear in the constraint
    text, it is considered a duplicate.

    Args:
        constraint: An LLM-generated constraint (str or dict)
        pinned_keywords: Set of keywords from pinned constraints

    Returns:
        True if the constraint is a duplicate
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
    return matches >= 2


def filter_duplicate_constraints(
    llm_constraints: List[Any],
    pinned_keywords: Set[str],
) -> Tuple[List[Any], int]:
    """Filter LLM constraints that duplicate pinned constraints.

    Args:
        llm_constraints: List of LLM-generated constraints
        pinned_keywords: Set of keywords from pinned constraints

    Returns:
        Tuple of (filtered non-duplicate constraints, count removed)
    """
    filtered = []
    removed_count = 0
    for kc in llm_constraints:
        if is_duplicate_of_pinned(kc, pinned_keywords):
            removed_count += 1
        else:
            filtered.append(kc)
    return filtered, removed_count


def pin_invariants_to_constraints(
    document: Dict[str, Any],
    invariants: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Pin binding invariants into document's known_constraints[].

    Pure function: builds canonical pinned constraints from invariants,
    removes duplicate LLM constraints, and merges them.

    Args:
        document: The produced document (will be deep-copied, not mutated)
        invariants: List of binding invariants from context_state

    Returns:
        Document copy with clean known_constraints (pinned + non-duplicate LLM)
    """
    if not invariants:
        return document

    pinned = copy.deepcopy(document)

    llm_constraints = pinned.get("known_constraints", [])
    if not isinstance(llm_constraints, list):
        llm_constraints = []

    pinned_constraints, pinned_keywords = build_pinned_constraints(invariants)
    filtered_llm, removed_count = filter_duplicate_constraints(
        llm_constraints, pinned_keywords
    )

    final_constraints = pinned_constraints + filtered_llm
    pinned["known_constraints"] = final_constraints

    return pinned
