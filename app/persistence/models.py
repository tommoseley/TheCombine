"""Persistence domain models."""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from enum import Enum


class DocumentStatus(str, Enum):
    """Document status values."""
    DRAFT = "draft"
    ACTIVE = "active"
    STALE = "stale"
    ARCHIVED = "archived"


@dataclass
class StoredDocument:
    """
    Domain model for a stored document.
    
    This is the persistence layer's view of a document,
    separate from the SQLAlchemy ORM model.
    """
    document_id: UUID
    document_type: str
    scope_type: str  # project, organization, team
    scope_id: str
    version: int
    title: str
    content: Dict[str, Any]
    status: DocumentStatus = DocumentStatus.DRAFT
    summary: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    created_by: Optional[str] = None
    created_by_step: Optional[str] = None
    execution_id: Optional[UUID] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_latest: bool = True
    
    @classmethod
    def create(
        cls,
        document_type: str,
        scope_type: str,
        scope_id: str,
        title: str,
        content: Dict[str, Any],
        **kwargs,
    ) -> "StoredDocument":
        """Create a new document with generated ID."""
        return cls(
            document_id=uuid4(),
            document_type=document_type,
            scope_type=scope_type,
            scope_id=scope_id,
            version=1,
            title=title,
            content=content,
            **kwargs,
        )


class ExecutionStatus(str, Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    WAITING_INPUT = "waiting_input"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class StoredExecutionState:
    """
    Persisted state of a workflow execution.
    """
    execution_id: UUID
    workflow_id: str
    scope_type: str
    scope_id: str
    status: ExecutionStatus
    current_step: Optional[str] = None
    step_states: Dict[str, Any] = field(default_factory=dict)
    context_data: Dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_by: Optional[str] = None
    
    @classmethod
    def create(
        cls,
        workflow_id: str,
        scope_type: str,
        scope_id: str,
        created_by: Optional[str] = None,
    ) -> "StoredExecutionState":
        """Create a new execution state."""
        return cls(
            execution_id=uuid4(),
            workflow_id=workflow_id,
            scope_type=scope_type,
            scope_id=scope_id,
            status=ExecutionStatus.PENDING,
            created_by=created_by,
        )
    
    def start(self, step_id: str) -> None:
        """Mark execution as started."""
        self.status = ExecutionStatus.RUNNING
        self.current_step = step_id
    
    def complete(self) -> None:
        """Mark execution as completed."""
        self.status = ExecutionStatus.COMPLETED
        self.completed_at = datetime.now(UTC)
    
    def fail(self, error: str) -> None:
        """Mark execution as failed."""
        self.status = ExecutionStatus.FAILED
        self.error_message = error
        self.completed_at = datetime.now(UTC)
