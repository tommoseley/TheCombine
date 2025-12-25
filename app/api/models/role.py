"""
Role and RoleTask SQLAlchemy models.

Add these to your app/api/models/__init__.py or models.py
"""

from sqlalchemy import Column, String, Text, Boolean, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class Role(Base):
    """
    Role identity - defines who the mentor is.
    
    Examples: architect, pm, ba, developer, qa
    """
    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), unique=True, nullable=False, index=True)
    identity_prompt = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    tasks = relationship("RoleTask", back_populates="role", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Role(name='{self.name}')>"