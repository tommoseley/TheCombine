"""Pure data transformation for document assembly before persistence.

Extracted from plan_executor._persist_produced_documents() for testability
(WS-CRAP-007). No I/O, no DB, no logging.
"""

import copy
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


def enforce_system_meta(
    doc_content: Dict[str, Any],
    execution_id: str,
    document_type: str,
    workflow_id: str,
    system_created_at: Optional[str] = None,
) -> Tuple[Dict[str, Any], List[str]]:
    """Enforce system-owned meta fields on a document.

    System-owned fields (meta.created_at, meta.artifact_id) are overwritten
    with system values -- the LLM must not mint these.

    Args:
        doc_content: Document content dict (will be deep-copied, not mutated)
        execution_id: Workflow execution ID
        document_type: Document type string
        workflow_id: Workflow ID string
        system_created_at: Optional override for created_at (ISO format).
            Defaults to utcnow if not provided.

    Returns:
        Tuple of (modified doc_content copy, list of warning messages)
    """
    doc = copy.deepcopy(doc_content)
    warnings = []

    if "meta" not in doc:
        doc["meta"] = {}

    meta = doc["meta"]

    # System-owned: created_at
    if system_created_at is None:
        system_created_at = datetime.utcnow().isoformat() + "Z"

    llm_created_at = meta.get("created_at")
    if llm_created_at and llm_created_at != system_created_at:
        warnings.append(
            f"LLM minted meta.created_at={llm_created_at}, "
            f"overwriting with system value"
        )
    meta["created_at"] = system_created_at

    # System-owned: artifact_id
    system_artifact_id = f"{document_type.upper()}-{execution_id}"
    llm_artifact_id = meta.get("artifact_id")
    if llm_artifact_id and llm_artifact_id != system_artifact_id:
        warnings.append(
            f"LLM minted meta.artifact_id={llm_artifact_id}, "
            f"overwriting with system value"
        )
    meta["artifact_id"] = system_artifact_id

    # Provenance
    meta["correlation_id"] = execution_id
    meta["workflow_id"] = workflow_id

    return doc, warnings


def derive_document_title(
    doc_content: Dict[str, Any],
    document_type: str,
    project_name: Optional[str] = None,
    doc_type_display_name: Optional[str] = None,
) -> str:
    """Derive a meaningful title for the document.

    Priority:
    1. doc_content["title"]
    2. doc_content["project_name"]
    3. "{project_name}: {doc_type_display_name}"
    4. project_name alone
    5. doc_type_display_name alone
    6. Titlecased document_type

    Args:
        doc_content: Document content dict
        document_type: Document type string (e.g., "project_discovery")
        project_name: Project name from DB (optional)
        doc_type_display_name: Document type display name from DB (optional)

    Returns:
        Derived title string
    """
    title = doc_content.get("title") or doc_content.get("project_name")
    if title:
        return title

    if project_name and doc_type_display_name:
        return f"{project_name}: {doc_type_display_name}"
    elif project_name:
        return project_name
    elif doc_type_display_name:
        return doc_type_display_name
    else:
        return document_type.replace("_", " ").title()


