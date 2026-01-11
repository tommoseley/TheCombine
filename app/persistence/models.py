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


# =============================================================================
# ADR-035: LLM Thread Queue Models
# =============================================================================

class ThreadStatus(str, Enum):
    """Thread status values."""
    OPEN = "open"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELED = "canceled"


class WorkItemStatus(str, Enum):
    """Work item status values."""
    QUEUED = "queued"
    CLAIMED = "claimed"
    RUNNING = "running"
    APPLIED = "applied"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


class LedgerEntryType(str, Enum):
    """Ledger entry types."""
    PROMPT = "prompt"
    RESPONSE = "response"
    PARSE_REPORT = "parse_report"
    MUTATION_REPORT = "mutation_report"
    ERROR = "error"


class ErrorCode(str, Enum):
    """Standardized error codes for work items."""
    LOCKED = "LOCKED"
    PROVIDER_RATE_LIMIT = "PROVIDER_RATE_LIMIT"
    PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
    SCHEMA_INVALID = "SCHEMA_INVALID"
    MUTATION_CONFLICT = "MUTATION_CONFLICT"
    UNKNOWN = "UNKNOWN"


@dataclass
class LLMThread:
    """
    Durable container for user intent (ADR-035).
    
    A Thread represents one semantic user intent (e.g., "Generate stories for Epic X").
    Threads are operation-scoped, not conversational.
    """
    id: UUID
    kind: str  # story_generate_epic, story_generate_all, etc.
    space_type: str  # project
    space_id: UUID
    target_ref: Dict[str, Any]  # {doc_type, doc_id, epic_id?}
    status: ThreadStatus = ThreadStatus.OPEN
    parent_thread_id: Optional[UUID] = None
    idempotency_key: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    closed_at: Optional[datetime] = None
    
    @classmethod
    def create(
        cls,
        kind: str,
        space_type: str,
        space_id: UUID,
        target_ref: Dict[str, Any],
        idempotency_key: Optional[str] = None,
        parent_thread_id: Optional[UUID] = None,
        created_by: Optional[str] = None,
    ) -> "LLMThread":
        """Create a new thread."""
        return cls(
            id=uuid4(),
            kind=kind,
            space_type=space_type,
            space_id=space_id,
            target_ref=target_ref,
            idempotency_key=idempotency_key,
            parent_thread_id=parent_thread_id,
            created_by=created_by,
        )
    
    def start(self) -> None:
        """Mark thread as running."""
        self.status = ThreadStatus.RUNNING
    
    def complete(self) -> None:
        """Mark thread as complete."""
        self.status = ThreadStatus.COMPLETE
        self.closed_at = datetime.now(UTC)
    
    def fail(self) -> None:
        """Mark thread as failed."""
        self.status = ThreadStatus.FAILED
        self.closed_at = datetime.now(UTC)
    
    def cancel(self) -> None:
        """Mark thread as canceled."""
        self.status = ThreadStatus.CANCELED
        self.closed_at = datetime.now(UTC)
    
    @property
    def is_active(self) -> bool:
        """Check if thread is still active."""
        return self.status in (ThreadStatus.OPEN, ThreadStatus.RUNNING)
    
    @property
    def is_terminal(self) -> bool:
        """Check if thread has reached a terminal state."""
        return self.status in (ThreadStatus.COMPLETE, ThreadStatus.FAILED, ThreadStatus.CANCELED)


@dataclass
class LLMWorkItem:
    """
    Execution unit in the queue (ADR-035).
    
    A Work Item is a single executable unit, typically one LLM call
    followed by validation and a lock-safe mutation.
    """
    id: UUID
    thread_id: UUID
    sequence: int = 1
    status: WorkItemStatus = WorkItemStatus.QUEUED
    attempt: int = 1
    lock_scope: Optional[str] = None  # project:{id} or epic:{id}
    not_before: Optional[datetime] = None
    error_code: Optional[ErrorCode] = None
    error_message: Optional[str] = None  # Informational only; authoritative context in ledger
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    
    @classmethod
    def create(
        cls,
        thread_id: UUID,
        sequence: int = 1,
        lock_scope: Optional[str] = None,
    ) -> "LLMWorkItem":
        """Create a new work item."""
        return cls(
            id=uuid4(),
            thread_id=thread_id,
            sequence=sequence,
            lock_scope=lock_scope,
        )
    
    def claim(self) -> None:
        """Claim work item for processing."""
        self.status = WorkItemStatus.CLAIMED
        self.started_at = datetime.now(UTC)
    
    def start(self) -> None:
        """Mark work item as running."""
        self.status = WorkItemStatus.RUNNING
    
    def apply(self) -> None:
        """Mark work item as successfully applied."""
        self.status = WorkItemStatus.APPLIED
        self.finished_at = datetime.now(UTC)
    
    def fail(self, error_code: ErrorCode, error_message: str) -> None:
        """Mark work item as failed."""
        self.status = WorkItemStatus.FAILED
        self.error_code = error_code
        self.error_message = error_message
        self.finished_at = datetime.now(UTC)
    
    def dead_letter(self, error_code: ErrorCode, error_message: str) -> None:
        """Move work item to dead letter."""
        self.status = WorkItemStatus.DEAD_LETTER
        self.error_code = error_code
        self.error_message = error_message
        self.finished_at = datetime.now(UTC)
    
    @property
    def is_terminal(self) -> bool:
        """Check if work item has reached a terminal state."""
        return self.status in (WorkItemStatus.APPLIED, WorkItemStatus.FAILED, WorkItemStatus.DEAD_LETTER)


@dataclass
class LLMLedgerEntry:
    """
    Immutable execution record (ADR-035).
    
    A Ledger Entry records what the system paid for and received.
    Ledger entries are immutable and append-only.
    """
    id: UUID
    thread_id: UUID
    work_item_id: Optional[UUID]
    entry_type: LedgerEntryType
    payload: Dict[str, Any]
    payload_hash: Optional[str] = None  # SHA256 for dedup/verification
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    
    @classmethod
    def create(
        cls,
        thread_id: UUID,
        entry_type: LedgerEntryType,
        payload: Dict[str, Any],
        work_item_id: Optional[UUID] = None,
        payload_hash: Optional[str] = None,
    ) -> "LLMLedgerEntry":
        """Create a new ledger entry."""
        return cls(
            id=uuid4(),
            thread_id=thread_id,
            work_item_id=work_item_id,
            entry_type=entry_type,
            payload=payload,
            payload_hash=payload_hash,
        )
