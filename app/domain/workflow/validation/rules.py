"""Validation rules and text matching utilities.

Per WS-PGC-VALIDATION-001 Phase 1.

Matching Algorithm (from WS):
- Extract keywords from text (nouns, verbs - exclude stopwords)
- Case-insensitive comparison
- Use simple word tokenization (split on whitespace/punctuation)
- Jaccard similarity for contradiction detection
"""

import re
from typing import Any, Dict, List, Optional, Set

from app.domain.workflow.validation.validation_result import ValidationIssue


# Common English stopwords to exclude from keyword extraction
STOPWORDS: Set[str] = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "been",
    "be", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "must", "shall", "can", "need",
    "it", "its", "this", "that", "these", "those", "i", "you", "he",
    "she", "we", "they", "what", "which", "who", "whom", "where", "when",
    "why", "how", "all", "each", "every", "both", "few", "more", "most",
    "other", "some", "such", "no", "not", "only", "same", "so", "than",
    "too", "very", "just", "also", "now", "here", "there", "then",
    "if", "else", "because", "about", "into", "through", "during",
    "before", "after", "above", "below", "between", "under", "again",
    "further", "once", "any", "our", "your", "their", "his", "her",
}

# Terms prohibited in unknowns/stakeholder_questions per policy
PROHIBITED_TERMS: Dict[str, List[str]] = {
    "budget": ["budget", "funding", "financial", "cost", "price", "expense", "money"],
    "authority": ["authority", "approval", "sign-off", "permission", "authorized", "approve"],
}


def extract_keywords(text: str) -> Set[str]:
    """Extract keywords from text, excluding stopwords.

    Args:
        text: Input text to extract keywords from

    Returns:
        Set of lowercase keywords
    """
    if not text:
        return set()

    # Tokenize: split on whitespace and punctuation
    tokens = re.findall(r'\b[a-zA-Z]+\b', text.lower())

    # Filter stopwords and very short words
    keywords = {t for t in tokens if t not in STOPWORDS and len(t) > 2}

    return keywords


def jaccard_similarity(set_a: Set[str], set_b: Set[str]) -> float:
    """Calculate Jaccard similarity between two sets.

    Jaccard = |intersection| / |union|

    Args:
        set_a: First set
        set_b: Second set

    Returns:
        Similarity score between 0.0 and 1.0
    """
    if not set_a and not set_b:
        return 0.0

    intersection = set_a & set_b
    union = set_a | set_b

    if not union:
        return 0.0

    return len(intersection) / len(union)


def keyword_overlap_ratio(source_keywords: Set[str], target_keywords: Set[str]) -> float:
    """Calculate what fraction of target keywords appear in source.

    Args:
        source_keywords: Keywords from the source (PGC answer, intake)
        target_keywords: Keywords from the target (constraint, guardrail)

    Returns:
        Fraction of target keywords found in source (0.0 to 1.0)
    """
    if not target_keywords:
        return 0.0

    overlap = source_keywords & target_keywords
    return len(overlap) / len(target_keywords)


