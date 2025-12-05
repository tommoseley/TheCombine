"""
RolePrompt model for storing AI role prompts with versioning.

Part of PIPELINE-175A: Data-Described Pipeline Infrastructure.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, JSON, Boolean, DateTime, Index
from sqlalchemy.orm import relationship
from app.orchestrator_api.persistence.database import Base


class RolePrompt(Base):
    """
    Role prompt with versioning and activation control.
    
    Stores prompt templates for AI roles (PM, Architect, BA, Dev, QA, Commit).
    Only one active version per role enforced by repository logic.
    """
    __tablename__ = "role_prompts"
    
    id = Column(String(64), primary_key=True)  # Format: rp_<ulid>
    role_name = Column(String(64), nullable=False, index=True)
    version = Column(String(16), nullable=False)
    starting_prompt = Column(Text, nullable=True)
    bootstrapper = Column(Text, nullable=False)
    instructions = Column(Text, nullable=False)
    working_schema = Column(JSON, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_by = Column(String(128), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Relationships
    pipeline_usages = relationship("PipelinePromptUsage", back_populates="prompt")
    
    # Composite index for fast active prompt lookups
    __table_args__ = (
        Index('idx_role_prompts_role_active', 'role_name', 'is_active'),
    )
    
    def __repr__(self):
        return f"<RolePrompt(id={self.id}, role={self.role_name}, version={self.version}, active={self.is_active})>"