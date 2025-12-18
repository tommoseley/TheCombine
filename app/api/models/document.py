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
    Column, String, Integer, Boolean, Text, DateTime,
    ForeignKey, Index, CheckConstraint, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB, TSVECTOR
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.sql import func

from database import Base


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
    outgoing_relations: Mapped[List["DocumentRelation"]] = relationship(
        "DocumentRelation",
        foreign_keys="DocumentRelation.from_document_id",
        back_populates="from_document",
        cascade="all, delete-orphan"
    )
    
    # Relations where this document is the target (to_document)
    incoming_relations: Mapped[List["DocumentRelation"]] = relationship(
        "DocumentRelation",
        foreign_keys="DocumentRelation.to_document_id",
        back_populates="to_document",
        cascade="all, delete-orphan"
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
    
    @property
    def requires(self) -> List["DocumentRelation"]:
        """Get documents this document requires."""
        return [r for r in self.outgoing_relations if r.relation_type == "requires"]
    
    @property
    def derived_from(self) -> List["DocumentRelation"]:
        """Get documents this document was derived from."""
        return [r for r in self.outgoing_relations if r.relation_type == "derived_from"]
    
    @property
    def required_by(self) -> List["DocumentRelation"]:
        """Get documents that require this document."""
        return [r for r in self.incoming_relations if r.relation_type == "requires"]
    
    @property
    def derivatives(self) -> List["DocumentRelation"]:
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
    
    def __repr__(self) -> str:
        return f"<Document(id={self.id}, type={self.doc_type_id}, title='{self.title[:30]}...')>"