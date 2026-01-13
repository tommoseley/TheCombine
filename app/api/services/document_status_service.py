"""
Document Status Service - ADR-007 Implementation

Derives document readiness and acceptance states for sidebar display.
All status is computed, never stored - prevents drift.

Key principle: The system never tells the user what to think.
It only tells them what's safe, what's risky, and what's missing.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from uuid import UUID
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models.document import Document
from app.api.models.document_type import DocumentType

logger = logging.getLogger(__name__)


# =============================================================================
# STATUS CONSTANTS
# =============================================================================

class ReadinessStatus:
    """Readiness status values - document buildability/usability."""
    READY = "ready"       # Exists, valid, safe to use
    STALE = "stale"       # Exists, but upstream inputs changed
    BLOCKED = "blocked"   # Cannot be built (missing requirements)
    WAITING = "waiting"   # Buildable but not yet built
    
    ALL = [READY, STALE, BLOCKED, WAITING]


class AcceptanceState:
    """Acceptance state values - human sign-off status."""
    ACCEPTED = "accepted"               # Explicitly approved
    NEEDS_ACCEPTANCE = "needs_acceptance"  # Required but not yet given
    REJECTED = "rejected"               # Reviewed, changes requested
    
    ALL = [ACCEPTED, NEEDS_ACCEPTANCE, REJECTED]


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class DocumentStatus:
    """
    Complete status for a document in the sidebar.
    
    This is the primary output of DocumentStatusService - contains
    everything needed to render a document row in the sidebar.
    """
    # Identity
    doc_type_id: str
    document_id: Optional[UUID]
    title: str
    icon: str
    
    # Derived states
    readiness: str                      # ready | stale | blocked | waiting
    acceptance_state: Optional[str]     # accepted | needs_acceptance | rejected | None
    
    # Context for UI
    subtitle: Optional[str]             # "Needs acceptance (PM)", "Missing: X"
    
    # Action enablement
    can_build: bool
    can_rebuild: bool
    can_accept: bool
    can_reject: bool
    can_use_as_input: bool
    
    # Blocked details
    missing_inputs: List[str] = field(default_factory=list)
    
    # Display ordering
    display_order: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "doc_type_id": self.doc_type_id,
            "document_id": str(self.document_id) if self.document_id else None,
            "title": self.title,
            "icon": self.icon,
            "readiness": self.readiness,
            "acceptance_state": self.acceptance_state,
            "subtitle": self.subtitle,
            "can_build": self.can_build,
            "can_rebuild": self.can_rebuild,
            "can_accept": self.can_accept,
            "can_reject": self.can_reject,
            "can_use_as_input": self.can_use_as_input,
            "missing_inputs": self.missing_inputs,
            "display_order": self.display_order,
        }


# =============================================================================
# SERVICE
# =============================================================================

class DocumentStatusService:
    """
    Service for deriving document status for sidebar display.
    
    All status is derived from current state - never stored.
    This ensures status always reflects reality.
    """
    
    async def get_project_document_statuses(
        self,
        db: AsyncSession,
        project_id: UUID
    ) -> List[DocumentStatus]:
        """
        Get status for all document types in a project.
        
        Returns ordered list for sidebar display, including:
        - Document types that have documents
        - Document types that could be built (waiting)
        - Document types that are blocked
        
        Args:
            db: Database session
            project_id: Project UUID
            
        Returns:
            List of DocumentStatus ordered by display_order
        """
        # Get all active document types for project scope
        doc_types = await self._get_project_document_types(db)
        
        # Get all existing documents for this project
        existing_docs = await self._get_project_documents(db, project_id)
        docs_by_type = {doc.doc_type_id: doc for doc in existing_docs}
        
        # Build status for each document type
        statuses = []
        existing_type_ids = set(docs_by_type.keys())
        logger.info(f"[STATUS] Project {project_id}: existing_type_ids = {existing_type_ids}")
        
        for doc_type in doc_types:
            document = docs_by_type.get(doc_type.doc_type_id)
            
            status = self._build_document_status(
                doc_type=doc_type,
                document=document,
                existing_type_ids=existing_type_ids
            )
            statuses.append(status)
        
        # Sort by display_order
        statuses.sort(key=lambda s: s.display_order)
        
        return statuses
    
    async def get_document_status(
        self,
        db: AsyncSession,
        doc_type_id: str,
        space_type: str,
        space_id: UUID
    ) -> Optional[DocumentStatus]:
        """
        Get status for a single document type in a space.
        
        Args:
            db: Database session
            doc_type_id: Document type identifier
            space_type: Space type ('project', 'organization', 'team')
            space_id: Space UUID
            
        Returns:
            DocumentStatus or None if doc_type not found
        """
        # Get document type
        doc_type = await self._get_document_type(db, doc_type_id)
        if not doc_type:
            return None
        
        # Get document if exists
        document = await self._get_document(db, doc_type_id, space_type, space_id)
        
        # Get existing doc types in this space for dependency checking
        existing_type_ids = await self._get_existing_doc_type_ids(db, space_type, space_id)
        
        return self._build_document_status(
            doc_type=doc_type,
            document=document,
            existing_type_ids=existing_type_ids
        )
    
    # =========================================================================
    # DERIVATION LOGIC (sync - no DB access)
    # =========================================================================
    
    def _build_document_status(
        self,
        doc_type: DocumentType,
        document: Optional[Document],
        existing_type_ids: set
    ) -> DocumentStatus:
        """
        Build complete DocumentStatus from document type and document.
        
        This is the core derivation logic from ADR-007.
        """
        # Derive readiness
        readiness, missing_inputs = self._derive_readiness(
            doc_type=doc_type,
            document=document,
            existing_type_ids=existing_type_ids
        )
        
        # Derive acceptance state
        acceptance_state = self._derive_acceptance_state(
            doc_type=doc_type,
            document=document
        )
        
        # Derive subtitle
        subtitle = self._derive_subtitle(
            doc_type=doc_type,
            document=document,
            readiness=readiness,
            acceptance_state=acceptance_state,
            missing_inputs=missing_inputs
        )
        
        # Derive action enablement
        can_build = readiness in (ReadinessStatus.WAITING, ReadinessStatus.STALE)
        can_rebuild = readiness == ReadinessStatus.STALE
        can_accept = acceptance_state == AcceptanceState.NEEDS_ACCEPTANCE
        can_reject = acceptance_state in (AcceptanceState.NEEDS_ACCEPTANCE, AcceptanceState.ACCEPTED)
        can_use_as_input = self._derive_can_use_as_input(
            doc_type=doc_type,
            document=document,
            readiness=readiness,
            acceptance_state=acceptance_state
        )
        
        return DocumentStatus(
            doc_type_id=doc_type.doc_type_id,
            document_id=document.id if document else None,
            title=doc_type.name,
            icon=doc_type.icon or "file",
            readiness=readiness,
            acceptance_state=acceptance_state,
            subtitle=subtitle,
            can_build=can_build,
            can_rebuild=can_rebuild,
            can_accept=can_accept,
            can_reject=can_reject,
            can_use_as_input=can_use_as_input,
            missing_inputs=missing_inputs,
            display_order=doc_type.display_order or 0,
        )
    
    def _derive_readiness(
        self,
        doc_type: DocumentType,
        document: Optional[Document],
        existing_type_ids: set
    ) -> tuple[str, List[str]]:
        """
        Derive readiness status from document state and dependencies.
        
        Returns:
            Tuple of (readiness_status, missing_input_list)
        
        Status meanings:
        - blocked: Cannot build - missing required input documents
        - waiting: CAN build - prerequisites met, just not built yet
        - stale: Built but inputs changed - rebuild recommended
        - ready: Built and current - safe to use
        """
        # Check for missing required inputs
        required_inputs = doc_type.required_inputs or []
        missing = [dep for dep in required_inputs if dep not in existing_type_ids]
        logger.info(f"[STATUS] {doc_type.doc_type_id}: required={required_inputs}, existing={existing_type_ids}, missing={missing}")
        
        if missing:
            return ReadinessStatus.BLOCKED, missing
        
        # Document doesn't exist yet BUT could be built (prerequisites met)
        if document is None:
            return ReadinessStatus.WAITING, []
        
        # Document exists but is stale
        if document.is_stale:
            return ReadinessStatus.STALE, []
        
        # Document exists and is current
        return ReadinessStatus.READY, []
    
    def _derive_acceptance_state(
        self,
        doc_type: DocumentType,
        document: Optional[Document]
    ) -> Optional[str]:
        """
        Derive acceptance state from document and type configuration.
        
        Returns None if:
        - Acceptance not required for this doc type
        - Document doesn't exist yet (can't accept nothing)
        """
        # Acceptance not required
        if not doc_type.acceptance_required:
            return None
        
        # Can't accept what doesn't exist
        if document is None:
            return None
        
        # Check rejection first (rejection supersedes pending acceptance)
        if document.rejected_at is not None:
            return AcceptanceState.REJECTED
        
        # Check if accepted
        if document.accepted_at is None:
            return AcceptanceState.NEEDS_ACCEPTANCE
        
        return AcceptanceState.ACCEPTED
    
    def _derive_subtitle(
        self,
        doc_type: DocumentType,
        document: Optional[Document],
        readiness: str,
        acceptance_state: Optional[str],
        missing_inputs: List[str]
    ) -> Optional[str]:
        """
        Derive contextual subtitle for UI display.
        
        Subtitles provide actionable context:
        - What's blocking
        - What needs attention
        - What role needs to act
        """
        # Blocked - show what's missing
        if readiness == ReadinessStatus.BLOCKED and missing_inputs:
            return f"Missing: {', '.join(missing_inputs)}"
        
        # Stale + Accepted - warn about review needed (ADR-007 UI Rule)
        if readiness == ReadinessStatus.STALE and acceptance_state == AcceptanceState.ACCEPTED:
            return "Inputs changed â€” review recommended"
        
        # Needs acceptance - show responsible role
        if acceptance_state == AcceptanceState.NEEDS_ACCEPTANCE:
            role = doc_type.accepted_by_role or "reviewer"
            return f"Needs acceptance ({role.title()})"
        
        # Rejected - show that changes were requested
        if acceptance_state == AcceptanceState.REJECTED:
            return "Changes requested"
        
        # Waiting + acceptance required - hint about future acceptance
        if readiness == ReadinessStatus.WAITING and doc_type.acceptance_required:
            role = doc_type.accepted_by_role or "reviewer"
            return f"Will need acceptance ({role.title()})"
        
        return None
    
    def _derive_can_use_as_input(
        self,
        doc_type: DocumentType,
        document: Optional[Document],
        readiness: str,
        acceptance_state: Optional[str]
    ) -> bool:
        """
        Determine if document can be used as input for downstream documents.
        
        Rules:
        - Blocked documents can never be used
        - Waiting (not built) documents can never be used
        - If acceptance required, must be accepted
        - Stale + accepted is allowed (with warning via subtitle)
        """
        # Must exist
        if document is None:
            return False
        
        # Blocked documents can never be used
        if readiness == ReadinessStatus.BLOCKED:
            return False
        
        # If acceptance required, must be accepted
        if doc_type.acceptance_required:
            return acceptance_state == AcceptanceState.ACCEPTED
        
        # No acceptance required - can be used if exists
        return True
    
    # =========================================================================
    # DATABASE QUERIES (async)
    # =========================================================================
    
    async def _get_project_document_types(self, db: AsyncSession) -> List[DocumentType]:
        """Get all active document types for project scope."""
        stmt = (
            select(DocumentType)
            .where(DocumentType.is_active == True)
            .where(DocumentType.scope == "project")
            .order_by(DocumentType.display_order)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())
    
    async def _get_project_documents(
        self,
        db: AsyncSession,
        project_id: UUID
    ) -> List[Document]:
        """Get all latest documents for a project."""
        stmt = (
            select(Document)
            .where(Document.space_type == "project")
            .where(Document.space_id == project_id)
            .where(Document.is_latest == True)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())
    
    async def _get_document_type(
        self,
        db: AsyncSession,
        doc_type_id: str
    ) -> Optional[DocumentType]:
        """Get a single document type by ID."""
        stmt = (
            select(DocumentType)
            .where(DocumentType.doc_type_id == doc_type_id)
            .where(DocumentType.is_active == True)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _get_document(
        self,
        db: AsyncSession,
        doc_type_id: str,
        space_type: str,
        space_id: UUID
    ) -> Optional[Document]:
        """Get the latest document of a type in a space."""
        stmt = (
            select(Document)
            .where(Document.doc_type_id == doc_type_id)
            .where(Document.space_type == space_type)
            .where(Document.space_id == space_id)
            .where(Document.is_latest == True)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _get_existing_doc_type_ids(
        self,
        db: AsyncSession,
        space_type: str,
        space_id: UUID
    ) -> set:
        """Get set of doc_type_ids that exist in a space."""
        stmt = (
            select(Document.doc_type_id)
            .where(Document.space_type == space_type)
            .where(Document.space_id == space_id)
            .where(Document.is_latest == True)
        )
        result = await db.execute(stmt)
        return set(result.scalars().all())


# =============================================================================
# MODULE-LEVEL INSTANCE
# =============================================================================

# Singleton instance for convenience
document_status_service = DocumentStatusService()

