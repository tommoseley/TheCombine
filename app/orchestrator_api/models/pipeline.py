"""SQLAlchemy ORM models for persistence."""

from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Index, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSON as PGJSON
from sqlalchemy.dialects.sqlite import JSON as SQLITEJSON

from app.orchestrator_api.persistence.database import Base, DATABASE_URL

def utcnow():
    return datetime.now(timezone.utc)
# Use appropriate JSON type based on database
JSONType = SQLITEJSON if "sqlite" in DATABASE_URL else PGJSON


class Pipeline(Base):
    """
    Pipeline metadata table.
    
    Note on state vs. current_phase:
    - For MVP, both store the same phase value (e.g., "pm_phase", "arch_phase")
    - state represents the pipeline's current status
    - current_phase tracks which phase is active
    - In future, these may diverge for async workflows
    """
    __tablename__ = "pipelines"
    
    pipeline_id = Column(String(64), primary_key=True)
    epic_id = Column(String(64), nullable=False, index=True)
    state = Column(String(32), nullable=False, index=True)
    current_phase = Column(String(32), nullable=False)
    canon_version = Column(String(16), nullable=False)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)
    completed_at = Column(DateTime, nullable=True)
    initial_context = Column(JSONType, nullable=True)
    # Relationships
    artifacts = relationship("Artifact", back_populates="pipeline")
    phase_transitions = relationship("PhaseTransition", back_populates="pipeline")
    
    # NEW: Relationship to PipelinePromptUsage (PIPELINE-175A)
    prompt_usages = relationship("PipelinePromptUsage", back_populates="pipeline")
    
    __table_args__ = (
        Index('idx_pipelines_epic_id', 'epic_id'),
        Index('idx_pipelines_state', 'state'),
        Index('idx_pipelines_created_at', 'created_at'),
    )