def promote_pgc_invariants_to_document(
    doc_content: Dict[str, Any],
    context_invariants: List[Dict[str, Any]],
    known_constraints: Optional[List[Any]] = None,
    derive_domain_fn=None,
    build_statement_fn=None,
) -> List[Dict[str, Any]]:
    """Promote PGC invariants into document's pgc_invariants[] structure.

    Per ADR-042: At document completion, mechanically transform binding
    constraints from context_state into a structured pgc_invariants[]
    section in the output document.

    Args:
        doc_content: The document content dict (mutated in place)
        context_invariants: List of invariant dicts from context_state
        known_constraints: Optional known_constraints for cross-referencing
        derive_domain_fn: Optional callable(constraint_id) -> domain string
        build_statement_fn: Optional callable(constraint_id, question_text,
            answer_label, binding_source) -> statement string

    Returns:
        List of structured invariant dicts (also set on doc_content)
    """
    if not context_invariants:
        return []

    if known_constraints is None:
        known_constraints = doc_content.get("known_constraints", [])

    pgc_invariants = []
    for idx, inv in enumerate(context_invariants, start=1):
        constraint_id = inv.get("id", f"UNKNOWN-{idx}")
        answer_label = inv.get("user_answer_label") or str(inv.get("user_answer", ""))
        binding_source = inv.get("binding_source", "priority")

        invariant_id = f"INV-{constraint_id}"

        # Cross-reference with known_constraints
        source_constraint_id = None
        for i, kc in enumerate(known_constraints):
            kc_text = kc if isinstance(kc, str) else kc.get("text", "")
            if answer_label and answer_label.lower() in kc_text.lower():
                source_constraint_id = f"CNS-{i + 1}"
                break

        # Derive domain
        domain = (
            derive_domain_fn(constraint_id)
            if derive_domain_fn
            else _default_derive_domain(constraint_id)
        )

        # Build statement
        question_text = inv.get("text", "")
        statement = (
            build_statement_fn(constraint_id, question_text, answer_label, binding_source)
            if build_statement_fn
            else _default_build_statement(constraint_id, question_text, answer_label, binding_source)
        )

        pgc_invariants.append({
            "invariant_id": invariant_id,
            "source_constraint_id": source_constraint_id,
            "statement": statement,
            "domain": domain,
            "binding": True,
            "origin": "pgc",
            "change_policy": "explicit_renegotiation_only",
            "pgc_question_id": constraint_id,
            "user_answer": inv.get("user_answer"),
            "user_answer_label": answer_label,
        })

    doc_content["pgc_invariants"] = pgc_invariants
    return pgc_invariants


def embed_pgc_clarifications(
    doc_content: Dict[str, Any],
    clarifications: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Embed PGC clarifications (questions + answers) into document for traceability.

    Only resolved clarifications are included.

    Args:
        doc_content: Document content dict (mutated in place)
        clarifications: List of clarification dicts from context_state

    Returns:
        List of embedded clarification entries
    """
    if not clarifications:
        return []

    embedded = []
    for c in clarifications:
        if not c.get("resolved"):
            continue
        entry = {
            "question_id": c.get("id", ""),
            "question": c.get("text", ""),
            "why_it_matters": c.get("why_it_matters"),
            "answer": c.get("user_answer_label") or str(c.get("user_answer", "")),
            "binding": c.get("binding", False),
        }
        embedded.append(entry)

    if embedded:
        doc_content["pgc_clarifications"] = embedded

    return embedded


# ---------------------------------------------------------------------------
# Internal helpers (private to this module)
# ---------------------------------------------------------------------------


def _default_derive_domain(constraint_id: str) -> str:
    """Derive semantic domain from constraint ID."""
    domain_patterns = {
        "PLATFORM": "platform",
        "TARGET": "platform",
        "USER": "user",
        "PRIMARY": "user",
        "DEPLOYMENT": "deployment",
        "CONTEXT": "deployment",
        "SCOPE": "scope",
        "MATH": "scope",
        "FEATURE": "feature",
        "TRACKING": "feature",
        "STANDARD": "compliance",
        "EDUCATIONAL": "compliance",
        "SYSTEM": "integration",
        "EXISTING": "integration",
    }
    constraint_upper = constraint_id.upper()
    for pattern, domain in domain_patterns.items():
        if pattern in constraint_upper:
            return domain
    return "general"


def _default_build_statement(
    constraint_id: str,
    question_text: str,
    answer_label: str,
    binding_source: str,
) -> str:
    """Build human-readable invariant statement."""
    if binding_source == "exclusion":
        return f"{answer_label} is explicitly excluded"

    if "PLATFORM" in constraint_id.upper():
        return f"Application must be deployed as {answer_label}"
    elif "USER" in constraint_id.upper():
        return f"Primary users are {answer_label}"
    elif "DEPLOYMENT" in constraint_id.upper() or "CONTEXT" in constraint_id.upper():
        return f"Deployment context is {answer_label}"
    elif "SCOPE" in constraint_id.upper():
        return f"Scope includes {answer_label}"
    elif "TRACKING" in constraint_id.upper():
        return f"System will provide {answer_label}"
    elif "STANDARD" in constraint_id.upper():
        return f"Educational standards: {answer_label}"
    else:
        return f"{constraint_id}: {answer_label}"
