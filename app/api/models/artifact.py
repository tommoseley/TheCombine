"""
Artifact model for The Combine.

Represents any deliverable in the RSP-1 canonical path system.
"""

from sqlalchemy import Column, String, Integer, DateTime, Text, Index, Computed
from sqlalchemy.dialects.postgresql import UUID, JSONB, TSVECTOR
from sqlalchemy.sql import func
from datetime import datetime
import uuid

from database import Base


class Artifact(Base):
    """
    Artifact model - RSP-1 canonical path architecture.
    
    Stores all deliverables (epics, features, stories, code, etc.) with:
    - Hierarchical paths (PROJECT/EPIC/FEATURE/STORY)
    - JSONB content (schema-less, flexible)
    - Full-text search via PostgreSQL tsvector
    """
    
    __tablename__ = "artifacts"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # RSP-1 Path Components
    artifact_path = Column(String(500), unique=True, nullable=False, index=True)
    artifact_type = Column(String(50), nullable=False, index=True)
    
    # Hierarchical IDs (extracted from path)
    project_id = Column(String(50), nullable=False, index=True)
    epic_id = Column(String(50), nullable=True, index=True)
    feature_id = Column(String(50), nullable=True, index=True)
    story_id = Column(String(50), nullable=True, index=True)
    
    # Content
    title = Column(String(500), nullable=False)
    content = Column(JSONB, nullable=False, default=dict)
    breadcrumbs = Column(JSONB, nullable=False, default=dict)
    
    # Metadata
    status = Column(String(50), nullable=False, default="draft", index=True)
    version = Column(Integer, nullable=False, default=1)
    created_by = Column(String(200), nullable=True)
    parent_path = Column(String(500), nullable=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Full-text search (GENERATED COLUMN - DO NOT INSERT)
    search_vector = Column(
        TSVECTOR,
        Computed(
            "to_tsvector('english', coalesce(title, '') || ' ' || coalesce(artifact_path, ''))",
            persisted=True
        ),
        nullable=True
    )
    
    # Indexes
    __table_args__ = (
        # GIN index for full-text search
        Index('idx_artifacts_search_vector', 'search_vector', postgresql_using='gin'),
        
        # Composite indexes for common queries
        Index('idx_artifacts_project_type', 'project_id', 'artifact_type'),
        Index('idx_artifacts_project_status', 'project_id', 'status'),
        Index('idx_artifacts_epic_type', 'epic_id', 'artifact_type'),
        
        # JSONB GIN indexes for content queries
        Index('idx_artifacts_content', 'content', postgresql_using='gin'),
        Index('idx_artifacts_breadcrumbs', 'breadcrumbs', postgresql_using='gin'),
    )
    
    def __repr__(self):
        return f"<Artifact(path='{self.artifact_path}', type='{self.artifact_type}', status='{self.status}')>"
    
    def to_dict(self):
        """Convert artifact to dictionary."""
        return {
            "id": str(self.id),
            "artifact_path": self.artifact_path,
            "artifact_type": self.artifact_type,
            "project_id": self.project_id,
            "epic_id": self.epic_id,
            "feature_id": self.feature_id,
            "story_id": self.story_id,
            "title": self.title,
            "content": self.content,
            "breadcrumbs": self.breadcrumbs,
            "status": self.status,
            "version": self.version,
            "created_by": self.created_by,
            "parent_path": self.parent_path,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }