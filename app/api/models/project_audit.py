"""
ProjectAudit model for The Combine.

Append-only audit log for project lifecycle events.
"""

from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class ProjectAudit(Base):
    """
    Append-only audit log for project lifecycle events.
    
    Immutable - records are never updated or deleted.
    """
    
    __tablename__ = "project_audit"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id', ondelete='RESTRICT'), nullable=False)
    actor_user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete='SET NULL'), nullable=True)
    action = Column(String, nullable=False)
    reason = Column(Text, nullable=True)
    # Use 'meta' as Python attr, 'metadata' as DB column (metadata is reserved in SQLAlchemy)
    meta = Column('metadata', JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "actor_user_id": str(self.actor_user_id) if self.actor_user_id else None,
            "action": self.action,
            "reason": self.reason,
            "metadata": self.meta,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }