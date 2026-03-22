"""
Downstream Progression Guard (ADR-063, WS-REWIND-012).

Only current artifacts may be used for downstream processing.
Prevents stale or superseded artifacts from feeding into generation,
promotion, or stabilization.
"""

import logging
from dataclasses import dataclass
from typing import List
from uuid import UUID

from app.domain.models.rewind_errors import RewindBlockedError, stale_input_error
from app.persistence.models import DocumentStatus, StoredDocument
from app.persistence.repositories import DocumentRepository

logger = logging.getLogger(__name__)


@dataclass
class GuardResult:
    """Result of a progression guard check."""

    passed: bool
    errors: List[RewindBlockedError]


def check_documents_current(documents: List[StoredDocument]) -> GuardResult:
    """
    Check that all provided documents are in current (non-stale) status.

    Pure function — no DB access. Caller provides the documents.

    Args:
        documents: Documents to check.

    Returns:
        GuardResult with passed=True if all current, or errors listing
        which documents are stale/superseded.
    """
    errors: List[RewindBlockedError] = []
    for doc in documents:
        if doc.status in (DocumentStatus.STALE, DocumentStatus.ARCHIVED):
            errors.append(
                stale_input_error(
                    document_id=doc.document_id,
                    document_type=doc.document_type,
                    consuming_operation="proceed with downstream processing",
                )
            )
    return GuardResult(passed=len(errors) == 0, errors=errors)


def check_document_promotable(doc: StoredDocument) -> GuardResult:
    """
    Check that a document can be promoted/stabilized.

    Args:
        doc: Document to check.

    Returns:
        GuardResult with passed=True if document is current and eligible.
    """
    if doc.status in (DocumentStatus.STALE, DocumentStatus.ARCHIVED):
        return GuardResult(
            passed=False,
            errors=[
                stale_input_error(
                    document_id=doc.document_id,
                    document_type=doc.document_type,
                    consuming_operation="promote or stabilize",
                )
            ],
        )
    return GuardResult(passed=True, errors=[])
