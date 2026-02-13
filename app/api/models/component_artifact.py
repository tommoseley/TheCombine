"""
ComponentArtifact model for ADR-034 Canonical Components.

Stores canonical component specifications that bind schema, prompt guidance,
and view bindings together as a reusable unit.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import String, DateTime, CheckConstraint, Index, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class ComponentArtifact(Base):
    """
    DB-backed canonical component specification.
    
    Per ADR-034:
    - Binds schema + prompt guidance + view bindings
    - Component specs are versioned via component_id (embeds semver)
    - Only accepted components may be used in document definitions
    """
    
    __tablename__ = "component_artifacts"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    
    # Identity (embeds semver per D5)
    component_id: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        unique=True,
        doc="Canonical component ID with semver (e.g., component:OpenQuestionV1:1.0.0)",
    )
    
    # Schema reference
    schema_artifact_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("schema_artifacts.id"),
        nullable=False,
        doc="FK to schema_artifacts",
    )
    schema_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Denormalized schema ID for convenience (e.g., schema:OpenQuestionV1)",
    )
    
    # Content
    generation_guidance: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        doc="Prompt generation bullets and instructions",
    )
    view_bindings: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        doc="Channel-specific fragment bindings",
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
    schema_artifact = relationship("SchemaArtifact", foreign_keys=[schema_artifact_id])
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'accepted')",
            name="ck_component_artifacts_status",
        ),
        Index("ix_component_artifacts_schema_artifact_id", "schema_artifact_id"),
        Index("ix_component_artifacts_status", "status"),
        Index("ix_component_artifacts_accepted_at", "accepted_at"),
    )
    
    def __repr__(self) -> str:
        return f"<ComponentArtifact {self.component_id} ({self.status})>"
