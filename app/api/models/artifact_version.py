"""
ArtifactVersion model for The Combine.

Tracks version history for all artifacts.
"""
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

from database import Base


class ArtifactVersion(Base):
    """
    Version history for artifacts.
    
    Every time an artifact is modified, a new version is created with a
    complete snapshot of the artifact's state at that point in time.
    """
    __tablename__ = "artifact_versions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    artifact_id = Column(UUID(as_uuid=True), ForeignKey('artifacts.id', ondelete='CASCADE'), nullable=False, index=True)
    artifact_path = Column(String(100), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    
    title = Column(String(500))
    content = Column(JSONB, nullable=False)
    breadcrumbs = Column(JSONB)
    status = Column(String(50))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    created_by = Column(String(100))
    change_summary = Column(Text)
    
    # Constraints
    __table_args__ = (
        Index('idx_artifact_versions_artifact_id', 'artifact_id'),
        Index('idx_artifact_versions_path', 'artifact_path'),
        Index('idx_artifact_versions_created_at', 'created_at'),
        {'schema': None}  # Use default schema
    )
    
    def __repr__(self):
        return f"<ArtifactVersion {self.artifact_path} v{self.version}>"
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': str(self.id),
            'artifact_id': str(self.artifact_id),
            'artifact_path': self.artifact_path,
            'version': self.version,
            'title': self.title,
            'content': self.content,
            'breadcrumbs': self.breadcrumbs,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by,
            'change_summary': self.change_summary
        }