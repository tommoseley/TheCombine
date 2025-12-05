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


class Artifact(Base):
    """Artifact storage table."""
    __tablename__ = "artifacts"
    
    artifact_id = Column(String(64), primary_key=True)
    pipeline_id = Column(String(64), ForeignKey('pipelines.pipeline_id'), nullable=False, index=True)
    artifact_type = Column(String(64), nullable=False, index=True)
    phase = Column(String(32), nullable=False)
    mentor_role = Column(String(32), nullable=True)
    payload = Column(JSONType, nullable=False)
    validation_status = Column(String(16), nullable=False)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    
    # Relationship - matches back_populates in Pipeline
    pipeline = relationship("Pipeline", back_populates="artifacts")

    __table_args__ = (
        Index('idx_artifacts_pipeline_id', 'pipeline_id'),
        Index('idx_artifacts_type', 'artifact_type'),
    )
