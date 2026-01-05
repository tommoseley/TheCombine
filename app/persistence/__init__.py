"""Persistence module for The Combine."""

from app.persistence.models import (
    StoredDocument,
    StoredExecutionState,
    DocumentStatus,
    ExecutionStatus,
)
from app.persistence.repositories import (
    DocumentRepository,
    ExecutionRepository,
    InMemoryDocumentRepository,
    InMemoryExecutionRepository,
    DocumentNotFoundError,
    ExecutionNotFoundError,
)

__all__ = [
    # Models
    "StoredDocument",
    "StoredExecutionState",
    "DocumentStatus",
    "ExecutionStatus",
    # Protocols
    "DocumentRepository",
    "ExecutionRepository",
    # In-memory implementations
    "InMemoryDocumentRepository",
    "InMemoryExecutionRepository",
    # Exceptions
    "DocumentNotFoundError",
    "ExecutionNotFoundError",
]
