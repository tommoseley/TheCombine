"""Constraint propagation and PGC invariant integration.

Extracted from PlanExecutor (WS-CRAP decomposition).
Handles invariant pinning, exclusion filtering, and PGC integration
into document structures.
"""

import logging
from typing import Any, Callable, Dict

from app.domain.workflow.document_workflow_state import DocumentWorkflowState

logger = logging.getLogger(__name__)


async def pin_invariants_via_operation(
    document: Dict[str, Any],
    state: DocumentWorkflowState,
    ops_service,
    operation_executor=None,
) -> Dict[str, Any]:
    """Pin binding invariants via mechanical operation.

    ADR-047: Dispatches to discovery_invariant_pinner operation.
    Falls back to inline method if operation not available.

    Args:
        document: The produced document
        state: Workflow state containing pgc_invariants
        ops_service: OperationProvider instance
        operation_executor: OperationExecutor instance

    Returns:
        Document with pinned constraints
    """
    invariants = state.context_state.get("pgc_invariants", [])
    if not invariants:
        return document

    op = ops_service.get_operation("discovery_invariant_pinner") if ops_service else None
    if op and operation_executor:
        result = await operation_executor.execute(
            operation=op,
            inputs={"document": document, "invariants": invariants},
        )
        if result.success and result.output:
            return result.output
        else:
            logger.warning(f"Invariant pinning operation failed: {result.error}, using fallback")

    # Fallback to existing method
    return pin_invariants_to_known_constraints(document, state)


async def filter_excluded_via_operation(
    document: Dict[str, Any],
    state: DocumentWorkflowState,
    ops_service,
    operation_executor=None,
) -> Dict[str, Any]:
    """Filter excluded topics via mechanical operation.

    ADR-047: Dispatches to discovery_exclusion_filter operation.
    Falls back to inline method if operation not available.

    Args:
        document: The document to filter
        state: Workflow state containing pgc_invariants
        ops_service: OperationProvider instance
        operation_executor: OperationExecutor instance

    Returns:
        Document with excluded topics filtered
    """
    invariants = state.context_state.get("pgc_invariants", [])
    if not invariants:
        return document

    op = ops_service.get_operation("discovery_exclusion_filter") if ops_service else None
    if op and operation_executor:
        result = await operation_executor.execute(
            operation=op,
            inputs={"document": document, "invariants": invariants},
        )
        if result.success and result.output:
            return result.output
        else:
            logger.warning(f"Exclusion filter operation failed: {result.error}, using fallback")

    # Fallback to existing method
    return filter_excluded_topics(document, state)


def pin_invariants_to_known_constraints(
    document: Dict[str, Any],
    state: DocumentWorkflowState,
) -> Dict[str, Any]:
    """Pin binding invariants into document's known_constraints[].

    .. deprecated::
        Use `pin_invariants_via_operation` instead, which dispatches to
        the `discovery_invariant_pinner` mechanical operation (ADR-047).
        This method is kept as a fallback and will be removed in a future release.

    Delegates to pure function pin_invariants_to_constraints() for testability.
    """
    from app.domain.workflow.constraint_matching import (
        pin_invariants_to_constraints,
    )

    invariants = state.context_state.get("pgc_invariants", [])
    result = pin_invariants_to_constraints(document, invariants)

    # Log summary (I/O concern stays in the thin wrapper)
    pinned_count = len(invariants)
    orig_count = len(document.get("known_constraints", []))
    final_count = len(result.get("known_constraints", []))
    removed = pinned_count + orig_count - final_count
    logger.info(
        f"ADR-042: Pinned {pinned_count} binding invariants, "
        f"removed {max(0, removed)} duplicates "
        f"(total: {final_count})"
    )

    return result


def filter_excluded_topics(
    document: Dict[str, Any],
    state: DocumentWorkflowState,
    exclusion_filter=None,
) -> Dict[str, Any]:
    """Filter recommendations and decision points mentioning excluded topics.

    .. deprecated::
        Use `filter_excluded_via_operation` instead, which dispatches to
        the `discovery_exclusion_filter` mechanical operation (ADR-047).
        This method is kept as a fallback and will be removed in a future release.

    Delegates to ExclusionFilter protocol (WS-CLEANUP-003).

    Args:
        document: The produced document (will be copied, not mutated)
        state: Workflow state containing pgc_invariants
        exclusion_filter: ExclusionFilter protocol implementation

    Returns:
        Document with excluded topics filtered out
    """
    invariants = state.context_state.get("pgc_invariants", [])
    if exclusion_filter:
        filtered, removed_count = exclusion_filter.apply(document, invariants)
    else:
        # Fallback — use default from factory registry
        from app.domain.workflow.operations import get_default_filter
        default_filter = get_default_filter()
        if default_filter:
            filtered, removed_count = default_filter.apply(document, invariants)
        else:
            filtered, removed_count = document, 0

    if removed_count > 0:
        logger.info(f"ADR-042: Filtered {removed_count} items mentioning excluded topics")

    return filtered


