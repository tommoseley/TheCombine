"""Repository protocols and in-memory implementations."""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, List, Optional, Protocol, runtime_checkable
from uuid import UUID

from app.persistence.models import (
    StoredDocument,
    StoredExecutionState,
    DocumentStatus,
    ExecutionStatus,
)


class DocumentNotFoundError(Exception):
    """Document not found in repository."""
    pass


class ExecutionNotFoundError(Exception):
    """Execution not found in repository."""
    pass


@runtime_checkable
class DocumentRepository(Protocol):
    """Protocol for document storage."""
    
    async def save(self, document: StoredDocument) -> StoredDocument:
        """Save a document (create or update)."""
        ...
    
    async def get(self, document_id: UUID) -> Optional[StoredDocument]:
        """Get document by ID."""
        ...
    
    async def get_by_scope_type(
        self,
        scope_type: str,
        scope_id: str,
        document_type: str,
        version: Optional[int] = None,
    ) -> Optional[StoredDocument]:
        """Get document by scope and type. None version = latest."""
        ...
    
    async def list_by_scope(
        self,
        scope_type: str,
        scope_id: str,
        document_type: Optional[str] = None,
    ) -> List[StoredDocument]:
        """List documents in a scope, optionally filtered by type."""
        ...
    
    async def delete(self, document_id: UUID) -> bool:
        """Delete a document. Returns True if deleted."""
        ...


@runtime_checkable
class ExecutionRepository(Protocol):
    """Protocol for execution state storage."""
    
    async def save(self, state: StoredExecutionState) -> StoredExecutionState:
        """Save execution state."""
        ...
    
    async def get(self, execution_id: UUID) -> Optional[StoredExecutionState]:
        """Get execution by ID."""
        ...
    
    async def list_by_scope(
        self,
        scope_type: str,
        scope_id: str,
        status: Optional[ExecutionStatus] = None,
    ) -> List[StoredExecutionState]:
        """List executions in a scope."""
        ...
    
    async def list_active(self) -> List[StoredExecutionState]:
        """List all active (running/waiting) executions."""
        ...
    
    async def delete(self, execution_id: UUID) -> bool:
        """Delete an execution. Returns True if deleted."""
        ...


class InMemoryDocumentRepository:
    """In-memory document repository for testing."""
    
    def __init__(self):
        self._documents: Dict[UUID, StoredDocument] = {}
        self._by_scope: Dict[str, Dict[str, List[UUID]]] = {}  # scope_key -> doc_type -> [ids]
    
    def _scope_key(self, scope_type: str, scope_id: str) -> str:
        return f"{scope_type}:{scope_id}"
    
    async def save(self, document: StoredDocument) -> StoredDocument:
        """Save a document."""
        document.updated_at = datetime.now(timezone.utc)
        
        # Handle versioning - mark old versions as not latest
        if document.is_latest:
            scope_key = self._scope_key(document.scope_type, document.scope_id)
            if scope_key in self._by_scope:
                type_docs = self._by_scope[scope_key].get(document.document_type, [])
                for doc_id in type_docs:
                    if doc_id != document.document_id:
                        existing = self._documents.get(doc_id)
                        if existing and existing.is_latest:
                            existing.is_latest = False
        
        self._documents[document.document_id] = document
        
        # Update index
        scope_key = self._scope_key(document.scope_type, document.scope_id)
        if scope_key not in self._by_scope:
            self._by_scope[scope_key] = {}
        if document.document_type not in self._by_scope[scope_key]:
            self._by_scope[scope_key][document.document_type] = []
        if document.document_id not in self._by_scope[scope_key][document.document_type]:
            self._by_scope[scope_key][document.document_type].append(document.document_id)
        
        return document
    
    async def get(self, document_id: UUID) -> Optional[StoredDocument]:
        """Get document by ID."""
        return self._documents.get(document_id)
    
    async def get_by_scope_type(
        self,
        scope_type: str,
        scope_id: str,
        document_type: str,
        version: Optional[int] = None,
    ) -> Optional[StoredDocument]:
        """Get document by scope and type."""
        scope_key = self._scope_key(scope_type, scope_id)
        
        if scope_key not in self._by_scope:
            return None
        if document_type not in self._by_scope[scope_key]:
            return None
        
        doc_ids = self._by_scope[scope_key][document_type]
        
        for doc_id in doc_ids:
            doc = self._documents.get(doc_id)
            if doc:
                if version is not None:
                    if doc.version == version:
                        return doc
                elif doc.is_latest:
                    return doc
        
        return None
    
    async def list_by_scope(
        self,
        scope_type: str,
        scope_id: str,
        document_type: Optional[str] = None,
    ) -> List[StoredDocument]:
        """List documents in a scope."""
        scope_key = self._scope_key(scope_type, scope_id)
        
        if scope_key not in self._by_scope:
            return []
        
        results = []
        scope_docs = self._by_scope[scope_key]
        
        if document_type:
            doc_ids = scope_docs.get(document_type, [])
            for doc_id in doc_ids:
                doc = self._documents.get(doc_id)
                if doc:
                    results.append(doc)
        else:
            for type_docs in scope_docs.values():
                for doc_id in type_docs:
                    doc = self._documents.get(doc_id)
                    if doc:
                        results.append(doc)
        
        return results
    
    async def delete(self, document_id: UUID) -> bool:
        """Delete a document."""
        if document_id not in self._documents:
            return False
        
        doc = self._documents.pop(document_id)
        
        # Remove from index
        scope_key = self._scope_key(doc.scope_type, doc.scope_id)
        if scope_key in self._by_scope:
            if doc.document_type in self._by_scope[scope_key]:
                try:
                    self._by_scope[scope_key][doc.document_type].remove(document_id)
                except ValueError:
                    pass
        
        return True
    
    def clear(self) -> None:
        """Clear all documents (for testing)."""
        self._documents.clear()
        self._by_scope.clear()


class InMemoryExecutionRepository:
    """In-memory execution repository for testing."""
    
    def __init__(self):
        self._executions: Dict[UUID, StoredExecutionState] = {}
        self._by_scope: Dict[str, List[UUID]] = {}
    
    def _scope_key(self, scope_type: str, scope_id: str) -> str:
        return f"{scope_type}:{scope_id}"
    
    async def save(self, state: StoredExecutionState) -> StoredExecutionState:
        """Save execution state."""
        self._executions[state.execution_id] = state
        
        # Update index
        scope_key = self._scope_key(state.scope_type, state.scope_id)
        if scope_key not in self._by_scope:
            self._by_scope[scope_key] = []
        if state.execution_id not in self._by_scope[scope_key]:
            self._by_scope[scope_key].append(state.execution_id)
        
        return state
    
    async def get(self, execution_id: UUID) -> Optional[StoredExecutionState]:
        """Get execution by ID."""
        return self._executions.get(execution_id)
    
    async def list_by_scope(
        self,
        scope_type: str,
        scope_id: str,
        status: Optional[ExecutionStatus] = None,
    ) -> List[StoredExecutionState]:
        """List executions in a scope."""
        scope_key = self._scope_key(scope_type, scope_id)
        
        if scope_key not in self._by_scope:
            return []
        
        results = []
        for exec_id in self._by_scope[scope_key]:
            execution = self._executions.get(exec_id)
            if execution:
                if status is None or execution.status == status:
                    results.append(execution)
        
        return results
    
    async def list_active(self) -> List[StoredExecutionState]:
        """List all active executions."""
        active_statuses = {ExecutionStatus.RUNNING, ExecutionStatus.WAITING_INPUT}
        return [
            e for e in self._executions.values()
            if e.status in active_statuses
        ]
    
    async def delete(self, execution_id: UUID) -> bool:
        """Delete an execution."""
        if execution_id not in self._executions:
            return False
        
        execution = self._executions.pop(execution_id)
        
        scope_key = self._scope_key(execution.scope_type, execution.scope_id)
        if scope_key in self._by_scope:
            try:
                self._by_scope[scope_key].remove(execution_id)
            except ValueError:
                pass
        
        return True
    
    def clear(self) -> None:
        """Clear all executions (for testing)."""
        self._executions.clear()
        self._by_scope.clear()
