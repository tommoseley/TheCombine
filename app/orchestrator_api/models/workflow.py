"""
Workflow model for The Combine.

Tracks pipeline execution state.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

from database import Base


class Workflow(Base):
    """
    Tracks pipeline execution.
    
    Represents a single workflow execution (e.g., PM analysis, code generation)
    with its current state, inputs, outputs, and any errors.
    """
    __tablename__ = "workflows"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(String(50), unique=True, nullable=False)
    artifact_path = Column(String(100), ForeignKey('artifacts.artifact_path', ondelete='CASCADE'), nullable=False, index=True)
    workflow_type = Column(String(50), nullable=False, index=True)
    
    status = Column(String(50), nullable=False, default='pending', index=True)
    current_step = Column(String(50))
    
    input_data = Column(JSONB)
    output_data = Column(JSONB)
    error_data = Column(JSONB)
    
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    triggered_by = Column(String(100))
    meta = Column(JSONB, default={}, name='metadata')
    
    # Indexes
    __table_args__ = (
        Index('idx_workflows_artifact_path', 'artifact_path'),
        Index('idx_workflows_status', 'status'),
        Index('idx_workflows_type', 'workflow_type'),
        Index('idx_workflows_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Workflow {self.workflow_id} ({self.workflow_type}): {self.status}>"
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': str(self.id),
            'workflow_id': self.workflow_id,
            'artifact_path': self.artifact_path,
            'workflow_type': self.workflow_type,
            'status': self.status,
            'current_step': self.current_step,
            'input_data': self.input_data,
            'output_data': self.output_data,
            'error_data': self.error_data,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'triggered_by': self.triggered_by,
            'metadata': self.meta
        }