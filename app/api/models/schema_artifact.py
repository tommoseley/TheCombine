"""
SchemaArtifact model for ADR-031 Schema Registry.

Stores canonical schema types and document schemas as governed artifacts.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import String, DateTime, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class SchemaArtifact(Base):
    """
    DB-backed schema artifact for the Schema Registry.
    
    Per ADR-031:
    - Canonical types are reused via $ref: "schema:<schema_id>"
    - Only accepted schemas may be used for LLM generation
    - Schema JSON is hashed for auditability
    """
    
    __tablename__ = "schema_artifacts"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    
    # Identity
    schema_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Canonical schema identifier (e.g., OpenQuestionV1)",
    )
    version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="1.0",
        doc="Schema version (semver or simple)",
    )
    
    # Classification
    kind: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        doc="Schema kind: 'type', 'document', or 'envelope'",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="draft",
        doc="Lifecycle status: 'draft', 'accepted', or 'deprecated'",
    )
    
    # Content
    schema_json: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        doc="The canonical JSON Schema definition",
    )
    sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        doc="SHA256 hash of schema_json for integrity verification",
    )
    
    # Governance
    governance_refs: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        doc="References to governing ADRs and policies",
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
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        onupdate=func.now(),
    )
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "kind IN ('type', 'document', 'envelope')",
            name="ck_schema_artifacts_kind",
        ),
        CheckConstraint(
            "status IN ('draft', 'accepted', 'deprecated')",
            name="ck_schema_artifacts_status",
        ),
        Index(
            "ix_schema_artifacts_schema_id_version",
            "schema_id", "version",
            unique=True,
        ),
        Index("ix_schema_artifacts_status", "status"),
        Index("ix_schema_artifacts_kind", "kind"),
    )
    
    def __repr__(self) -> str:
        return f"<SchemaArtifact {self.schema_id}@{self.version} ({self.status})>"