def check_promotion_validity(
    constraints: List[Dict[str, Any]],
    pgc_questions: List[Dict[str, Any]],
    pgc_answers: Dict[str, Any],
    intake: Optional[Dict[str, Any]],
) -> List[ValidationIssue]:
    """Check that constraints trace to valid sources.

    A constraint is valid ONLY if:
    - It traces to a PGC question with priority="must" AND user provided answer
    - OR it is explicitly stated in the intake brief

    Args:
        constraints: List of known_constraints from document
        pgc_questions: Questions from PGC node
        pgc_answers: User's answers
        intake: Optional concierge intake

    Returns:
        List of validation issues (warnings for invalid promotions)
    """
    issues: List[ValidationIssue] = []

    # Build valid sources: must-priority answers + intake statements
    valid_source_keywords: List[Dict[str, Any]] = []

    # Add must-priority PGC answers as valid sources
    question_map = {q.get("id"): q for q in pgc_questions}
    for q_id, answer in pgc_answers.items():
        question = question_map.get(q_id)
        if not question:
            continue

        priority = question.get("priority", "").lower()
        if priority != "must":
            continue

        # Skip empty/null/undecided answers
        if answer is None or answer == "" or answer == "undecided":
            continue

        # Build keywords from question text and answer
        q_text = question.get("text", "") or question.get("question", "")
        answer_text = str(answer) if not isinstance(answer, bool) else ""
        combined_text = f"{q_text} {answer_text}"

        valid_source_keywords.append({
            "keywords": extract_keywords(combined_text),
            "source": f"PGC must-answer: {q_id}",
            "priority": "must",
        })

    # Add should-priority answers (to detect promotion from these)
    should_sources: List[Dict[str, Any]] = []
    for q_id, answer in pgc_answers.items():
        question = question_map.get(q_id)
        if not question:
            continue

        priority = question.get("priority", "").lower()
        if priority not in ("should", "could"):
            continue

        if answer is None or answer == "" or answer == "undecided":
            continue

        q_text = question.get("text", "") or question.get("question", "")
        answer_text = str(answer) if not isinstance(answer, bool) else ""
        combined_text = f"{q_text} {answer_text}"

        should_sources.append({
            "keywords": extract_keywords(combined_text),
            "source": f"PGC {priority}-answer: {q_id}",
            "priority": priority,
        })

    # Add intake statements as valid sources
    if intake:
        # Extract text from common intake fields
        intake_texts = []
        for field in ["description", "brief", "statement", "artifact_type", "audience"]:
            if field in intake and intake[field]:
                intake_texts.append(str(intake[field]))

        # Also check raw_inputs if present
        if "raw_inputs" in intake and isinstance(intake["raw_inputs"], list):
            intake_texts.extend(str(inp) for inp in intake["raw_inputs"])

        if intake_texts:
            combined_intake = " ".join(intake_texts)
            valid_source_keywords.append({
                "keywords": extract_keywords(combined_intake),
                "source": "intake",
                "priority": "stated",
            })

    # Check each constraint
    for constraint in constraints:
        constraint_id = constraint.get("id", "unknown")
        constraint_text = constraint.get("constraint", "") or constraint.get("text", "")

        if not constraint_text:
            continue

        constraint_keywords = extract_keywords(constraint_text)
        if not constraint_keywords:
            continue

        # Check against valid sources (must-answers and intake)
        best_valid_match = 0.0
        for source in valid_source_keywords:
            overlap = keyword_overlap_ratio(source["keywords"], constraint_keywords)
            best_valid_match = max(best_valid_match, overlap)

        # If >= 50% match to valid source, it's valid
        if best_valid_match >= 0.5:
            continue

        # Check if it matches a should/could source (promotion violation)
        best_should_match = 0.0
        matched_should_source = None
        for source in should_sources:
            overlap = keyword_overlap_ratio(source["keywords"], constraint_keywords)
            if overlap > best_should_match:
                best_should_match = overlap
                matched_should_source = source

        if best_should_match >= 0.5 and matched_should_source:
            # Promotion from should/could to constraint
            source_priority = matched_should_source['priority'].upper()
            match_pct = round(best_should_match * 100)
            confidence = "HIGH" if match_pct >= 80 else "MEDIUM" if match_pct >= 60 else "LOW"

            issues.append(ValidationIssue(
                severity="warning",
                check_type="promotion",
                section="known_constraints",
                field_id=constraint_id,
                message=f"Constraint appears derived from {matched_should_source['priority']}-priority answer, not must-priority",
                evidence={
                    "constraint": constraint_text,
                    "matched_source": matched_should_source["source"],
                    "source_priority": matched_should_source["priority"],
                    "match_ratio": round(best_should_match, 2),
                    # Rule identification
                    "rule_id": "QA-PGC-PROMOTION-002",
                    "rule_name": "Should/Could Answer Promotion",
                    # Source traceability
                    "expected_sources": ["PGC answer with priority=must", "Concierge intake hard constraint"],
                    "actual_source": f"PGC {matched_should_source['priority']}-priority answer ({match_pct}% match)",
                    # Decision support
                    "confidence": confidence,
                    "confidence_rationale": f"{match_pct}% keyword overlap with {source_priority} answer",
                    # Normalized promotion path
                    "promotion_path": f"PGC_{source_priority} -> PINNED",
                    "promotion_legitimacy": "UNAUTHORIZED",
                    # Promotion impact
                    "blocks_stabilization": False,
                    "requires_user_confirmation": True,
                    # Governance
                    "governance_ref": "ADR-042 S3.2",
                    "governance_title": "Constraint Promotion Rules",
                    # Rationale and guidance
                    "severity_rationale": f"Non-binding {source_priority}-answer promoted without must-priority justification",
                    "override_guidance": "If intentional: change PGC question priority to 'must', or add explicit intake constraint",
                },
            ))
        elif best_valid_match < 0.5:
            # No traceable source
            best_match = max(best_valid_match, best_should_match)
            match_pct = round(best_match * 100)
            confidence = "HIGH" if match_pct < 20 else "MEDIUM" if match_pct < 40 else "LOW"

            issues.append(ValidationIssue(
                severity="warning",
                check_type="promotion",
                section="known_constraints",
                field_id=constraint_id,
                message="Constraint has no traceable source in intake or must-priority answers",
                evidence={
                    "constraint": constraint_text,
                    "best_match_ratio": round(best_match, 2),
                    # Rule identification
                    "rule_id": "QA-PGC-PROMOTION-001",
                    "rule_name": "Untraceable Constraint",
                    # Source traceability
                    "expected_sources": ["PGC answer with priority=must", "Concierge intake hard constraint"],
                    "actual_source": f"Inferred from document text (best match: {match_pct}%)",
                    # Decision support
                    "confidence": confidence,
                    "confidence_rationale": f"No input source matched above 50% threshold (best: {match_pct}%)",
                    # Normalized promotion path
                    "promotion_path": "INFERRED -> PINNED",
                    "promotion_legitimacy": "UNAUTHORIZED",
                    # Promotion impact
                    "blocks_stabilization": False,
                    "requires_user_confirmation": True,
                    # Governance
                    "governance_ref": "ADR-042 S3.1",
                    "governance_title": "Constraint Binding Requirements",
                    # Rationale and guidance
                    "severity_rationale": "Constraint may be correct but lacks binding justification from governed input",
                    "override_guidance": f"If intentional: add explicit PGC must-priority question or concierge hard constraint for '{constraint_id}'",
                },
            ))

    return issues


