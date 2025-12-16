"""
RolePrompt model for The Combine.

Stores prompt templates for PM, Architect, BA, Developer, and QA mentors.
Zero hard-coded prompts - all externalized to database.
"""
from sqlalchemy import Column, String, Text, DateTime, Boolean, Index, JSON
from sqlalchemy.sql import func

from database import Base


class RolePrompt(Base):
    """
    Prompt templates for mentor roles.
    
    Each role (pm, architect, ba, developer, qa) can have multiple versions,
    with one marked as active at any time.
    """
    __tablename__ = "role_prompts"
    
    id = Column(String(64), primary_key=True)  # e.g., "pm-v1", "architect-v2"
    role_name = Column(String(64), nullable=False, index=True)  # pm, architect, ba, developer, qa
    version = Column(String(16), nullable=False)  # "1", "2", "2.1", etc.
    instructions = Column(Text, nullable=False)  # The prompt template
    expected_schema = Column(JSON)  # JSON schema for validation
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    created_by = Column(String(128))
    notes = Column(Text)
    
    # Indexes
    __table_args__ = (
        Index('idx_role_prompts_role_name', 'role_name'),
        Index('idx_role_prompts_active', 'is_active'),
        Index('idx_role_prompts_version', 'role_name', 'version'),
    )
    
    def __repr__(self):
        return f"<RolePrompt {self.role_name} v{self.version} (active={self.is_active})>"
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'role_name': self.role_name,
            'version': self.version,
            'instructions': self.instructions,
            'expected_schema': self.expected_schema,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
            'notes': self.notes
        }