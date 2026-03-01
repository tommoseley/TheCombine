"""Pure functions for workflow result handling -- WS-CRAP-001 Target 1.

Extracted from PlanExecutor._handle_result() (CC=47, CRAP=2190.4) and
PlanExecutor._extract_qa_feedback().
These functions contain no I/O, no logging, and no side effects.
"""

from typing import Any, Dict, List, Optional


# Keys to extract from result metadata for Gate Profile resumption
GATE_PROFILE_KEYS = [
    "intake_gate_phase",
    "intake_classification",
    "extracted",
    "entry_op_ref",
    "user_input",
    "intake_operational_error",
    "reason",
]

# Keys to extract from result metadata for intake gate context
INTAKE_METADATA_KEYS = [
    "intake_summary",
    "project_type",
    "user_input",
    "intent_canon",
    "extracted_data",
    "interpretation",
    "phase",
    "intake_classification",
    "intake_confirmation",
    "artifact_type",
    "audience",
    "intake_gate_phase",
]


def extract_metadata_by_keys(
    metadata: Dict[str, Any],
    keys: List[str],
) -> Dict[str, Any]:
    """Extract a subset of metadata matching the given keys.

    Args:
        metadata: Source metadata dict
        keys: List of keys to extract

    Returns:
        Dict containing only the matching key-value pairs
    """
    return {k: metadata[k] for k in keys if k in metadata}


def extract_qa_feedback(metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract actionable QA feedback from failed result metadata.

    Builds a structured feedback object for remediation context.
    Handles drift errors, code validation errors, LLM QA errors,
    and semantic QA findings.

    Args:
        metadata: The result metadata dict (from NodeResult.metadata)

    Returns:
        Dict with issues, summary, and source -- or None if no issues
    """
    if not metadata:
        return None

    feedback: Dict[str, Any] = {
        "issues": [],
        "summary": "",
        "source": metadata.get("validation_source", "qa"),
    }

    # Extract drift validation errors (ADR-042)
    for err in metadata.get("drift_errors", []):
        feedback["issues"].append({
            "type": "constraint_drift",
            "check_id": err.get("check_id"),
            "message": err.get("message"),
            "remediation": err.get("remediation"),
        })

    # Extract code-based validation errors
    for err in metadata.get("validation_errors", []):
        feedback["issues"].append({
            "type": "validation",
            "check_id": err.get("check_id"),
            "message": err.get("message"),
        })

    # Extract LLM QA errors (list of strings or dicts)
    for err in metadata.get("errors", []):
        if isinstance(err, dict):
            feedback["issues"].append({
                "type": "llm_qa",
                "severity": err.get("severity", "error"),
                "section": err.get("section"),
                "message": err.get("message"),
            })
        elif isinstance(err, str):
            feedback["issues"].append({
                "type": "llm_qa",
                "message": err,
            })

    # Extract semantic QA findings (WS-SEMANTIC-QA-001)
    semantic_report = metadata.get("semantic_qa_report")
    if semantic_report:
        for finding in semantic_report.get("findings", []):
            if finding.get("severity") == "error":
                feedback["issues"].append({
                    "type": "semantic_qa",
                    "check_id": finding.get("code"),
                    "constraint_id": finding.get("constraint_id"),
                    "message": finding.get("message"),
                    "remediation": finding.get("suggested_fix"),
                    "evidence": finding.get("evidence_pointers", []),
                })

    # Extract feedback summary
    qa_feedback = metadata.get("feedback", {})
    if isinstance(qa_feedback, dict):
        feedback["summary"] = qa_feedback.get("llm_feedback", "")
    elif isinstance(qa_feedback, str):
        feedback["summary"] = qa_feedback

    if not feedback["issues"]:
        return None

    return feedback


def should_pause_for_intake_review(
    node_type_is_intake_gate: bool,
    result_phase: Optional[str],
    current_phase: Optional[str],
) -> bool:
    """Determine if execution should pause for intake review.

    Legacy INTAKE_GATE nodes pause when phase transitions to "review"
    and we're not already in "generating" phase.

    Args:
        node_type_is_intake_gate: Whether the current node is a legacy INTAKE_GATE
        result_phase: The phase from result metadata
        current_phase: The current phase from context_state

    Returns:
        True if should pause for review
    """
    if not node_type_is_intake_gate:
        return False
    return result_phase == "review" and current_phase != "generating"
