"""Pure functions for PGC (Pre-Generation Clarification) data -- WS-CRAP-002.

Extracted from app/api/v1/routers/projects.py to enable Tier-1 testing.
These functions perform data transformations with no I/O, no DB, no logging.
"""

from typing import Any, Dict, List, Optional


def resolve_answer_label(question: Dict[str, Any], user_answer: Any) -> Optional[str]:
    """Resolve human-readable answer label from question choices.

    Maps raw answer values (IDs, booleans, lists) to display labels
    using the question's answer_type and choices configuration.
    """
    if user_answer is None:
        return None

    answer_type = question.get("answer_type", "free_text")
    choices = question.get("choices", [])

    if answer_type == "single_choice" and choices:
        for c in choices:
            if (c.get("id") or c.get("value")) == user_answer:
                return c.get("label", str(user_answer))
    elif answer_type == "multi_choice" and choices and isinstance(user_answer, list):
        choice_map = {(c.get("id") or c.get("value")): c.get("label") for c in choices}
        return ", ".join(choice_map.get(s, str(s)) for s in user_answer)
    elif answer_type == "yes_no" and isinstance(user_answer, bool):
        return "Yes" if user_answer else "No"

    if isinstance(user_answer, list):
        return ", ".join(str(s) for s in user_answer)
    return str(user_answer)


def build_pgc_from_answers(
    questions: List[Dict[str, Any]],
    answers: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Build clarifications from pgc_answers table data (newer format).

    Takes the raw questions list and answers dict from a PGCAnswer record
    and builds the unified clarification display format.
    """
    clarifications = []
    for q in questions:
        qid = q.get("id", "")
        user_answer = answers.get(qid)
        answer_label = resolve_answer_label(q, user_answer)

        clarifications.append({
            "question_id": qid,
            "question": q.get("text", ""),
            "why_it_matters": q.get("why_it_matters"),
            "answer": answer_label,
            "binding": q.get("constraint_kind") in ("exclusion", "requirement") or q.get("priority") == "must",
        })

    return clarifications


def build_pgc_from_context_state(context_state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build clarifications from workflow execution context_state (older format).

    Checks multiple keys where PGC data may be stored:
    - pgc_clarifications (newer context format)
    - document_pgc_clarifications.* (older context format)
    - pgc_questions + pgc_answers (raw data fallback)
    """
    # Try pgc_clarifications (newer context format, has full merged data)
    pgc_clars = context_state.get("pgc_clarifications", [])
    if pgc_clars:
        return [
            {
                "question_id": c.get("id", ""),
                "question": c.get("text", ""),
                "why_it_matters": c.get("why_it_matters"),
                "answer": c.get("user_answer_label") or str(c.get("user_answer", "")),
                "binding": c.get("binding", False),
            }
            for c in pgc_clars
            if c.get("resolved", True)
        ]

    # Try document_pgc_clarifications.* keys (older context format)
    for key, value in context_state.items():
        if key.startswith("document_pgc_clarifications.") and isinstance(value, dict):
            clars = value.get("clarifications", [])
            if clars:
                # Older format has questions in pgc_questions with why_it_matters
                questions_obj = context_state.get("pgc_questions", {})
                questions_list = questions_obj.get("questions", [])
                q_map = {q.get("id"): q for q in questions_list}

                return [
                    {
                        "question_id": c.get("id", ""),
                        "question": c.get("question", ""),
                        "why_it_matters": c.get("why_it_matters") or q_map.get(c.get("id"), {}).get("why_it_matters"),
                        "answer": resolve_answer_label(
                            q_map.get(c.get("id"), {}),
                            c.get("answer"),
                        ),
                        "binding": c.get("priority") == "must" or c.get("binding", False),
                    }
                    for c in clars
                ]

    # Raw fallback: pgc_questions + pgc_answers
    questions_obj = context_state.get("pgc_questions", {})
    raw_answers = context_state.get("pgc_answers", {})
    questions_list = questions_obj.get("questions", [])
    if questions_list and raw_answers:
        return [
            {
                "question_id": q.get("id", ""),
                "question": q.get("text", ""),
                "why_it_matters": q.get("why_it_matters"),
                "answer": resolve_answer_label(q, raw_answers.get(q.get("id"))),
                "binding": q.get("constraint_kind") in ("exclusion", "requirement") or q.get("priority") == "must",
            }
            for q in questions_list
        ]

    return []


def build_resolution_dict(
    answers: Optional[Dict[str, Any]],
    decision: Optional[str],
    notes: Optional[str],
    escalation_option: Optional[str],
) -> Dict[str, Any]:
    """Build interrupt resolution dict from request fields.

    Returns dict of non-None resolution fields.
    """
    resolution: Dict[str, Any] = {}
    if answers:
        resolution["answers"] = answers
    if decision:
        resolution["decision"] = decision
    if notes:
        resolution["notes"] = notes
    if escalation_option:
        resolution["escalation_option"] = escalation_option
    return resolution
