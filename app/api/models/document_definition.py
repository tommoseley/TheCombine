"""
DocumentDefinition model for ADR-034 Document Composition Manifest.

Stores document definitions that compose canonical components into
complete document structures for LLM generation and rendering.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import String, DateTime, CheckConstraint, Index, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class DocumentDefinition(Base):
    """
    DB-backed document definition (composition manifest).
    
    Per ADR-034:
    - Composes components into document structure
    - Defines prompt header and section ordering
    - Only accepted definitions may be used for generation
    """
    
    __tablename__ = "document_definitions"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    
    # Identity (embeds semver per D5)
    document_def_id: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        unique=True,
        doc="Canonical docdef ID with semver (e.g., docdef:EpicBacklog:1.0.0)",
    )
    
    # Optional document schema reference (nullable for MVP)
    document_schema_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("schema_artifacts.id"),
        nullable=True,
        doc="Optional FK to document schema (nullable for MVP)",
    )
    
    # Content
    prompt_header: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        doc="Role and constraints for prompt generation",
    )
    sections: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        doc="Section definitions with component bindings",
    )
    
    # Lifecycle
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="draft",
        doc="Lifecycle status: draft, accepted",
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    created_by: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    accepted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when status changed to accepted",
    )
    
    # Relationships
    document_schema = relationship("SchemaArtifact", foreign_keys=[document_schema_id])
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'accepted')",
            name="ck_document_definitions_status",
        ),
        Index("ix_document_definitions_status", "status"),
        Index("ix_document_definitions_accepted_at", "accepted_at"),
    )
    
    def __repr__(self) -> str:
        return f"<DocumentDefinition {self.document_def_id} ({self.status})>"
