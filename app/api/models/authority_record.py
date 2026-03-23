"""
Authority Record ORM Model (ADR-064).

Persists durable authority records — PGC answers that survive
pipeline rewind and regeneration.
"""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, String, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


class AuthorityRecord(Base):
    """Stores durable authority records per ADR-064.

    Authority records are project-scoped and persist across
    execution boundaries. They are the source of truth for
    what the user declared as binding.
    """

    __tablename__ = "authority_records"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Project scope
    project_id = Column(UUID(as_uuid=True), nullable=False)

    # Authority classification
    authority_type = Column(String(50), nullable=False)  # "pgc_answer" (MVP)
    stage = Column(String(20), nullable=False)  # PipelineStage name
    key = Column(String(255), nullable=False)  # question_id / constraint_id
    value = Column(JSONB, nullable=False)  # arbitrary JSON answer/value

    # Provenance
    source_execution_id = Column(UUID(as_uuid=True), nullable=False)
    lineage_path_id = Column(UUID(as_uuid=True), nullable=False)  # MVP: execution_id surrogate
    actor = Column(String(100), nullable=False)

    # Lifecycle
    status = Column(String(20), nullable=False, default="current")
    superseded_by = Column(UUID(as_uuid=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Indexes for common query patterns
    __table_args__ = (
        Index("idx_authority_project_status", "project_id", "status"),
        Index("idx_authority_supersession", "project_id", "authority_type", "key", "status"),
        Index("idx_authority_lineage_path", "lineage_path_id"),
    )

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "authority_type": self.authority_type,
            "stage": self.stage,
            "key": self.key,
            "value": self.value,
            "source_execution_id": str(self.source_execution_id),
            "lineage_path_id": str(self.lineage_path_id),
            "actor": self.actor,
            "status": self.status,
            "superseded_by": str(self.superseded_by) if self.superseded_by else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
