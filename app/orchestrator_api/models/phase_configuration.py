"""
PhaseConfiguration model for defining pipeline phase flow as data.

Part of PIPELINE-175A: Data-Described Pipeline Infrastructure.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, JSON, DateTime
from app.orchestrator_api.persistence.database import Base


class PhaseConfiguration(Base):
    """
    Phase configuration defining pipeline flow and role assignments.
    
    Stores which role executes each phase, what artifact is produced,
    and the next phase in sequence (null = terminal phase).
    """
    __tablename__ = "phase_configurations"
    
    id = Column(String(64), primary_key=True)  # Format: pc_<ulid>
    phase_name = Column(String(64), nullable=False, unique=True, index=True)
    role_name = Column(String(64), nullable=False)
    artifact_type = Column(String(64), nullable=False)
    next_phase = Column(String(64), nullable=True)  # NULL = terminal phase
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    config = Column(JSON, nullable=True)  # Phase-specific configuration
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f"<PhaseConfiguration(phase={self.phase_name}, role={self.role_name}, next={self.next_phase})>"