def check_internal_contradictions(
    constraints: List[Dict[str, Any]],
    assumptions: List[Dict[str, Any]],
) -> List[ValidationIssue]:
    """Check that same concept doesn't appear in both constraints and assumptions.

    Uses Jaccard similarity > 0.5 to detect matching concepts.

    Args:
        constraints: List of known_constraints from document
        assumptions: List of assumptions from document

    Returns:
        List of validation issues (errors for contradictions)
    """
    issues: List[ValidationIssue] = []

    # Extract keywords for all items
    constraint_items = []
    for c in constraints:
        text = c.get("constraint", "") or c.get("text", "")
        if text:
            constraint_items.append({
                "id": c.get("id", "unknown"),
                "text": text,
                "keywords": extract_keywords(text),
            })

    assumption_items = []
    for a in assumptions:
        text = a.get("assumption", "") or a.get("text", "")
        if text:
            assumption_items.append({
                "id": a.get("id", "unknown"),
                "text": text,
                "keywords": extract_keywords(text),
            })

    # Compare each pair
    for c_item in constraint_items:
        for a_item in assumption_items:
            similarity = jaccard_similarity(c_item["keywords"], a_item["keywords"])

            if similarity > 0.5:
                issues.append(ValidationIssue(
                    severity="error",
                    check_type="contradiction",
                    section="known_constraints/assumptions",
                    field_id=f"{c_item['id']}/{a_item['id']}",
                    message="Same concept appears in both constraints and assumptions",
                    evidence={
                        "constraint_id": c_item["id"],
                        "constraint_text": c_item["text"],
                        "assumption_id": a_item["id"],
                        "assumption_text": a_item["text"],
                        "jaccard_similarity": round(similarity, 2),
                    },
                ))

    return issues