def promote_pgc_invariants_to_document(
    doc_content: Dict[str, Any],
    state: DocumentWorkflowState,
    derive_domain_fn: Callable[[str], str],
    build_statement_fn: Callable[[str, str, str, str], str],
) -> None:
    """Promote PGC invariants into document structure.

    Per ADR-042: At document completion, mechanically transform binding
    constraints from context_state into a structured pgc_invariants[]
    section in the output document.

    Args:
        doc_content: The document content dict (mutated in place)
        state: The workflow state containing pgc_invariants
        derive_domain_fn: Function to derive constraint domain from ID
        build_statement_fn: Function to build invariant statement text
    """
    context_invariants = state.context_state.get("pgc_invariants", [])
    if not context_invariants:
        return

    # Get existing known_constraints for cross-referencing
    known_constraints = doc_content.get("known_constraints", [])

    # Build structured invariants
    pgc_invariants = []
    for idx, inv in enumerate(context_invariants, start=1):
        constraint_id = inv.get("id", f"UNKNOWN-{idx}")
        answer_label = inv.get("user_answer_label") or str(inv.get("user_answer", ""))
        binding_source = inv.get("binding_source", "priority")

        # Generate invariant ID
        invariant_id = f"INV-{constraint_id}"

        # Find matching constraint ID in known_constraints (if present)
        source_constraint_id = None
        for i, kc in enumerate(known_constraints):
            kc_text = kc if isinstance(kc, str) else kc.get("text", "")
            if answer_label.lower() in kc_text.lower():
                source_constraint_id = f"CNS-{i + 1}"
                break

        # Derive domain from constraint ID (heuristic)
        domain = derive_domain_fn(constraint_id)

        # Build statement from question context
        question_text = inv.get("text", "")
        statement = build_statement_fn(
            constraint_id, question_text, answer_label, binding_source
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
    logger.info(
        f"ADR-042: Promoted {len(pgc_invariants)} PGC invariants to document structure"
    )


def embed_pgc_clarifications(
    doc_content: Dict[str, Any],
    state: DocumentWorkflowState,
) -> None:
    """Embed PGC clarifications (questions + answers) into document.

    If the workflow included a PGC gate, the full set of clarification
    questions and operator answers are embedded in the final document
    for traceability. Only resolved clarifications are included.

    Args:
        doc_content: The document content dict (mutated in place)
        state: The workflow state containing pgc_clarifications
    """
    clarifications = state.context_state.get("pgc_clarifications", [])
    if not clarifications:
        return

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
        logger.info(
            f"Embedded {len(embedded)} PGC clarifications in document"
        )


def derive_constraint_domain(constraint_id: str) -> str:
    """Derive semantic domain from constraint ID.

    Args:
        constraint_id: The PGC question ID (e.g., TARGET_PLATFORM)

    Returns:
        Domain string (e.g., "platform", "user", "scope")
    """
    # Map common patterns to domains
    domain_patterns = {
        "PLATFORM": "platform",
        "TARGET": "platform",
        "USER": "user",
        "PRIMARY": "user",
        "DEPLOYMENT": "deployment",
        "CONTEXT": "deployment",
        "SCOPE": "scope",
        "MATH": "scope",
        "CAPABILITY": "capability",
        "TRACKING": "capability",
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


def build_invariant_statement(
    constraint_id: str,
    question_text: str,
    answer_label: str,
    binding_source: str,
) -> str:
    """Build human-readable invariant statement.

    Args:
        constraint_id: The PGC question ID
        question_text: The original question text
        answer_label: The user's answer label
        binding_source: How binding was derived (priority, exclusion, etc.)

    Returns:
        Statement string describing the invariant
    """
    # Handle exclusions specially
    if binding_source == "exclusion":
        return f"{answer_label} is explicitly excluded"

    # Build statement based on constraint type
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
        # Generic statement
        return f"{constraint_id}: {answer_label}"
