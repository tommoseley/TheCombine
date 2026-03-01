"""Pure data transformation for semantic QA node.

Extracted from qa._run_semantic_qa() for testability (WS-CRAP-007).
No I/O, no DB, no logging, no LLM calls.
"""

import json
from typing import Any, Dict, List, Tuple


def extract_semantic_qa_inputs(
    context_state: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    """Extract invariants, PGC questions, and PGC answers from context_state.

    Args:
        context_state: Workflow context state dict

    Returns:
        Tuple of (invariants, pgc_questions, pgc_answers)
    """
    invariants = context_state.get("pgc_invariants", [])

    raw_pgc_questions = context_state.get("pgc_questions", [])
    if isinstance(raw_pgc_questions, dict):
        pgc_questions = raw_pgc_questions.get("questions", [])
    else:
        pgc_questions = raw_pgc_questions

    pgc_answers = context_state.get("pgc_answers", {})

    return invariants, pgc_questions, pgc_answers


def build_semantic_qa_prompt(
    pgc_questions: List[Dict[str, Any]],
    pgc_answers: Dict[str, Any],
    invariants: List[Dict[str, Any]],
    document: Dict[str, Any],
    correlation_id: str,
    policy_prompt: str,
) -> str:
    """Assemble the full prompt string for semantic QA LLM call.

    Args:
        pgc_questions: PGC question definitions
        pgc_answers: User answers keyed by question ID
        invariants: Bound constraints to evaluate
        document: Generated document to audit
        correlation_id: Workflow correlation ID
        policy_prompt: The loaded semantic QA policy prompt text

    Returns:
        Formatted message content for LLM
    """
    parts = [policy_prompt]

    # PGC Questions with answers
    parts.append("\n\n---\n\n## PGC Questions and Answers\n")
    for q in pgc_questions:
        qid = q.get("id", "UNKNOWN")
        answer = pgc_answers.get(qid)
        priority = q.get("priority", "could")
        answer_label = ""
        if isinstance(answer, dict):
            answer_label = answer.get("label", str(answer))
        elif answer is not None:
            answer_label = str(answer)
        parts.append(f"- {qid} (priority={priority}): {answer_label}\n")

    # Bound constraints
    parts.append("\n## Bound Constraints (MUST evaluate each)\n")
    for inv in invariants:
        cid = inv.get("id", "UNKNOWN")
        kind = inv.get("invariant_kind", "requirement")
        text = (
            inv.get("normalized_text")
            or inv.get("user_answer_label")
            or str(inv.get("user_answer", ""))
        )
        parts.append(f"- {cid} [{kind}]: {text}\n")

    # Document
    parts.append("\n## Generated Document\n```json\n")
    parts.append(json.dumps(document, indent=2))
    parts.append("\n```\n")

    # Correlation ID and output instructions
    parts.append(f"\ncorrelation_id for output: {correlation_id}\n")
    parts.append(
        "\nOutput ONLY valid JSON matching qa_semantic_compliance_output.v1 schema. No prose.\n"
    )

    return "".join(parts)


def build_error_report(
    correlation_id: str,
    invariant_count: int,
    error: Exception,
) -> Dict[str, Any]:
    """Build a failing semantic QA report for error cases.

    Args:
        correlation_id: Workflow correlation ID
        invariant_count: Number of invariants that were to be evaluated
        error: The exception that occurred

    Returns:
        Dict conforming to qa_semantic_compliance_output.v1 schema
    """
    return {
        "schema_version": "qa_semantic_compliance_output.v1",
        "correlation_id": correlation_id,
        "gate": "fail",
        "summary": {
            "errors": 1,
            "warnings": 0,
            "infos": 0,
            "expected_constraints": invariant_count,
            "evaluated_constraints": 0,
            "blocked_reasons": [f"Semantic QA error: {str(error)}"],
        },
        "coverage": {
            "expected_count": invariant_count,
            "evaluated_count": 0,
            "items": [],
        },
        "findings": [
            {
                "severity": "error",
                "code": "OTHER",
                "constraint_id": "SYSTEM",
                "message": f"Semantic QA execution failed: {str(error)}",
                "evidence_pointers": [],
            }
        ],
    }
