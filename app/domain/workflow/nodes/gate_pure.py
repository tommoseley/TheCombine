"""Pure data transformation for PGC gate node.

Extracted from gate._execute_pgc_gate() for testability (WS-CRAP-007).
No I/O, no DB, no logging, no LLM calls.
"""

from typing import Any, Callable, Dict, List, Optional, Tuple


def merge_questions_with_answers(
    pgc_questions: Dict[str, Any],
    pgc_answers: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Merge PGC questions with user answers into clarifications document.

    Phase 3 of PGC gate: combines the generated questions with user-provided
    answers into a structured clarifications document.

    Args:
        pgc_questions: Dict with "questions" key containing list of question dicts
        pgc_answers: Dict mapping question ID to answer value

    Returns:
        Tuple of (merged_clarifications list, clarifications_doc dict)
    """
    questions_list = pgc_questions.get("questions", [])
    merged_clarifications = []

    for q in questions_list:
        q_id = q.get("id", "")
        answer = pgc_answers.get(q_id, "")
        merged_clarifications.append({
            "id": q_id,
            "question": q.get("text", q.get("question", "")),
            "answer": answer,
            "priority": q.get("priority", "should"),
            "why_it_matters": q.get("why_it_matters", ""),
        })

    clarifications_doc = {
        "schema_version": "pgc_clarifications.v1",
        "clarifications": merged_clarifications,
        "question_count": len(questions_list),
        "answered_count": len([c for c in merged_clarifications if c.get("answer")]),
    }

    return merged_clarifications, clarifications_doc


def build_pgc_task_config(
    pass_a: Dict[str, Any],
    produces: str,
    resolve_urn_fn: Callable[[str], str],
) -> Dict[str, Any]:
    """Build the task node configuration for PGC pass_a execution.

    Resolves URN-style references to file paths and assembles the
    config dict expected by TaskNodeExecutor.

    Args:
        pass_a: The pass_a internal config from node_config
        produces: The produces key for the output
        resolve_urn_fn: Callable to resolve URN references to file paths

    Returns:
        Task node config dict
    """
    task_ref = resolve_urn_fn(pass_a.get("template_ref", ""))
    includes = {}
    for key, value in pass_a.get("includes", {}).items():
        includes[key] = resolve_urn_fn(value)

    # Add OUTPUT_SCHEMA from output_schema_ref if present (v2 workflow format)
    if pass_a.get("output_schema_ref"):
        includes["OUTPUT_SCHEMA"] = resolve_urn_fn(pass_a.get("output_schema_ref"))

    return {
        "type": "pgc",
        "task_ref": task_ref,
        "includes": includes,
        "produces": produces,
    }


def determine_pgc_phase(
    pgc_questions: Optional[Dict[str, Any]],
    pgc_answers: Optional[Dict[str, Any]],
) -> str:
    """Determine the current PGC gate phase based on context state.

    Args:
        pgc_questions: Questions from context_state (None if not yet generated)
        pgc_answers: Answers from context_state (None if not yet collected)

    Returns:
        Phase string: "merge", "entry", or "pass_a"
    """
    if pgc_questions and pgc_answers:
        return "merge"
    elif pgc_questions and not pgc_answers:
        return "entry"
    else:
        return "pass_a"
