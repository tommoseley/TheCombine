"""
Fragment models for ADR-032 Fragment-Based Rendering.

Stores canonical rendering fragments and their bindings to schema types.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import String, Text, Boolean, DateTime, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class FragmentArtifact(Base):
    """
    DB-backed fragment artifact for the Fragment Registry.
    
    Per ADR-032:
    - Fragments render one instance of a canonical schema type
    - Fragments are versioned, auditable artifacts
    - Fragment markup is hashed for integrity verification
    """
    
    __tablename__ = "fragment_artifacts"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    
    # Identity
    fragment_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Fragment identifier (e.g., OpenQuestionV1Fragment)",
    )
    version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="1.0",
        doc="Fragment version",
    )
    
    # Binding target
    schema_type_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Canonical schema type this fragment renders",
    )
    
    # Lifecycle
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="draft",
        doc="Lifecycle status: 'draft', 'accepted', or 'deprecated'",
    )
    
    # Content
    fragment_markup: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="HTML/Jinja2 template content",
    )
    sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        doc="SHA256 hash of fragment_markup for integrity verification",
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
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'accepted', 'deprecated')",
            name="ck_fragment_artifacts_status",
        ),
        Index(
            "ix_fragment_artifacts_fragment_id_version",
            "fragment_id", "version",
            unique=True,
        ),
        Index("ix_fragment_artifacts_schema_type_id", "schema_type_id"),
        Index("ix_fragment_artifacts_status", "status"),
    )
    
    def __repr__(self) -> str:
        return f"<FragmentArtifact {self.fragment_id}@{self.version} ({self.status})>"


class FragmentBinding(Base):
    """
    Binding between a canonical schema type and its active fragment.
    
    Per ADR-032:
    - Only one active binding per schema_type_id
    - Bindings can be activated/deactivated for versioning
    """
    
    __tablename__ = "fragment_bindings"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    
    # Binding
    schema_type_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Canonical schema type ID",
    )
    fragment_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Bound fragment ID",
    )
    fragment_version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        doc="Bound fragment version",
    )
    
    # Active flag
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
        doc="Whether this binding is currently active",
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
    
    __table_args__ = (
        # Unique active binding per schema_type_id (partial index)
        Index(
            "ix_fragment_bindings_unique_active",
            "schema_type_id",
            unique=True,
            postgresql_where="is_active = true",
        ),
        Index("ix_fragment_bindings_fragment_id", "fragment_id"),
    )
    
    def __repr__(self) -> str:
        active = "active" if self.is_active else "inactive"
        return f"<FragmentBinding {self.schema_type_id} -> {self.fragment_id}@{self.fragment_version} ({active})>"