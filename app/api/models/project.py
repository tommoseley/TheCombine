"""
Project model for The Combine.

Represents top-level project containers (e.g., HMP, ACME).
"""
from sqlalchemy import Column, String, Text, DateTime, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class Project(Base):
    """
    Top-level project container.
    
    Each project has a unique project_id (e.g., 'HMP', 'ACME') that serves
    as the root of all artifact paths within that project.
    """
    __tablename__ = "projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(String(8), nullable=False, unique=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    status = Column(String(50), default='active', index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String(100))
    
    meta = Column(JSONB, default={}, name='metadata')
    
    # Constraints
    __table_args__ = (
        CheckConstraint("project_id ~ '^[A-Z]{2,8}$'", name='projects_project_id_format'),
        Index('idx_projects_project_id', 'project_id'),
        Index('idx_projects_status', 'status'),
        Index('idx_projects_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Project {self.project_id}: {self.name}>"
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': str(self.id),
            'project_id': self.project_id,
            'name': self.name,
            'description': self.description,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
            'metadata': self.meta
        }