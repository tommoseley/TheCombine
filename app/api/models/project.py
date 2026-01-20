"""
Project model for The Combine.

Represents top-level project containers (e.g., HMP, ACME).
"""
from sqlalchemy import Column, String, Text, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class Project(Base):
    """
    Top-level project container.
    
    Each project has a unique project_id (e.g., 'LIR-001', 'MA-002') that serves
    as the root of all artifact paths within that project.
    
    Format: 2-5 uppercase letters, hyphen, 3 digits (e.g., LIR-001)
    Application code enforces this format; no DB constraint for flexibility.
    """
    __tablename__ = "projects"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Core fields
    project_id = Column(String(20), nullable=False, unique=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    status = Column(String(50), default='active', index=True)
    icon = Column(String(32), default='folder')
    
    # Ownership fields
    owner_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    organization_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String(100))
    
    # Archive fields
    archived_at = Column(DateTime(timezone=True), nullable=True)
    archived_by = Column(UUID(as_uuid=True), nullable=True)
    archived_reason = Column(Text, nullable=True)
    
    # Metadata
    meta = Column(JSONB, default={}, name='metadata')
    
    # Indexes
    __table_args__ = (
        Index('idx_projects_project_id', 'project_id'),
        Index('idx_projects_status', 'status'),
        Index('idx_projects_created_at', 'created_at'),
        Index('idx_projects_owner_id', 'owner_id'),
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
            'icon': self.icon or 'folder',
            'owner_id': str(self.owner_id) if self.owner_id else None,
            'organization_id': str(self.organization_id) if self.organization_id else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
            'archived_at': self.archived_at.isoformat() if self.archived_at else None,
            'archived_by': str(self.archived_by) if self.archived_by else None,
            'archived_reason': self.archived_reason,
            'is_archived': self.archived_at is not None,
            'metadata': self.meta
        }