def check_policy_conformance(document: Dict[str, Any]) -> List[ValidationIssue]:
    """Check that document doesn't contain prohibited policy terms.

    Scans unknowns and stakeholder_questions for budget/authority terms.

    Args:
        document: The generated document

    Returns:
        List of validation issues (warnings for policy violations)
    """
    issues: List[ValidationIssue] = []

    # Sections to scan for prohibited terms
    sections_to_scan = ["unknowns", "stakeholder_questions", "open_questions"]

    for section_name in sections_to_scan:
        section = document.get(section_name)
        if not section:
            continue

        # Handle both list and dict formats
        items_to_check = []
        if isinstance(section, list):
            for item in section:
                if isinstance(item, dict):
                    text = item.get("question", "") or item.get("text", "") or item.get("unknown", "")
                    items_to_check.append((item.get("id", "unknown"), text))
                elif isinstance(item, str):
                    items_to_check.append(("unknown", item))
        elif isinstance(section, dict):
            for item_id, item in section.items():
                if isinstance(item, dict):
                    text = item.get("question", "") or item.get("text", "")
                else:
                    text = str(item)
                items_to_check.append((item_id, text))

        # Check each item for prohibited terms
        for item_id, text in items_to_check:
            text_lower = text.lower()

            for category, terms in PROHIBITED_TERMS.items():
                for term in terms:
                    if term in text_lower:
                        issues.append(ValidationIssue(
                            severity="warning",
                            check_type="policy",
                            section=section_name,
                            field_id=item_id,
                            message=f"Contains prohibited {category}-related term: '{term}'",
                            evidence={
                                "text": text,
                                "prohibited_term": term,
                                "category": category,
                            },
                        ))
                        break  # Only report once per category per item

    return issues


def check_grounding(
    guardrails: List[Dict[str, Any]],
    pgc_questions: List[Dict[str, Any]],
    pgc_answers: Dict[str, Any],
    intake: Optional[Dict[str, Any]],
) -> List[ValidationIssue]:
    """Check that MVP guardrails trace to explicit input.

    Uses same keyword matching as promotion validity check.

    Args:
        guardrails: List of mvp_guardrails from document
        pgc_questions: Questions from PGC node
        pgc_answers: User's answers
        intake: Optional concierge intake

    Returns:
        List of validation issues (warnings for ungrounded guardrails)
    """
    issues: List[ValidationIssue] = []

    # Build valid sources (same as promotion check, but include should-priority too)
    valid_source_keywords: List[Set[str]] = []

    # Add all PGC answers with explicit values as valid sources
    question_map = {q.get("id"): q for q in pgc_questions}
    for q_id, answer in pgc_answers.items():
        question = question_map.get(q_id)
        if not question:
            continue

        priority = question.get("priority", "").lower()
        if priority not in ("must", "should"):
            continue

        if answer is None or answer == "" or answer == "undecided":
            continue

        q_text = question.get("text", "") or question.get("question", "")
        answer_text = str(answer) if not isinstance(answer, bool) else ""
        combined_text = f"{q_text} {answer_text}"
        valid_source_keywords.append(extract_keywords(combined_text))

    # Add intake as valid source
    if intake:
        intake_texts = []
        for field in ["description", "brief", "statement", "artifact_type", "audience"]:
            if field in intake and intake[field]:
                intake_texts.append(str(intake[field]))

        if "raw_inputs" in intake and isinstance(intake["raw_inputs"], list):
            intake_texts.extend(str(inp) for inp in intake["raw_inputs"])

        if intake_texts:
            valid_source_keywords.append(extract_keywords(" ".join(intake_texts)))

    # Check each guardrail
    for guardrail in guardrails:
        guardrail_id = guardrail.get("id", "unknown")
        guardrail_text = guardrail.get("guardrail", "") or guardrail.get("text", "")

        if not guardrail_text:
            continue

        guardrail_keywords = extract_keywords(guardrail_text)
        if not guardrail_keywords:
            continue

        # Find best match
        best_match = 0.0
        for source_keywords in valid_source_keywords:
            overlap = keyword_overlap_ratio(source_keywords, guardrail_keywords)
            best_match = max(best_match, overlap)

        if best_match < 0.5:
            issues.append(ValidationIssue(
                severity="warning",
                check_type="grounding",
                section="mvp_guardrails",
                field_id=guardrail_id,
                message="Guardrail appears inferred rather than explicitly stated in input",
                evidence={
                    "guardrail": guardrail_text,
                    "best_match_ratio": round(best_match, 2),
                },
            ))

    return issues
