"""
Staleness Service for ADR-036 / WS-DOCUMENT-SYSTEM-CLEANUP Phase 4.

Propagates staleness to downstream documents when upstream documents change.
Staleness is informational, not destructive - documents remain viewable.
"""

import logging
from typing import Dict, List
from uuid import UUID

from sqlalchemy import update, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models.document import Document

logger = logging.getLogger(__name__)


# =============================================================================
# DEPENDENCY GRAPH (Per WS-DOCUMENT-SYSTEM-CLEANUP)
# =============================================================================
# This graph defines which document types depend on which.
# When an upstream document changes, direct dependents are marked stale.
# Staleness does NOT cascade (only direct dependents).

DOCUMENT_TYPE_DEPENDENCIES: Dict[str, List[str]] = {
    # doc_type_id -> list of doc_type_ids that depend on it
    "project_discovery": ["technical_architecture"],
    # technical_architecture has no downstream dependents
}


def get_downstream_types(doc_type_id: str) -> List[str]:
    """
    Get document types that directly depend on the given type.
    
    Per ADR-036: Only direct dependents, no cascading.
    """
    return DOCUMENT_TYPE_DEPENDENCIES.get(doc_type_id, [])


class StalenessService:
    """
    Service for propagating staleness to downstream documents.
    
    Per ADR-036:
    - Staleness is informational, not destructive
    - Documents remain fully renderable when stale
    - No auto-regeneration triggered
    - Only direct dependents are marked (no cascade)
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def propagate_staleness(
        self,
        source_document: Document,
    ) -> int:
        """
        Mark downstream documents as stale when source document changes.
        
        Args:
            source_document: The document that was just saved/updated
            
        Returns:
            Count of documents marked stale
        """
        # Get downstream document types
        downstream_types = get_downstream_types(source_document.doc_type_id)
        
        if not downstream_types:
            logger.debug(
                f"No downstream types for {source_document.doc_type_id}, "
                "skipping staleness propagation"
            )
            return 0
        
        # Find downstream documents in the same space that are not already stale
        # Per ADR-036: Only mark documents that are 'partial' or 'complete'
        result = await self.db.execute(
            update(Document)
            .where(
                and_(
                    Document.space_type == source_document.space_type,
                    Document.space_id == source_document.space_id,
                    Document.doc_type_id.in_(downstream_types),
                    Document.is_latest == True,
                    Document.lifecycle_state.in_(['partial', 'complete']),
                )
            )
            .values(
                lifecycle_state='stale',
                is_stale=True,  # Keep legacy field in sync
            )
        )
        
        count = result.rowcount
        
        if count > 0:
            logger.info(
                f"Marked {count} downstream documents as stale "
                f"(source: {source_document.doc_type_id} in space {source_document.space_id})"
            )
        
        return count
    
    async def get_stale_documents(
        self,
        space_type: str,
        space_id: UUID,
    ) -> List[Document]:
        """
        Get all stale documents in a space.
        
        Args:
            space_type: Space type (project, org, team)
            space_id: Space UUID
            
        Returns:
            List of stale documents
        """
        query = (
            select(Document)
            .where(Document.space_type == space_type)
            .where(Document.space_id == space_id)
            .where(Document.lifecycle_state == 'stale')
            .where(Document.is_latest == True)
        )
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_upstream_dependencies(
        self,
        doc_type_id: str,
    ) -> List[str]:
        """
        Get document types that this type depends on.
        
        Inverse of DOCUMENT_TYPE_DEPENDENCIES.
        """
        upstream = []
        for source, dependents in DOCUMENT_TYPE_DEPENDENCIES.items():
            if doc_type_id in dependents:
                upstream.append(source)
        return upstream