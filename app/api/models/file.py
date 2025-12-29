"""
File model for The Combine.

Represents context files referenced in breadcrumbs.
"""
from sqlalchemy import Column, String, Integer, Text, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import TSVECTOR
import uuid

from app.core.database import Base


class File(Base):
    """
    Context files referenced in breadcrumbs.
    
    Stores files that provide context for artifact generation, with full-text
    search capabilities for efficient retrieval.
    """
    __tablename__ = "files"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_path = Column(String(500), nullable=False, unique=True, index=True)
    content = Column(Text)
    content_hash = Column(String(64), index=True)
    file_type = Column(String(50), index=True)
    
    size_bytes = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Full-text search vector (auto-generated)
    search_vector = Column(TSVECTOR)
    
    # Indexes
    __table_args__ = (
        Index('idx_files_path', 'file_path'),
        Index('idx_files_type', 'file_type'),
        Index('idx_files_hash', 'content_hash'),
        Index('idx_files_search', 'search_vector', postgresql_using='gin'),
    )
    
    def __repr__(self):
        return f"<File {self.file_path}>"
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': str(self.id),
            'file_path': self.file_path,
            'content': self.content,
            'content_hash': self.content_hash,
            'file_type': self.file_type,
            'size_bytes': self.size_bytes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }