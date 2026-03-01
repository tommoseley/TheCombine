"""
Document Relation Model - Typed edges between documents.

Relations enable:
- `requires`: Gating / buildability (A can't be built until B exists)
- `derived_from`: Provenance / staleness (A was built using B as input)
- `references`: Navigation (A mentions B) [future]
- `supersedes`: Version lineage (A replaces B) [future]
"""

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

from sqlalchemy import (
    Column, String, Integer, Text, DateTime,
    ForeignKey, Index, CheckConstraint, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.sql import func

from app.core.database import Base


class DocumentRelation(Base):
    """
    DocumentRelation model - typed edges between documents.
    
    Represents relationships like:
    - Architecture Spec REQUIRES Project Discovery
    - Architecture Spec DERIVED_FROM Project Discovery
    - Architecture Spec REQUIRES Security Baseline (org standard, pinned to v2)
    """
    
    __tablename__ = "document_relations"
    
    # =========================================================================
    # IDENTITY
    # =========================================================================
    
    id: Mapped[UUID] = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid()
    )
    
    # =========================================================================
    # EDGE ENDPOINTS
    # =========================================================================
    
    from_document_id: Mapped[UUID] = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Source document (the one that has the dependency)"
    )
    
    to_document_id: Mapped[UUID] = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Target document (the one being depended on)"
    )
    
    # =========================================================================
    # EDGE TYPE
    # =========================================================================
    
    relation_type: Mapped[str] = Column(
        String(50),
        nullable=False,
        index=True,
        doc="Relation type: 'requires' | 'derived_from' | 'references' | 'supersedes'"
    )
    
    # =========================================================================
    # VERSION PINNING (for cross-space requires)
    # =========================================================================
    
    pinned_version: Mapped[Optional[int]] = Column(
        Integer,
        nullable=True,
        doc="Pinned version number (NULL = use latest)"
    )
    
    pinned_revision: Mapped[Optional[str]] = Column(
        String(64),
        nullable=True,
        doc="Pinned revision hash for exact immutability"
    )
    
    # =========================================================================
    # METADATA
    # =========================================================================
    
    notes: Mapped[Optional[str]] = Column(
        Text,
        nullable=True,
        doc="Human-readable notes about this relationship"
    )
    
    relation_metadata: Mapped[Optional[Dict[str, Any]]] = Column(
        JSONB,
        nullable=True,
        doc="Additional structured metadata"
    )
    
    # =========================================================================
    # AUDIT
    # =========================================================================
    
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    created_by: Mapped[Optional[str]] = Column(
        String(200),
        nullable=True,
        doc="Who created this relationship"
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    
    from_document: Mapped["Document"] = relationship(  # noqa: F821
        "Document",
        foreign_keys=[from_document_id],
        back_populates="outgoing_relations"
    )

    to_document: Mapped["Document"] = relationship(  # noqa: F821
        "Document",
        foreign_keys=[to_document_id],
        back_populates="incoming_relations"
    )
    
    # =========================================================================
    # CONSTRAINTS
    # =========================================================================
    
    __table_args__ = (
        # No self-references
        CheckConstraint(
            "from_document_id != to_document_id",
            name="no_self_reference"
        ),
        
        # Unique relation per type between two documents
        UniqueConstraint(
            "from_document_id", "to_document_id", "relation_type",
            name="unique_relation"
        ),
        
        # Indexes
        Index("idx_relations_from", "from_document_id"),
        Index("idx_relations_to", "to_document_id"),
        Index("idx_relations_type", "relation_type"),
    )
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    @property
    def is_pinned(self) -> bool:
        """Check if this relation is pinned to a specific version."""
        return self.pinned_version is not None or self.pinned_revision is not None
    
    def __repr__(self) -> str:
        return (
            f"<DocumentRelation("
            f"{self.from_document_id} --[{self.relation_type}]--> {self.to_document_id}"
            f"{f' @v{self.pinned_version}' if self.pinned_version else ''}"
            f")>"
        )


# =============================================================================
# RELATION TYPE CONSTANTS
# =============================================================================

class RelationType:
    """Constants for relation types."""
    
    # MVP types
    REQUIRES = "requires"           # Gating / buildability
    DERIVED_FROM = "derived_from"   # Provenance / staleness
    
    # Future types
    REFERENCES = "references"       # Loose linkage / navigation
    SUPERSEDES = "supersedes"       # Version lineage across rewrites
    CONSTRAINS = "constrains"       # Standards compliance (A defines rules B must follow)
    
    # All valid types
    ALL = [REQUIRES, DERIVED_FROM, REFERENCES, SUPERSEDES, CONSTRAINS]
    MVP = [REQUIRES, DERIVED_FROM]