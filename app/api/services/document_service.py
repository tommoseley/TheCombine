"""
Document Service - CRUD and relationship management for documents.

This service handles:
- Creating documents with proper versioning
- Managing document relationships
- Staleness detection and propagation
- Cross-space standard references
"""

from typing import Dict, Any, List, Optional
from uuid import UUID
import logging

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.models.document import Document
from app.api.models.document_relation import DocumentRelation, RelationType
from app.domain.workflow.scope import ScopeHierarchy

# =============================================================================
# OWNERSHIP EXCEPTIONS (ADR-011-Part-2)
# =============================================================================

class OwnershipError(Exception):
    """Base class for ownership validation errors."""
    pass


class CycleDetectedError(OwnershipError):
    """Raised when setting parent would create a cycle."""
    pass


class InvalidOwnershipError(OwnershipError):
    """Raised when parent doc_type cannot own child doc_type."""
    pass


class IncomparableScopesError(OwnershipError):
    """Raised when parent and child scopes are not on same ancestry chain."""
    pass


class ScopeViolationError(OwnershipError):
    """Raised when child scope depth < parent scope depth."""
    pass


class HasChildrenError(OwnershipError):
    """Raised when attempting to delete a document with children."""
    pass


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
        schema_bundle_sha256: Optional[str] = None,
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
            schema_bundle_sha256: Schema bundle hash at generation time
            
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
            schema_bundle_sha256=schema_bundle_sha256,
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
    # =========================================================================
    # OWNERSHIP VALIDATION (ADR-011-Part-2)
    # =========================================================================
    
    async def validate_parent_assignment(
        self,
        child_id: UUID,
        proposed_parent_id: UUID,
        workflow: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Validate that setting child.parent_document_id = proposed_parent_id is allowed.
        
        Checks (in order):
        1. Cycle detection (always enforced)
        2. Ownership validity (if workflow provided)
        3. Scope monotonicity (if workflow provided)
        """
        child = await self.get_by_id(child_id)
        parent = await self.get_by_id(proposed_parent_id)
        
        if not child or not parent:
            raise OwnershipError("Document not found")
        
        await self._check_no_cycle(child, parent)
        
        if workflow:
            self._check_ownership_validity(child, parent, workflow)
            self._check_scope_monotonicity(child, parent, workflow)
    
    async def _check_no_cycle(
        self,
        child: Document,
        proposed_parent: Document
    ) -> None:
        """Walk parent chain from proposed_parent. If child.id appears, reject."""
        if child.id == proposed_parent.id:
            raise CycleDetectedError(f"Document cannot own itself: {child.id}")
        
        visited = {child.id}
        current_id = proposed_parent.parent_document_id
        
        while current_id is not None:
            if current_id in visited:
                raise CycleDetectedError(
                    f"Setting parent would create cycle: {child.id} -> {proposed_parent.id}"
                )
            visited.add(current_id)
            
            query = select(Document.parent_document_id).where(Document.id == current_id)
            result = await self.db.execute(query)
            row = result.first()
            current_id = row[0] if row else None
    
    def _check_ownership_validity(
        self,
        child: Document,
        parent: Document,
        workflow: Dict[str, Any],
    ) -> None:
        """Check if parent's doc_type may_own child's doc_type per workflow."""
        doc_types = workflow.get("document_types", {})
        entity_types = workflow.get("entity_types", {})
        
        parent_config = doc_types.get(parent.doc_type_id, {})
        may_own = parent_config.get("may_own", [])
        
        if not may_own:
            return
        
        child_config = doc_types.get(child.doc_type_id, {})
        child_scope = child_config.get("scope")
        
        for entity_type_name in may_own:
            entity_config = entity_types.get(entity_type_name, {})
            if entity_config.get("creates_scope") == child_scope:
                return
        
        raise InvalidOwnershipError(
            f"Document type '{parent.doc_type_id}' cannot own '{child.doc_type_id}' "
            f"per workflow rules (may_own: {may_own})"
        )
    
    def _check_scope_monotonicity(
        self,
        child: Document,
        parent: Document,
        workflow: Dict[str, Any],
    ) -> None:
        """Check scope depth: child depth >= parent depth."""
        hierarchy = ScopeHierarchy.from_workflow(workflow)
        doc_types = workflow.get("document_types", {})
        
        parent_scope = doc_types.get(parent.doc_type_id, {}).get("scope")
        child_scope = doc_types.get(child.doc_type_id, {}).get("scope")
        
        if not parent_scope or not child_scope:
            return
        
        same_scope = parent_scope == child_scope
        parent_is_ancestor = hierarchy.is_ancestor(parent_scope, child_scope)
        child_is_ancestor = hierarchy.is_ancestor(child_scope, parent_scope)
        
        if not (same_scope or parent_is_ancestor or child_is_ancestor):
            raise IncomparableScopesError(
                f"Scopes '{parent_scope}' and '{child_scope}' are not comparable"
            )
        
        parent_depth = hierarchy.get_depth(parent_scope)
        child_depth = hierarchy.get_depth(child_scope)
        
        if child_depth < parent_depth:
            raise ScopeViolationError(
                f"Child scope '{child_scope}' (depth={child_depth}) is broader than "
                f"parent scope '{parent_scope}' (depth={parent_depth})"
            )
    
    async def validate_deletion(self, document_id: UUID) -> None:
        """Check if document can be deleted (has no children)."""
        query = select(Document.id).where(
            Document.parent_document_id == document_id
        ).limit(1)
        result = await self.db.execute(query)
        
        if result.first():
            raise HasChildrenError(f"Cannot delete document {document_id}: has children")
    
    async def get_children(self, document_id: UUID) -> List[Document]:
        """Get all direct children of a document."""
        query = (
            select(Document)
            .where(Document.parent_document_id == document_id)
            .order_by(Document.created_at)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_subtree(self, document_id: UUID) -> List[Document]:
        """Get entire subtree rooted at document."""
        subtree = []
        children = await self.get_children(document_id)
        for child in children:
            subtree.append(child)
            subtree.extend(await self.get_subtree(child.id))
        return subtree
    
    async def delete(self, document_id: UUID) -> bool:
        """Delete a document. Raises HasChildrenError if has children."""
        await self.validate_deletion(document_id)
        
        doc = await self.get_by_id(document_id)
        if not doc:
            return False
        
        await self.db.delete(doc)
        await self.db.commit()
        return True