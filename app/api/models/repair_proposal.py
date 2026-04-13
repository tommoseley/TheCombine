"""
Repair Proposal ORM Model (ADR-065).

Persists component-scoped repair proposals for canonical artifacts.
Proposals are decision-bearing: pending → accepted/rejected/superseded.
"""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, String, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


class RepairProposal(Base):
    """Stores repair proposals per ADR-065.

    Each proposal targets a single component within a canonical artifact
    and contains the proposed replacement payload.
    """

    __tablename__ = "repair_proposals"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Target artifact
    artifact_id = Column(UUID(as_uuid=True), nullable=False)
    artifact_type = Column(String(50), nullable=False)  # "TA" initially
    component_identifier = Column(String(255), nullable=False)  # component.name

    # Trigger
    trigger_finding = Column(JSONB, nullable=False)  # serialized finding

    # Proposal content
    proposed_payload = Column(JSONB, nullable=False)  # corrected component

    # Lifecycle
    status = Column(String(20), nullable=False, default="pending")
    # pending → accepted | rejected | superseded

    # Provenance
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_by = Column(String(100), nullable=False)
    decision_at = Column(DateTime(timezone=True), nullable=True)
    decision_by = Column(String(100), nullable=True)

    # Indexes
    __table_args__ = (
        Index("idx_repair_artifact", "artifact_id", "artifact_type"),
        Index("idx_repair_artifact_status", "artifact_id", "status"),
    )
