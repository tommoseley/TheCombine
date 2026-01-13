"""Persistence module for The Combine."""

from app.persistence.models import (
    StoredDocument,
    StoredExecutionState,
    DocumentStatus,
    ExecutionStatus,
    # ADR-035: LLM Thread Queue
    LLMThread,
    LLMWorkItem,
    LLMLedgerEntry,
    ThreadStatus,
    WorkItemStatus,
    LedgerEntryType,
    ErrorCode,
)
from app.persistence.repositories import (
    DocumentRepository,
    ExecutionRepository,
    InMemoryDocumentRepository,
    InMemoryExecutionRepository,
    DocumentNotFoundError,
    ExecutionNotFoundError,
)
from app.persistence.llm_thread_repositories import (
    ThreadRepository,
    WorkItemRepository,
    LedgerRepository,
)

__all__ = [
    # Models
    "StoredDocument",
    "StoredExecutionState",
    "DocumentStatus",
    "ExecutionStatus",
    # ADR-035: LLM Thread Queue Models
    "LLMThread",
    "LLMWorkItem",
    "LLMLedgerEntry",
    "ThreadStatus",
    "WorkItemStatus",
    "LedgerEntryType",
    "ErrorCode",
    # Protocols
    "DocumentRepository",
    "ExecutionRepository",
    # In-memory implementations
    "InMemoryDocumentRepository",
    "InMemoryExecutionRepository",
    # Exceptions
    "DocumentNotFoundError",
    "ExecutionNotFoundError",
    # ADR-035: LLM Thread Queue Repositories
    "ThreadRepository",
    "WorkItemRepository",
    "LedgerRepository",
]
