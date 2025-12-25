"""
RoleTask SQLAlchemy model.
"""

from sqlalchemy import Column, String, Text, Boolean, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class RoleTask(Base):
    """
    Role task - defines what the mentor is doing right now.
    
    Examples: 
    - architect + preliminary
    - architect + final  
    - pm + epic_creation
    - ba + story_breakdown
    """
    __tablename__ = "role_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    task_name = Column(String(100), nullable=False)
    task_prompt = Column(Text, nullable=False)
    expected_schema = Column(JSONB, nullable=True)
    progress_steps = Column(JSONB, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    version = Column(String(16), nullable=False, default="1")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String(128), nullable=True)
    notes = Column(Text, nullable=True)

    # Relationship - use string reference to avoid circular import
    role = relationship("Role", back_populates="tasks")

    def __repr__(self):
        return f"<RoleTask(role_id='{self.role_id}', task_name='{self.task_name}')>"