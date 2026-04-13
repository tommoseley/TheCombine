"""
Lineage Event ORM Model (ADR-063).

Persists pipeline rewind and regeneration events for audit
and traceability.
"""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, String, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


class LineageEventModel(Base):
    """Stores lineage events per ADR-063.

    Lineage events are immutable audit records that track
    pipeline state changes (rewinds and regenerations).
    """

    __tablename__ = "lineage_events"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Project scope
    project_id = Column(UUID(as_uuid=True), nullable=False)

    # Event classification
    event_type = Column(String(20), nullable=False)  # "rewind" | "regeneration"
    rewind_to_stage = Column(String(50), nullable=False)  # Pipeline stage name

    # Context
    reason = Column(String(500), nullable=False)
    actor = Column(String(100), nullable=False)

    # Affected documents (list of UUIDs stored as JSONB array)
    affected_document_ids = Column(JSONB, nullable=False, default=list)

    # Optional link to follow-up regeneration event
    regeneration_event_id = Column(UUID(as_uuid=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Indexes for common query patterns
    __table_args__ = (
        Index("idx_lineage_project", "project_id"),
        Index("idx_lineage_project_type", "project_id", "event_type"),
    )
