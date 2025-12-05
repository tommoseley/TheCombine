
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



class PhaseTransition(Base):
    """Phase transition audit trail."""
    __tablename__ = "phase_transitions"
    
    transition_id = Column(String(64), primary_key=True)
    pipeline_id = Column(String(64), ForeignKey('pipelines.pipeline_id'), nullable=False, index=True)
    from_state = Column(String(32), nullable=False)
    to_state = Column(String(32), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=utcnow)
    reason = Column(String(256), nullable=True)
        
    # Relationship - matches back_populates in Pipeline
    pipeline = relationship("Pipeline", back_populates="phase_transitions")

    __table_args__ = (
        Index('idx_transitions_pipeline_id', 'pipeline_id'),
    )

    # app/orchestrator_api/persistence/models.py
