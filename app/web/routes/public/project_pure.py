"""
Pure data transformation functions extracted from project_routes.py.

No I/O, no DB, no logging. All functions are deterministic and testable in isolation.

WS-CRAP-006: Testability refactoring for CRAP score reduction.
"""

from typing import Optional


# =============================================================================
# Document Status Derivation
# =============================================================================

def derive_status_summary(document_statuses: list) -> dict:
    """Derive aggregate status summary from a list of document status objects.

    Counts documents by readiness state: ready, stale, blocked, waiting.

    Args:
        document_statuses: List of objects/dicts with a 'readiness' attribute or key.

    Returns:
        Dict with keys: ready, stale, blocked, waiting, needs_acceptance (all int).
    """
    summary = {"ready": 0, "stale": 0, "blocked": 0, "waiting": 0, "needs_acceptance": 0}

    for doc in document_statuses:
        readiness = _get_readiness(doc)
        if readiness and readiness in summary:
            summary[readiness] += 1

    return summary


def normalize_document_status(doc) -> dict:
    """Normalize a document status object into a consistent dict.

    If the object has a 'readiness' attribute, extracts structured fields.
    Otherwise returns the object as-is (assumed to already be a dict).

    Args:
        doc: A document status object (with attributes) or dict.

    Returns:
        Dict with keys: doc_type_id, title, icon, readiness, acceptance_state, subtitle.
    """
    readiness = _get_readiness(doc)
    if readiness is None:
        # Already a dict or object without readiness
        return doc if isinstance(doc, dict) else {}

    return {
        "doc_type_id": _get_attr(doc, "doc_type_id"),
        "title": _get_attr(doc, "title"),
        "icon": _get_attr(doc, "icon"),
        "readiness": readiness,
        "acceptance_state": _get_attr(doc, "acceptance_state"),
        "subtitle": _get_attr(doc, "subtitle"),
    }


def derive_documents_and_summary(document_statuses: list) -> tuple[list[dict], dict]:
    """Derive both normalized documents list and status summary.

    Combines normalize_document_status and derive_status_summary in a single pass.

    Args:
        document_statuses: List of document status objects.

    Returns:
        Tuple of (documents_list, status_summary_dict).
    """
    documents = []
    summary = {"ready": 0, "stale": 0, "blocked": 0, "waiting": 0, "needs_acceptance": 0}

    for doc in document_statuses:
        readiness = _get_readiness(doc)
        if readiness is not None:
            if readiness in summary:
                summary[readiness] += 1
            documents.append({
                "doc_type_id": _get_attr(doc, "doc_type_id"),
                "title": _get_attr(doc, "title"),
                "icon": _get_attr(doc, "icon"),
                "readiness": readiness,
                "acceptance_state": _get_attr(doc, "acceptance_state"),
                "subtitle": _get_attr(doc, "subtitle"),
            })
        else:
            documents.append(doc if isinstance(doc, dict) else {})

    return documents, summary


# =============================================================================
# Deletion Validation
# =============================================================================

def validate_soft_delete(
    project_archived_at,
    project_deleted_at,
    confirmation: str,
    project_id_upper: str,
) -> Optional[str]:
    """Validate preconditions for soft-deleting a project.

    Returns None if validation passes, or an error message string if it fails.

    Args:
        project_archived_at: Timestamp or None. Must be non-None (archived).
        project_deleted_at: Timestamp or None. Must be None (not already deleted).
        confirmation: User-entered confirmation string.
        project_id_upper: The project_id in uppercase for comparison.

    Returns:
        None on success, or error message string on validation failure.
    """
    if project_archived_at is None:
        return "Project must be archived before deletion"

    if project_deleted_at is not None:
        return "already_deleted"

    if confirmation.strip().upper() != project_id_upper.upper():
        return f"confirmation_mismatch:{project_id_upper}"

    return None


# =============================================================================
# Internal helpers
# =============================================================================

def _get_readiness(doc) -> Optional[str]:
    """Get readiness from an object (attribute or dict key)."""
    if hasattr(doc, "readiness"):
        return doc.readiness
    if isinstance(doc, dict):
        return doc.get("readiness")
    return None


def _get_attr(doc, name: str, default=None):
    """Get attribute from object or dict."""
    if hasattr(doc, name):
        return getattr(doc, name, default)
    if isinstance(doc, dict):
        return doc.get(name, default)
    return default
