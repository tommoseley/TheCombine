"""Document readiness gate for downstream consumption.

WS-WB-020: Defines a deterministic predicate for whether a document
is ready to be consumed by downstream stations (e.g., TA -> Work Binder).

A document is ready for downstream consumption when:
  1. It exists (not None)
  2. Its lifecycle_state is "complete" (generation finished)
  3. Its status is not "stale" or "archived"

The pipeline creates documents with status="draft" and transitions
lifecycle_state to "complete" after QA. The status field is not
currently managed by the pipeline, so "draft" + "complete" is the
normal production path.

Uses duck typing -- works with any object that has `lifecycle_state`
and `status` attributes (Document ORM model, dataclass stubs, dicts
with __getattr__, etc.).
"""

from typing import Any, Optional

_EXCLUDED_STATUSES = frozenset({"stale", "archived"})


def is_doc_ready_for_downstream(doc: Optional[Any]) -> bool:
    """Check whether a document is ready for downstream consumption.

    Args:
        doc: Any document-like object with ``status`` and
             ``lifecycle_state`` attributes, or None.

    Returns:
        True when the document exists, lifecycle_state is ``"complete"``,
        and status is not ``"stale"`` or ``"archived"``.
        Returns False for None, missing attributes, or any other
        combination.
    """
    if doc is None:
        return False

    try:
        lifecycle_state = doc.lifecycle_state
        doc_status = doc.status
    except AttributeError:
        return False

    return lifecycle_state == "complete" and doc_status not in _EXCLUDED_STATUSES
