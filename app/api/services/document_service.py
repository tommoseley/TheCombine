"""
Document Service - CRUD and relationship management for documents.

This service handles:
- Creating documents with proper versioning
- Managing document relationships
- Staleness detection and propagation
- Cross-space standard references
"""

from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID
from datetime import datetime
import logging

from sqlalchemy import select, update, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.models.document import Document
from app.api.models.document_relation import DocumentRelation, RelationType

logger = logging.getLogger(__name__)


class DocumentService:
    """
    Service for document CRUD and relationship management.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # =========================================================================
    # CREATE
    # =========================================================================
    
    async def create_document(
        self,
        space_type: str,
        space_id: UUID,
        doc_type_id: str,
        title: str,
        content: Dict[str, Any],
        summary: Optional[str] = None,
        created_by: Optional[str] = None,
        created_by_type: str = "builder",
        builder_metadata: Optional[Dict[str, Any]] = None,
        derived_from: Optional[List[UUID]] = None,
    ) -> Document:
        """
        Create a new document.
        
        If a document of this type already exists in this space:
        - Mark the old one as not latest
        - Increment version number
        
        Args:
            space_type: 'project' | 'organization' | 'team'
            space_id: UUID of owning entity
            doc_type_id: Document type from registry
            title: Human-readable title
            content: Document content as dict
            summary: Optional summary
            created_by: Creator identifier
            created_by_type: 'user' | 'builder' | 'import'
            builder_metadata: Build metadata (model, tokens, etc.)
            derived_from: List of document IDs this was built from
            
        Returns:
            Created Document
        """
        # Check for existing latest document of this type
        existing = await self.get_latest(space_type, space_id, doc_type_id)
        
        version = 1
        if existing:
            # Mark existing as not latest
            existing.is_latest = False
            version = existing.version + 1
        
        # Create new document
        doc = Document(
            space_type=space_type,
            space_id=space_id,
            doc_type_id=doc_type_id,
            version=version,
            is_latest=True,
            title=title,
            summary=summary,
            content=content,
            status="draft",
            is_stale=False,
            created_by=created_by,
            created_by_type=created_by_type,
            builder_metadata=builder_metadata,
        )
        
        # Compute revision hash
        doc.update_revision_hash()
        
        self.db.add(doc)
        await self.db.flush()  # Get the ID
        
        # Create derived_from relationships
        if derived_from:
            for source_id in derived_from:
                relation = DocumentRelation(
                    from_document_id=doc.id,
                    to_document_id=source_id,
                    relation_type=RelationType.DERIVED_FROM,
                    created_by=created_by,
                )
                self.db.add(relation)
        
        await self.db.commit()
        await self.db.refresh(doc)
        
        logger.info(f"Created document: {doc.id} ({doc_type_id} v{version})")
        return doc
    
    # =========================================================================
    # READ
    # =========================================================================
    
    async def get_by_id(
        self, 
        document_id: UUID,
        include_relations: bool = False
    ) -> Optional[Document]:
        """Get document by ID."""
        query = select(Document).where(Document.id == document_id)
        
        if include_relations:
            query = query.options(
                selectinload(Document.outgoing_relations).selectinload(DocumentRelation.to_document),
                selectinload(Document.incoming_relations).selectinload(DocumentRelation.from_document),
            )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_latest(
        self,
        space_type: str,
        space_id: UUID,
        doc_type_id: str
    ) -> Optional[Document]:
        """Get the latest version of a document type in a space."""
        query = (
            select(Document)
            .where(Document.space_type == space_type)
            .where(Document.space_id == space_id)
            .where(Document.doc_type_id == doc_type_id)
            .where(Document.is_latest == True)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def list_by_space(
        self,
        space_type: str,
        space_id: UUID,
        status: Optional[str] = None,
        latest_only: bool = True
    ) -> List[Document]:
        """List documents in a space."""
        query = (
            select(Document)
            .where(Document.space_type == space_type)
            .where(Document.space_id == space_id)
        )
        
        if latest_only:
            query = query.where(Document.is_latest == True)
        
        if status:
            query = query.where(Document.status == status)
        
        query = query.order_by(Document.created_at.desc())
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_existing_doc_types(
        self,
        space_type: str,
        space_id: UUID
    ) -> List[str]:
        """Get list of doc_type_ids that exist in a space."""
        query = (
            select(Document.doc_type_id)
            .where(Document.space_type == space_type)
            .where(Document.space_id == space_id)
            .where(Document.is_latest == True)
            .where(Document.status.in_(["draft", "active"]))
            .distinct()
        )
        result = await self.db.execute(query)
        return [row[0] for row in result.all()]
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    
    async def add_relation(
        self,
        from_document_id: UUID,
        to_document_id: UUID,
        relation_type: str,
        pinned_version: Optional[int] = None,
        pinned_revision: Optional[str] = None,
        notes: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> DocumentRelation:
        """Add a relationship between documents."""
        relation = DocumentRelation(
            from_document_id=from_document_id,
            to_document_id=to_document_id,
            relation_type=relation_type,
            pinned_version=pinned_version,
            pinned_revision=pinned_revision,
            notes=notes,
            created_by=created_by,
        )
        self.db.add(relation)
        await self.db.commit()
        await self.db.refresh(relation)
        return relation
    
    async def get_relations(
        self,
        document_id: UUID,
        direction: str = "both",  # 'outgoing' | 'incoming' | 'both'
        relation_type: Optional[str] = None
    ) -> Dict[str, List[DocumentRelation]]:
        """Get relationships for a document."""
        result = {"outgoing": [], "incoming": []}
        
        if direction in ("outgoing", "both"):
            query = (
                select(DocumentRelation)
                .options(selectinload(DocumentRelation.to_document))
                .where(DocumentRelation.from_document_id == document_id)
            )
            if relation_type:
                query = query.where(DocumentRelation.relation_type == relation_type)
            
            res = await self.db.execute(query)
            result["outgoing"] = list(res.scalars().all())
        
        if direction in ("incoming", "both"):
            query = (
                select(DocumentRelation)
                .options(selectinload(DocumentRelation.from_document))
                .where(DocumentRelation.to_document_id == document_id)
            )
            if relation_type:
                query = query.where(DocumentRelation.relation_type == relation_type)
            
            res = await self.db.execute(query)
            result["incoming"] = list(res.scalars().all())
        
        return result
    
    # =========================================================================
    # STALENESS
    # =========================================================================
    
    async def mark_downstream_stale(self, document_id: UUID) -> int:
        """
        Mark all documents derived from this one as stale.
        
        Returns count of documents marked stale.
        """
        # Find all documents that have derived_from pointing to this doc
        subquery = (
            select(DocumentRelation.from_document_id)
            .where(DocumentRelation.to_document_id == document_id)
            .where(DocumentRelation.relation_type == RelationType.DERIVED_FROM)
        )
        
        # Mark them stale
        result = await self.db.execute(
            update(Document)
            .where(Document.id.in_(subquery))
            .where(Document.is_stale == False)  # Only mark if not already stale
            .values(is_stale=True, status="stale")
        )
        
        await self.db.commit()
        
        count = result.rowcount
        if count > 0:
            logger.info(f"Marked {count} downstream documents as stale")
        
        return count
    
    async def clear_stale(self, document_id: UUID) -> None:
        """Clear the stale flag on a document."""
        await self.db.execute(
            update(Document)
            .where(Document.id == document_id)
            .values(is_stale=False, status="active")
        )
        await self.db.commit()
    
    async def get_stale_documents(
        self,
        space_type: str,
        space_id: UUID
    ) -> List[Document]:
        """Get all stale documents in a space."""
        query = (
            select(Document)
            .where(Document.space_type == space_type)
            .where(Document.space_id == space_id)
            .where(Document.is_stale == True)
            .where(Document.is_latest == True)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    # =========================================================================
    # STANDARDS UPDATES
    # =========================================================================
    
    async def check_standard_updates(
        self,
        document_id: UUID
    ) -> List[Dict[str, Any]]:
        """
        Check if any org standards this document requires have newer versions.
        
        Returns list of available updates.
        """
        # Get requires relations to org documents with pinned versions
        query = (
            select(DocumentRelation, Document)
            .join(Document, DocumentRelation.to_document_id == Document.id)
            .where(DocumentRelation.from_document_id == document_id)
            .where(DocumentRelation.relation_type == RelationType.REQUIRES)
            .where(Document.space_type == "organization")
            .where(DocumentRelation.pinned_version.isnot(None))
        )
        
        result = await self.db.execute(query)
        
        updates = []
        for relation, doc in result.all():
            # Get latest version of this doc type in org space
            latest_query = (
                select(Document.version)
                .where(Document.space_type == "organization")
                .where(Document.space_id == doc.space_id)
                .where(Document.doc_type_id == doc.doc_type_id)
                .where(Document.is_latest == True)
            )
            latest_result = await self.db.execute(latest_query)
            latest_version = latest_result.scalar()
            
            if latest_version and latest_version > relation.pinned_version:
                updates.append({
                    "standard_id": str(doc.id),
                    "standard_title": doc.title,
                    "doc_type_id": doc.doc_type_id,
                    "pinned_version": relation.pinned_version,
                    "latest_version": latest_version,
                })
        
        return updates
    
    # =========================================================================
    # UPDATE
    # =========================================================================
    
    async def update_status(
        self,
        document_id: UUID,
        status: str
    ) -> Optional[Document]:
        """Update document status."""
        doc = await self.get_by_id(document_id)
        if not doc:
            return None
        
        doc.status = status
        if status == "active":
            doc.is_stale = False
        
        await self.db.commit()
        await self.db.refresh(doc)
        return doc
    
    # =========================================================================
    # DELETE
    # =========================================================================
    
    async def archive(self, document_id: UUID) -> Optional[Document]:
        """Archive a document (soft delete)."""
        return await self.update_status(document_id, "archived")