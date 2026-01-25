"""Mechanical merge of PGC questions and answers into clarifications.

Per ADR-042 and WS-ADR-042-001 Phase 2.

This module provides deterministic (no LLM, no NLP) merging of PGC questions
with user answers, deriving binding status from schema fields only.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def merge_clarifications(
    questions: List[Dict[str, Any]],
    answers: Dict[str, Any],
    execution_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Merge PGC questions with user answers into clarifications.

    Args:
        questions: List of PGC question objects from the question set
        answers: Dict mapping question ID to user's answer
        execution_id: Optional workflow execution ID for traceability
        workflow_id: Optional workflow definition ID

    Returns:
        List of merged clarification objects with binding status
    """
    clarifications = []

    for question in questions:
        question_id = question.get("id")
        if not question_id:
            logger.warning("Skipping question without ID")
            continue

        # Get user's answer (may be None if not answered)
        user_answer = answers.get(question_id)

        # Determine if resolved
        resolved = _is_resolved(user_answer)

        # Derive binding status
        binding, binding_source, binding_reason = _derive_binding(
            question=question,
            answer=user_answer,
            resolved=resolved,
        )

        # Build the merged clarification
        clarification = {
            "id": question_id,
            "text": question.get("text", ""),
            "priority": question.get("priority", "could"),
            "answer_type": question.get("answer_type", "free_text"),
            "constraint_kind": question.get("constraint_kind", "selection"),
            "choices": question.get("choices"),
            "user_answer": user_answer,
            "user_answer_label": _get_answer_label(question, user_answer),
            "resolved": resolved,
            "binding": binding,
            "binding_source": binding_source,
            "binding_reason": binding_reason,
        }

        clarifications.append(clarification)

    logger.info(
        f"ADR-042: Merged {len(clarifications)} clarifications from "
        f"{len(questions)} questions and {len(answers)} answers"
    )

    return clarifications


def extract_invariants(clarifications: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract binding constraints from merged clarifications.

    Args:
        clarifications: List of merged clarification objects

    Returns:
        List of clarifications where binding=true
    """
    invariants = [c for c in clarifications if c.get("binding", False)]

    logger.info(
        f"ADR-042: Extracted {len(invariants)} binding invariants "
        f"from {len(clarifications)} clarifications"
    )

    return invariants


def _derive_binding(
    question: Dict[str, Any],
    answer: Any,
    resolved: bool,
) -> Tuple[bool, Optional[str], str]:
    """Derive binding status from question schema fields.

    Rules per ADR-042 Section 3 (in order of precedence):
    1. Not resolved -> binding=False
    2. constraint_kind == "exclusion" AND resolved -> binding=True
    3. constraint_kind == "requirement" AND resolved -> binding=True
    4. priority == "must" AND resolved -> binding=True
    5. Otherwise -> binding=False

    Args:
        question: The PGC question object
        answer: User's answer value
        resolved: Whether the question is resolved

    Returns:
        Tuple of (binding, binding_source, binding_reason)
    """
    if not resolved:
        return False, None, "not resolved"

    # Check explicit constraint_kind from question schema (preferred)
    constraint_kind = question.get("constraint_kind", "selection")

    if constraint_kind == "exclusion":
        return True, "exclusion", "explicit exclusion constraint"

    if constraint_kind == "requirement":
        return True, "requirement", "explicit requirement constraint"

    # Priority-based binding
    priority = question.get("priority", "could")
    if priority == "must":
        return True, "priority", "must-priority question with resolved answer"

    return False, None, f"{priority}-priority is informational only"


def _is_resolved(answer: Any) -> bool:
    """Determine if an answer represents a resolved question.

    Args:
        answer: The user's answer value

    Returns:
        True if the answer is a meaningful resolution
    """
    if answer is None:
        return False

    if isinstance(answer, str):
        # Empty string or "undecided" is not resolved
        normalized = answer.strip().lower()
        if normalized == "" or normalized == "undecided":
            return False

    if isinstance(answer, list):
        # Empty list is not resolved
        return len(answer) > 0

    # Any other value (bool, number, non-empty string, dict) is resolved
    return True


def _get_answer_label(question: Dict[str, Any], answer: Any) -> Optional[str]:
    """Get human-readable label for an answer.

    For choice-type questions, looks up the label from choices.
    For other types, returns string representation.

    Args:
        question: The PGC question object
        answer: User's answer value

    Returns:
        Human-readable label or None if not resolvable
    """
    if answer is None:
        return None

    answer_type = question.get("answer_type", "free_text")
    choices = question.get("choices", [])

    if answer_type == "single_choice" and choices:
        # Look up label from choices
        for choice in choices:
            # Handle both 'id' and 'value' as choice identifier
            choice_id = choice.get("id") or choice.get("value")
            if choice_id == answer:
                return choice.get("label", str(answer))
        return str(answer)

    if answer_type == "multi_choice" and choices and isinstance(answer, list):
        # Look up labels for all selected choices
        labels = []
        choice_map = {
            (c.get("id") or c.get("value")): c.get("label")
            for c in choices
        }
        for selected in answer:
            labels.append(choice_map.get(selected, str(selected)))
        return ", ".join(labels)

    if answer_type == "yes_no":
        if isinstance(answer, bool):
            return "Yes" if answer else "No"
        return str(answer)

    # For free_text and other types, just stringify
    if isinstance(answer, str):
        return answer
    return str(answer)


def build_clarifications_document(
    clarifications: List[Dict[str, Any]],
    execution_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a complete clarifications document per schema.

    Args:
        clarifications: List of merged clarification objects
        execution_id: Optional workflow execution ID
        workflow_id: Optional workflow definition ID

    Returns:
        Document conforming to pgc_clarifications.v1.json schema
    """
    invariants = extract_invariants(clarifications)

    return {
        "schema_version": "pgc_clarifications.v1",
        "execution_id": execution_id,
        "workflow_id": workflow_id,
        "merged_at": datetime.now(timezone.utc).isoformat(),
        "clarifications": clarifications,
        "invariants": invariants,
    }
