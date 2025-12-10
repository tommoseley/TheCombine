"""
Artifact model for The Combine.

Universal storage for all artifacts (epics, features, stories, code, etc.).
"""
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import TSVECTOR
import uuid

from database import Base


class Artifact(Base):
    """
    Universal storage for all artifacts using RSP-1 paths.
    
    Every artifact (epic, feature, story, code file, etc.) is stored here with:
    - artifact_path: Unique hierarchical identifier (e.g., HMP/E001/F003/S007)
    - content: JSONB for flexible schema evolution
    - breadcrumbs: Context chain for LLM prompts
    """
    __tablename__ = "artifacts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    artifact_path = Column(String(100), nullable=False, unique=True, index=True)
    artifact_type = Column(String(50), nullable=False, index=True)
    
    # Parsed path components (for easier querying)
    project_id = Column(String(8), ForeignKey('projects.project_id', ondelete='CASCADE'), nullable=False, index=True)
    epic_id = Column(String(20), index=True)
    feature_id = Column(String(20), index=True)
    story_id = Column(String(20), index=True)
    
    # Core data
    title = Column(String(500))
    content = Column(JSONB, nullable=False)
    breadcrumbs = Column(JSONB)
    
    # Metadata
    status = Column(String(50), default='draft', index=True)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String(100))
    parent_path = Column(String(100), index=True)
    
    # Full-text search vector (auto-generated)
    search_vector = Column(TSVECTOR)
    
    # Constraints
    __table_args__ = (
        CheckConstraint("artifact_path ~ '^[A-Z]{2,8}(/[A-Z0-9-]+)*$'", name='artifacts_path_format'),
        CheckConstraint("project_id ~ '^[A-Z]{2,8}$'", name='artifacts_project_id_format'),
        Index('idx_artifacts_path', 'artifact_path'),
        Index('idx_artifacts_project_id', 'project_id'),
        Index('idx_artifacts_type', 'artifact_type'),
        Index('idx_artifacts_parent_path', 'parent_path'),
        Index('idx_artifacts_status', 'status'),
        Index('idx_artifacts_created_at', 'created_at'),
        Index('idx_artifacts_search', 'search_vector', postgresql_using='gin'),
        Index('idx_artifacts_content', 'content', postgresql_using='gin'),
    )
    
    def __repr__(self):
        return f"<Artifact {self.artifact_path} ({self.artifact_type})>"
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': str(self.id),
            'artifact_path': self.artifact_path,
            'artifact_type': self.artifact_type,
            'project_id': self.project_id,
            'epic_id': self.epic_id,
            'feature_id': self.feature_id,
            'story_id': self.story_id,
            'title': self.title,
            'content': self.content,
            'breadcrumbs': self.breadcrumbs,
            'status': self.status,
            'version': self.version,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
            'parent_path': self.parent_path
        }