"""
Document Model - Core artifact storage for The Combine.

Every document lives in a space (project, organization, team) and has a type.
Documents are versioned and can be related to other documents.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
import hashlib
import json

from sqlalchemy import (
    Column, String, Integer, Boolean, Text, DateTime, Enum,
    ForeignKey, Index
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB, TSVECTOR
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.sql import func

from app.core.database import Base


class Document(Base):
    """
    Document model - the primary artifact in The Combine.
    
    Documents are typed (via doc_type_id) and live in a space (project, org, team).
    They are versioned and can have relationships to other documents.
    """
    
    __tablename__ = "documents"
    
    # =========================================================================
    # IDENTITY
    # =========================================================================
    
    id: Mapped[UUID] = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid()
    )
    
    # =========================================================================
    # OWNERSHIP - Which space does this document live in?
    # =========================================================================
    
    space_type: Mapped[str] = Column(
        String(50),
        nullable=False,
        index=True,
        doc="Space type: 'project' | 'organization' | 'team'"
    )
    
    space_id: Mapped[UUID] = Column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True,
        doc="UUID of the owning entity (project, org, or team)"
    )
    
    # =========================================================================
    # DOCUMENT OWNERSHIP (ADR-011-Part-2)
    # =========================================================================
    
    parent_document_id: Mapped[Optional[UUID]] = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
        doc="Parent document ID for ownership hierarchy (ADR-011-Part-2)"
    )

    # Stable domain identifier for multi-instance doc types (WS-INSTANCE-ID-001)
    # e.g., epic_id='backend_api_foundation'. NULL for single-instance types.
    instance_id: Mapped[Optional[str]] = Column(
        String(200),
        nullable=True,
        doc="Stable domain identifier for multi-instance doc types (e.g., epic_id). NULL for single-instance types."
    )

    # =========================================================================
    # TYPE - What kind of document is this?
    # =========================================================================
    
    doc_type_id: Mapped[str] = Column(
        String(100),
        ForeignKey("document_types.doc_type_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        doc="Document type from registry"
    )
    
    # =========================================================================
    # VERSIONING
    # =========================================================================
    
    version: Mapped[int] = Column(
        Integer,
        nullable=False,
        default=1,
        doc="Version number, increments on major changes"
    )
    
    revision_hash: Mapped[Optional[str]] = Column(
        String(64),
        nullable=True,
        doc="SHA-256 hash of content for immutability verification"
    )

    schema_bundle_sha256: Mapped[Optional[str]] = Column(
        String(100),
        nullable=True,
        doc="Schema bundle hash at generation time (Phase 2 WS-DOCUMENT-SYSTEM-CLEANUP)"
    )
    
    is_latest: Mapped[bool] = Column(
        Boolean,
        nullable=False,
        default=True,
        doc="True if this is the latest version of this doc type in this space"
    )
    
    # =========================================================================
    # CONTENT
    # =========================================================================
    
    title: Mapped[str] = Column(
        String(500),
        nullable=False,
        doc="Human-readable title"
    )
    
    summary: Mapped[Optional[str]] = Column(
        Text,
        nullable=True,
        doc="Short description, can be AI-generated"
    )
    
    content: Mapped[Dict[str, Any]] = Column(
        JSONB,
        nullable=False,
        doc="The actual document data as JSON"
    )
    
    # =========================================================================
    # STATUS
    # =========================================================================
    
    status: Mapped[str] = Column(
        String(50),
        nullable=False,
        default="draft",
        doc="Status: draft | active | stale | archived"
    )
    
    is_stale: Mapped[bool] = Column(
        Boolean,
        nullable=False,
        default=False,
        doc="True when inputs have changed and doc may need rebuild"
    )

    # =========================================================================
    # LIFECYCLE STATE (ADR-036)
    # =========================================================================
    
    lifecycle_state: Mapped[str] = Column(
        Enum(
            'generating', 'partial', 'complete', 'stale',
            name='document_lifecycle_state',
            create_type=False,  # Created by migration
        ),
        nullable=False,
        default='complete',
        doc="ADR-036 lifecycle state: generating | partial | complete | stale"
    )
    
    state_changed_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="Timestamp of last lifecycle state change"
    )
    
    # =========================================================================
    # ACCEPTANCE (ADR-007)
    # =========================================================================
    
    accepted_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when document was accepted"
    )
    
    accepted_by: Mapped[Optional[str]] = Column(
        String(200),
        nullable=True,
        doc="User ID or identifier who accepted the document"
    )
    
    rejected_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when document was rejected (most recent rejection)"
    )
    
    rejected_by: Mapped[Optional[str]] = Column(
        String(200),
        nullable=True,
        doc="User ID or identifier who rejected the document"
    )
    
    rejection_reason: Mapped[Optional[str]] = Column(
        Text,
        nullable=True,
        doc="Human-provided reason for rejection"
    )
    
    # =========================================================================
    # PROVENANCE - Who/what created this document?
    # =========================================================================
    
    created_by: Mapped[Optional[str]] = Column(
        String(200),
        nullable=True,
        doc="User ID or system identifier"
    )
    
    created_by_type: Mapped[Optional[str]] = Column(
        String(50),
        nullable=True,
        doc="Creator type: 'user' | 'builder' | 'import'"
    )
    
    builder_metadata: Mapped[Optional[Dict[str, Any]]] = Column(
        JSONB,
        nullable=True,
        doc="Build metadata: model, tokens, prompt_id, etc."
    )
    
    # =========================================================================
    # TIMESTAMPS
    # =========================================================================
    
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    updated_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # =========================================================================
    # SEARCH
    # =========================================================================
    
    search_vector: Mapped[Optional[str]] = Column(
        TSVECTOR,
        nullable=True,
        doc="Full-text search vector"
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    
    # Relations where this document is the source (from_document)
    outgoing_relations: Mapped[List["DocumentRelation"]] = relationship(  # noqa: F821
        "DocumentRelation",
        foreign_keys="DocumentRelation.from_document_id",
        back_populates="from_document",
        # Note: No cascade delete per ADR-011-Part-2 - delete with children forbidden
    )

    # Relations where this document is the target (to_document)
    incoming_relations: Mapped[List["DocumentRelation"]] = relationship(  # noqa: F821
        "DocumentRelation",
        foreign_keys="DocumentRelation.to_document_id",
        back_populates="to_document",
        # Note: No cascade delete per ADR-011-Part-2 - delete with children forbidden
    )
    
    
    # =========================================================================
    # OWNERSHIP HIERARCHY (ADR-011-Part-2)
    # =========================================================================
    
    parent: Mapped[Optional["Document"]] = relationship(
        "Document",
        remote_side=[id],
        foreign_keys=[parent_document_id],
        back_populates="children",
    )
    
    children: Mapped[List["Document"]] = relationship(
        "Document",
        foreign_keys="Document.parent_document_id",
        back_populates="parent",
    )
    # =========================================================================
    # INDEXES (defined in __table_args__)
    # =========================================================================
    
    __table_args__ = (
        # Composite index for space lookups
        Index("idx_documents_space", "space_type", "space_id"),
        
        # Unique: only one "latest" doc per type per space
        Index(
            "idx_documents_unique_latest",
            "space_type", "space_id", "doc_type_id",
            unique=True,
            postgresql_where=(is_latest == True)
        ),
        
        # Full-text search
        Index("idx_documents_search", "search_vector", postgresql_using="gin"),
        
        # Acceptance status index (ADR-007)
        Index(
            "idx_documents_acceptance",
            "accepted_at", "rejected_at",
            postgresql_where=(is_latest == True)
        ),
    )
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def compute_revision_hash(self) -> str:
        """Compute SHA-256 hash of content for immutability verification."""
        content_str = json.dumps(self.content, sort_keys=True, default=str)
        return hashlib.sha256(content_str.encode()).hexdigest()
    
    def update_revision_hash(self) -> None:
        """Update the revision hash based on current content."""
        self.revision_hash = self.compute_revision_hash()
    
    # =========================================================================
    # OWNERSHIP METHODS (ADR-011-Part-2)
    # =========================================================================
    
    def get_ancestor_chain(self) -> List["Document"]:
        """Walk parent chain upward. Returns [parent, grandparent, ...] or []."""
        chain = []
        current = self.parent
        while current is not None:
            chain.append(current)
            current = current.parent
        return chain
    
    def has_children(self) -> bool:
        """Check if document has any children."""
        return len(self.children) > 0
    
    @property
    def requires(self) -> List["DocumentRelation"]:  # noqa: F821
        """Get documents this document requires."""
        return [r for r in self.outgoing_relations if r.relation_type == "requires"]

    @property
    def derived_from(self) -> List["DocumentRelation"]:  # noqa: F821
        """Get documents this document was derived from."""
        return [r for r in self.outgoing_relations if r.relation_type == "derived_from"]

    @property
    def required_by(self) -> List["DocumentRelation"]:  # noqa: F821
        """Get documents that require this document."""
        return [r for r in self.incoming_relations if r.relation_type == "requires"]

    @property
    def derivatives(self) -> List["DocumentRelation"]:  # noqa: F821
        """Get documents derived from this document."""
        return [r for r in self.incoming_relations if r.relation_type == "derived_from"]
    
    # =========================================================================
    # ACCEPTANCE METHODS (ADR-007)
    # =========================================================================
    
    @property
    def is_accepted(self) -> bool:
        """Check if document has been accepted."""
        return self.accepted_at is not None and self.rejected_at is None
    
    @property
    def is_rejected(self) -> bool:
        """Check if document has been rejected (and not subsequently accepted)."""
        if self.rejected_at is None:
            return False
        if self.accepted_at is None:
            return True
        # If both exist, the later one wins
        return self.rejected_at > self.accepted_at
    
    @property
    def needs_acceptance(self) -> bool:
        """Check if document needs acceptance (not yet accepted or rejected)."""
        return self.accepted_at is None and self.rejected_at is None
    
    def accept(self, accepted_by: str) -> None:
        """
        Accept this document.
        
        Clears rejection state if previously rejected.
        """
        self.accepted_at = func.now()
        self.accepted_by = accepted_by
        # Clear rejection (acceptance supersedes rejection)
        self.rejected_at = None
        self.rejected_by = None
        self.rejection_reason = None
    
    def reject(self, rejected_by: str, reason: str) -> None:
        """
        Reject this document.
        
        Clears acceptance state if previously accepted.
        """
        self.rejected_at = func.now()
        self.rejected_by = rejected_by
        self.rejection_reason = reason
        # Clear acceptance (rejection supersedes acceptance)
        self.accepted_at = None
        self.accepted_by = None
    
    def clear_acceptance(self) -> None:
        """
        Clear all acceptance/rejection state.
        
        Used when document is rebuilt and needs fresh review.
        """
        self.accepted_at = None
        self.accepted_by = None
        self.rejected_at = None
        self.rejected_by = None
        self.rejection_reason = None
    

    # =========================================================================
    # LIFECYCLE STATE METHODS (ADR-036)
    # =========================================================================
    
    # Valid state transitions per ADR-036
    VALID_TRANSITIONS = {
        'generating': ['partial', 'complete'],
        'partial': ['generating', 'complete', 'stale'],
        'complete': ['partial', 'stale'],
        'stale': ['generating'],
    }
    
    def can_transition_to(self, new_state: str) -> bool:
        """Check if transition to new_state is valid per ADR-036."""
        if self.lifecycle_state is None:
            return True  # Initial state
        valid_targets = self.VALID_TRANSITIONS.get(self.lifecycle_state, [])
        return new_state in valid_targets
    
    def set_lifecycle_state(self, new_state: str) -> None:
        """
        Set lifecycle state with validation and timestamp update.
        
        Raises ValueError if transition is invalid.
        """
        if not self.can_transition_to(new_state):
            raise ValueError(
                f"Invalid state transition: {self.lifecycle_state} -> {new_state}"
            )
        self.lifecycle_state = new_state
        self.state_changed_at = func.now()
    
    def mark_generating(self) -> None:
        """Mark document as generating."""
        self.set_lifecycle_state("generating")
    
    def mark_partial(self) -> None:
        """Mark document as partial (some sections complete)."""
        self.set_lifecycle_state("partial")
    
    def mark_complete(self) -> None:
        """Mark document as complete."""
        self.set_lifecycle_state("complete")
    
    def mark_stale(self) -> None:
        """Mark document as stale due to upstream changes."""
        # Stale can be set from partial or complete
        if self.lifecycle_state in ('partial', 'complete'):
            self.lifecycle_state = "stale"
            self.state_changed_at = func.now()
            self.is_stale = True  # Keep legacy field in sync

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, type={self.doc_type_id}, title='{self.title[:30]}...')>"