"""
BreadcrumbFile model for The Combine.

Links artifacts to files referenced in their breadcrumbs.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from database import Base


class BreadcrumbFile(Base):
    """
    Links artifacts to files referenced in their breadcrumbs.
    
    Many-to-many relationship with categories:
    - must_load: Required context
    - should_load: Optional but helpful context
    - search_hint: Suggestions for finding additional context
    """
    __tablename__ = "breadcrumb_files"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    artifact_id = Column(UUID(as_uuid=True), ForeignKey('artifacts.id', ondelete='CASCADE'), nullable=False, index=True)
    file_id = Column(UUID(as_uuid=True), ForeignKey('files.id', ondelete='CASCADE'), nullable=False, index=True)
    file_category = Column(String(20), nullable=False, index=True)  # must_load, should_load, search_hint
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Constraints
    __table_args__ = (
        CheckConstraint("file_category IN ('must_load', 'should_load', 'search_hint')", name='breadcrumb_files_category'),
        Index('idx_breadcrumb_files_artifact', 'artifact_id'),
        Index('idx_breadcrumb_files_file', 'file_id'),
        Index('idx_breadcrumb_files_category', 'file_category'),
    )
    
    def __repr__(self):
        return f"<BreadcrumbFile {self.file_category}>"
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': str(self.id),
            'artifact_id': str(self.artifact_id),
            'file_id': str(self.file_id),
            'file_category': self.file_category,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }