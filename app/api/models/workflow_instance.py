"""
WorkflowInstance and WorkflowInstanceHistory models for The Combine.

Per ADR-046: Project-scoped POW instances stored in the database
as mutable runtime data with append-only audit trail.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class WorkflowInstance(Base):
    """
    Project-scoped workflow instance.

    Created by snapshotting a reference or template POW from combine-config/.
    Mutable within the project context. One active instance per project.
    """
    __tablename__ = "workflow_instances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey('projects.id', ondelete='CASCADE'),
        nullable=False,
        unique=True,
    )
    base_workflow_ref = Column(JSONB, nullable=False)
    effective_workflow = Column(JSONB, nullable=False)
    status = Column(String(50), nullable=False, server_default='active')
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    history = relationship(
        "WorkflowInstanceHistory",
        back_populates="instance",
        cascade="all, delete-orphan",
        order_by="WorkflowInstanceHistory.changed_at.desc()",
    )

    def __repr__(self):
        return f"<WorkflowInstance project={self.project_id} status={self.status}>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "base_workflow_ref": self.base_workflow_ref,
            "effective_workflow": self.effective_workflow,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class WorkflowInstanceHistory(Base):
    """
    Append-only audit log for workflow instance changes.

    Records are never updated or deleted directly -- only via CASCADE
    when the parent instance is removed.
    """
    __tablename__ = "workflow_instance_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instance_id = Column(
        UUID(as_uuid=True),
        ForeignKey('workflow_instances.id', ondelete='CASCADE'),
        nullable=False,
    )
    change_type = Column(String(50), nullable=False)
    change_detail = Column(JSONB)
    changed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    changed_by = Column(String(100))

    instance = relationship("WorkflowInstance", back_populates="history")

    def __repr__(self):
        return f"<WorkflowInstanceHistory {self.change_type} at {self.changed_at}>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "instance_id": str(self.instance_id),
            "change_type": self.change_type,
            "change_detail": self.change_detail,
            "changed_at": self.changed_at.isoformat() if self.changed_at else None,
            "changed_by": self.changed_by,
        }
