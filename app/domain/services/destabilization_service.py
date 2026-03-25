"""
Automatic Destabilization Service (ADR-063, WS-REWIND-005).

When upstream rewind occurs, revokes stabilization status of dependent
WPs and WSs. Fires atomically as part of the rewind operation.
"""

import logging
from typing import List
from uuid import UUID

from app.persistence.models import DocumentStatus, StoredDocument
from app.persistence.repositories import DocumentRepository

logger = logging.getLogger(__name__)


async def destabilize_downstream(
    document_repo: DocumentRepository,
    project_id: UUID,
    stale_document_ids: List[UUID],
) -> List[UUID]:
    """
    Destabilize all child documents of stale WPs.

    When a WP is marked stale, all its child WSs must also become stale.
    Acceptance state (accepted_at/accepted_by) is conceptually revoked
    by the stale status — stale documents cannot be promoted regardless
    of prior acceptance.

    Args:
        document_repo: Document repository.
        project_id: Project being rewound.
        stale_document_ids: IDs of documents already marked stale by rewind.

    Returns:
        List of additionally destabilized document IDs.
    """
    # Get all documents in the project
    all_docs = await document_repo.list_by_scope(
        scope_type="project",
        scope_id=str(project_id),
    )

    stale_set = set(stale_document_ids)
    additionally_staled: List[UUID] = []

    for doc in all_docs:
        # Skip documents that are already stale or in the stale set
        if doc.document_id in stale_set:
            continue
        if doc.status in (DocumentStatus.STALE, DocumentStatus.ARCHIVED):
            continue

        # If this doc is a WS whose doc_type is work_statement,
        # check if its content references a parent WP that is stale
        if doc.document_type == "work_statement":
            parent_wp_id = doc.content.get("parent_wp_id") if doc.content else None
            if parent_wp_id:
                # Check if any stale doc has matching WP id in content
                for stale_id in stale_document_ids:
                    stale_doc = await document_repo.get(stale_id)
                    if stale_doc and stale_doc.document_type == "work_package":
                        wp_id = (
                            stale_doc.content.get("wp_id")
                            if stale_doc.content
                            else None
                        )
                        if wp_id and wp_id == parent_wp_id:
                            doc.status = DocumentStatus.STALE
                            doc.is_latest = False
                            await document_repo.save(doc)
                            additionally_staled.append(doc.document_id)
                            logger.info(
                                "Destabilized child WS %s (parent WP %s stale)",
                                doc.document_id,
                                wp_id,
                            )
                            break

    if additionally_staled:
        logger.info(
            "Destabilized %d additional child documents", len(additionally_staled)
        )

    return additionally_staled
