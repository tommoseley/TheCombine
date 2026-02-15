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

        # Get answer label for use in normalization
        answer_label = _get_answer_label(question, user_answer)
        
        # ADR-042 Fix #3: Derive exclusion normalization for binding constraints
        invariant_kind = None
        normalized_text = None
        canonical_tags = None
        
        if binding:
            invariant_kind, normalized_text, canonical_tags = _derive_exclusion_normalization(
                question_id=question_id,
                question_text=question.get("text", ""),
                answer=user_answer,
                answer_label=answer_label,
            )
        
        # Build the merged clarification
        clarification = {
            "id": question_id,
            "text": question.get("text", ""),
            "why_it_matters": question.get("why_it_matters"),
            "priority": question.get("priority", "could"),
            "answer_type": question.get("answer_type", "free_text"),
            "constraint_kind": question.get("constraint_kind", "selection"),
            "choices": question.get("choices"),
            "user_answer": user_answer,
            "user_answer_label": answer_label,
            "resolved": resolved,
            "binding": binding,
            "binding_source": binding_source,
            "binding_reason": binding_reason,
            # ADR-042 exclusion normalization fields
            "invariant_kind": invariant_kind,
            "normalized_text": normalized_text,
            "canonical_tags": canonical_tags,
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


def _derive_exclusion_normalization(
    question_id: str,
    question_text: str,
    answer: Any,
    answer_label: Optional[str],
) -> Tuple[str, str, List[str]]:
    """Derive exclusion normalization fields for binding constraints.
    
    ADR-042 Fix #3: Converts "No" answers into explicit exclusion invariants
    with canonical tags for structural QA validation.
    
    Args:
        question_id: The constraint ID (e.g., "EXISTING_SYSTEMS")
        question_text: The question text for context
        answer: Raw user answer
        answer_label: Human-readable answer label
        
    Returns:
        Tuple of (invariant_kind, normalized_text, canonical_tags)
    """
    # Determine if this is an exclusion (answer is "No" or False)
    is_exclusion = False
    if isinstance(answer, bool) and answer is False:
        is_exclusion = True
    elif isinstance(answer, str) and answer.lower().strip() in ("no", "none", "n/a", "not required"):
        is_exclusion = True
    elif answer_label and answer_label.lower().strip() in ("no", "none", "n/a", "not required"):
        is_exclusion = True
    
    # Derive canonical tags from question_id AND answer_label
    # Answer-derived tags are more specific and reduce false positives
    # E.g., MATH_SCOPE with answer "Addition, Subtraction" -> ["addition", "subtraction"]
    canonical_tags = _derive_canonical_tags(question_id, answer_label)
    
    if is_exclusion:
        invariant_kind = "exclusion"
        # Build normalized exclusion text
        # E.g., "No integrations with existing systems are in scope."
        normalized_text = _build_exclusion_text(question_id, question_text)
    else:
        invariant_kind = "requirement"
        # Build normalized requirement text
        # E.g., "MATH_CONCEPTS: Counting (1-10, 1-20, 1-100), Addition, Subtraction"
        normalized_text = f"{question_id}: {answer_label}" if answer_label else f"{question_id}: {answer}"
    
    return invariant_kind, normalized_text, canonical_tags


# Generic words that appear in constraint IDs but are too common to be meaningful tags
TAG_STOPWORDS = {
    # Generic descriptors
    "scope", "target", "type", "level", "needs", "requirements",
    "platform", "kind", "mode", "style", "format", "status",
    "count", "size", "range", "limit", "area", "zone",
    "primary", "secondary", "main", "other", "additional",
    "current", "new", "old", "default", "custom",
    # Common software/domain terms that appear everywhere
    "user", "users", "context", "data", "system", "systems",
    "feature", "features", "app", "application", "service",
    "project", "document", "config", "settings", "options",
}


def _derive_canonical_tags(question_id: str, answer_label: Optional[str] = None) -> List[str]:
    """Derive canonical tags from question ID and answer content.
    
    PRIORITY: Answer-derived tags take precedence over ID-derived tags.
    Answer content is specific (e.g., "Addition, Subtraction") while
    question IDs are generic (e.g., "MATH_SCOPE").
    
    Tags are used for structural QA matching. Generic words are filtered.
    
    Args:
        question_id: E.g., "EXISTING_SYSTEMS", "MATH_CONCEPTS"
        answer_label: E.g., "Number counting, Basic addition, Basic subtraction"
        
    Returns:
        List of lowercase tags (excluding stopwords)
    """
    import re
    
    all_tags = []
    
    # 1. Extract tags from answer_label (PRIORITY - most specific)
    if answer_label:
        # Split on commas, "and", parentheses, common separators
        answer_parts = re.split(r'[,;()]|\band\b', answer_label.lower())
        for part in answer_parts:
            # Extract meaningful words (3+ chars, not stopwords)
            words = re.findall(r'\b[a-z]{3,}\b', part)
            for word in words:
                if word not in TAG_STOPWORDS and len(word) > 3:
                    all_tags.append(word)
    
    # 2. Extract tags from question_id (fallback - more generic)
    id_tags = [t.lower() for t in question_id.split("_") if t]
    id_tags = [t for t in id_tags if t not in TAG_STOPWORDS]
    
    # Only use ID tags if we got nothing specific from the answer
    # This prevents generic ID words like "math" from causing false positives
    if not all_tags:
        all_tags.extend(id_tags)
    
    # 3. Add semantic aliases for answer-derived tags only
    # (ID-derived aliases are too broad)
    tag_aliases = {
        "counting": ["count", "numbers"],
        "addition": ["add", "plus"],
        "subtraction": ["subtract", "minus"],
        "accessibility": ["wcag", "a11y"],
        "integration": ["integrations", "external"],
    }
    
    expanded_tags = list(all_tags)
    for tag in all_tags:
        if tag in tag_aliases:
            expanded_tags.extend(tag_aliases[tag])
    
    # If all tags were filtered, this constraint can't be validated via tags
    # The constraint will still be enforced via pinning and exclusion filtering
    if not expanded_tags:
        logger.debug(f"ADR-042: No tags derived for {question_id}, skipping tag-based validation")
        return []
    
    return list(set(expanded_tags))  # Deduplicate


def _build_exclusion_text(question_id: str, question_text: str) -> str:
    """Build normalized exclusion text from question context.
    
    Args:
        question_id: The constraint ID
        question_text: The original question text
        
    Returns:
        Normalized exclusion statement
    """
    # Common patterns for exclusion normalization
    exclusion_templates = {
        "EXISTING_SYSTEMS": "No integrations with existing systems are in scope.",
        "PLATFORM": "No specific platform constraints apply.",
        "AUTH": "No authentication requirements specified.",
        "COMPLIANCE": "No compliance requirements specified.",
    }
    
    # Check for exact match first
    if question_id in exclusion_templates:
        return exclusion_templates[question_id]
    
    # Check for partial match
    for key, template in exclusion_templates.items():
        if key in question_id:
            return template
    
    # Fallback: generic exclusion based on question ID
    readable_id = question_id.replace("_", " ").lower()
    return f"No {readable_id} requirements are in scope."


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
