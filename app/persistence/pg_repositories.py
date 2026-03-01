"""PostgreSQL repository implementations."""

from datetime import datetime, timezone
from typing import Callable, List, Optional
from uuid import UUID

from sqlalchemy import select, and_, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.models import (
    StoredDocument,
    StoredExecutionState,
    DocumentStatus,
    ExecutionStatus,
)
from app.api.models.document import Document


def _orm_to_stored_document(orm_doc: Document) -> StoredDocument:
    """Convert ORM Document to StoredDocument domain model."""
    return StoredDocument(
        document_id=orm_doc.id,
        document_type=orm_doc.doc_type_id,
        scope_type=orm_doc.space_type,
        scope_id=str(orm_doc.space_id),
        version=orm_doc.version,
        title=orm_doc.title,
        content=orm_doc.content,
        status=DocumentStatus(orm_doc.status),
        summary=orm_doc.summary,
        created_at=orm_doc.created_at,
        updated_at=orm_doc.updated_at,
        created_by=orm_doc.created_by,
        created_by_step=orm_doc.builder_metadata.get("step_id") if orm_doc.builder_metadata else None,
        execution_id=orm_doc.builder_metadata.get("execution_id") if orm_doc.builder_metadata else None,
        metadata=orm_doc.builder_metadata or {},
        is_latest=orm_doc.is_latest,
    )


def _stored_to_orm_document(stored: StoredDocument, orm_doc: Optional[Document] = None) -> Document:
    """Convert StoredDocument to ORM Document."""
    if orm_doc is None:
        orm_doc = Document()
    
    orm_doc.id = stored.document_id
    orm_doc.doc_type_id = stored.document_type
    orm_doc.space_type = stored.scope_type
    orm_doc.space_id = UUID(stored.scope_id) if isinstance(stored.scope_id, str) else stored.scope_id
    orm_doc.version = stored.version
    orm_doc.title = stored.title
    orm_doc.content = stored.content
    orm_doc.status = stored.status.value
    orm_doc.summary = stored.summary
    orm_doc.created_by = stored.created_by
    orm_doc.is_latest = stored.is_latest
    
    # Build metadata
    metadata = dict(stored.metadata) if stored.metadata else {}
    if stored.created_by_step:
        metadata["step_id"] = stored.created_by_step
    if stored.execution_id:
        metadata["execution_id"] = str(stored.execution_id)
    orm_doc.builder_metadata = metadata if metadata else None
    
    return orm_doc


class PostgresDocumentRepository:
    """PostgreSQL implementation of DocumentRepository."""
    
    def __init__(self, session_factory: Callable[[], AsyncSession]):
        """
        Initialize repository.
        
        Args:
            session_factory: Callable that returns an AsyncSession
        """
        self._session_factory = session_factory
    
    async def save(self, document: StoredDocument) -> StoredDocument:
        """Save a document (create or update)."""
        async with self._session_factory() as session:
            # Check if document exists
            existing = await session.get(Document, document.document_id)
            
            if existing:
                # Update existing
                orm_doc = _stored_to_orm_document(document, existing)
                orm_doc.updated_at = datetime.now(timezone.utc)
            else:
                # Create new
                orm_doc = _stored_to_orm_document(document)
                session.add(orm_doc)
            
            # Handle is_latest - unset other versions if this is latest
            if document.is_latest:
                await session.execute(
                    update(Document)
                    .where(
                        and_(
                            Document.space_type == document.scope_type,
                            Document.space_id == UUID(document.scope_id),
                            Document.doc_type_id == document.document_type,
                            Document.id != document.document_id,
                            Document.is_latest == True,
                        )
                    )
                    .values(is_latest=False)
                )
            
            await session.commit()
            await session.refresh(orm_doc)
            
            return _orm_to_stored_document(orm_doc)
    
    async def get(self, document_id: UUID) -> Optional[StoredDocument]:
        """Get document by ID."""
        async with self._session_factory() as session:
            orm_doc = await session.get(Document, document_id)
            if orm_doc is None:
                return None
            return _orm_to_stored_document(orm_doc)
    
    async def get_by_scope_type(
        self,
        scope_type: str,
        scope_id: str,
        document_type: str,
        version: Optional[int] = None,
    ) -> Optional[StoredDocument]:
        """Get document by scope and type. None version = latest."""
        async with self._session_factory() as session:
            query = select(Document).where(
                and_(
                    Document.space_type == scope_type,
                    Document.space_id == UUID(scope_id),
                    Document.doc_type_id == document_type,
                )
            )
            
            if version is not None:
                query = query.where(Document.version == version)
            else:
                query = query.where(Document.is_latest == True)
            
            result = await session.execute(query)
            orm_doc = result.scalar_one_or_none()
            
            if orm_doc is None:
                return None
            return _orm_to_stored_document(orm_doc)
    
    async def list_by_scope(
        self,
        scope_type: str,
        scope_id: str,
        document_type: Optional[str] = None,
    ) -> List[StoredDocument]:
        """List documents in a scope, optionally filtered by type."""
        async with self._session_factory() as session:
            query = select(Document).where(
                and_(
                    Document.space_type == scope_type,
                    Document.space_id == UUID(scope_id),
                )
            )
            
            if document_type:
                query = query.where(Document.doc_type_id == document_type)
            
            result = await session.execute(query)
            orm_docs = result.scalars().all()
            
            return [_orm_to_stored_document(d) for d in orm_docs]
    
    async def delete(self, document_id: UUID) -> bool:
        """Delete a document."""
        async with self._session_factory() as session:
            result = await session.execute(
                delete(Document).where(Document.id == document_id)
            )
            await session.commit()
            return result.rowcount > 0


# ============================================================================
# Execution ORM Model (inline - will be moved to models later if needed)
# ============================================================================

from sqlalchemy import Column, String, Text, DateTime  # noqa: E402
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB  # noqa: E402
from sqlalchemy.sql import func  # noqa: E402

try:
    from app.core.database import Base
except ImportError:
    # Fallback for testing without full app context
    from sqlalchemy.orm import declarative_base
    Base = declarative_base()


class ExecutionStateORM(Base):
    """ORM model for workflow execution state."""
    
    __tablename__ = "execution_states"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    workflow_id = Column(String(100), nullable=False, index=True)
    scope_type = Column(String(50), nullable=False, index=True)
    scope_id = Column(String(100), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="pending", index=True)
    current_step = Column(String(100), nullable=True)
    step_states = Column(JSONB, nullable=False, default=dict)
    context_data = Column(JSONB, nullable=False, default=dict)
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    created_by = Column(String(200), nullable=True)


def _orm_to_stored_execution(orm_exec: ExecutionStateORM) -> StoredExecutionState:
    """Convert ORM to domain model."""
    return StoredExecutionState(
        execution_id=orm_exec.id,
        workflow_id=orm_exec.workflow_id,
        scope_type=orm_exec.scope_type,
        scope_id=orm_exec.scope_id,
        status=ExecutionStatus(orm_exec.status),
        current_step=orm_exec.current_step,
        step_states=orm_exec.step_states or {},
        context_data=orm_exec.context_data or {},
        started_at=orm_exec.started_at,
        completed_at=orm_exec.completed_at,
        error_message=orm_exec.error_message,
        created_by=orm_exec.created_by,
    )


def _stored_to_orm_execution(
    stored: StoredExecutionState,
    orm_exec: Optional[ExecutionStateORM] = None,
) -> ExecutionStateORM:
    """Convert domain model to ORM."""
    if orm_exec is None:
        orm_exec = ExecutionStateORM()
    
    orm_exec.id = stored.execution_id
    orm_exec.workflow_id = stored.workflow_id
    orm_exec.scope_type = stored.scope_type
    orm_exec.scope_id = stored.scope_id
    orm_exec.status = stored.status.value
    orm_exec.current_step = stored.current_step
    orm_exec.step_states = stored.step_states
    orm_exec.context_data = stored.context_data
    orm_exec.started_at = stored.started_at
    orm_exec.completed_at = stored.completed_at
    orm_exec.error_message = stored.error_message
    orm_exec.created_by = stored.created_by
    
    return orm_exec


class PostgresExecutionRepository:
    """PostgreSQL implementation of ExecutionRepository."""
    
    def __init__(self, session_factory: Callable[[], AsyncSession]):
        """
        Initialize repository.
        
        Args:
            session_factory: Callable that returns an AsyncSession
        """
        self._session_factory = session_factory
    
    async def save(self, state: StoredExecutionState) -> StoredExecutionState:
        """Save execution state."""
        async with self._session_factory() as session:
            existing = await session.get(ExecutionStateORM, state.execution_id)
            
            if existing:
                orm_exec = _stored_to_orm_execution(state, existing)
            else:
                orm_exec = _stored_to_orm_execution(state)
                session.add(orm_exec)
            
            await session.commit()
            await session.refresh(orm_exec)
            
            return _orm_to_stored_execution(orm_exec)
    
    async def get(self, execution_id: UUID) -> Optional[StoredExecutionState]:
        """Get execution by ID."""
        async with self._session_factory() as session:
            orm_exec = await session.get(ExecutionStateORM, execution_id)
            if orm_exec is None:
                return None
            return _orm_to_stored_execution(orm_exec)
    
    async def list_by_scope(
        self,
        scope_type: str,
        scope_id: str,
        status: Optional[ExecutionStatus] = None,
    ) -> List[StoredExecutionState]:
        """List executions in a scope."""
        async with self._session_factory() as session:
            query = select(ExecutionStateORM).where(
                and_(
                    ExecutionStateORM.scope_type == scope_type,
                    ExecutionStateORM.scope_id == scope_id,
                )
            )
            
            if status:
                query = query.where(ExecutionStateORM.status == status.value)
            
            result = await session.execute(query)
            orm_execs = result.scalars().all()
            
            return [_orm_to_stored_execution(e) for e in orm_execs]
    
    async def list_active(self) -> List[StoredExecutionState]:
        """List all active executions."""
        active_statuses = [ExecutionStatus.RUNNING.value, ExecutionStatus.WAITING_INPUT.value]
        
        async with self._session_factory() as session:
            query = select(ExecutionStateORM).where(
                ExecutionStateORM.status.in_(active_statuses)
            )
            
            result = await session.execute(query)
            orm_execs = result.scalars().all()
            
            return [_orm_to_stored_execution(e) for e in orm_execs]
    
    async def delete(self, execution_id: UUID) -> bool:
        """Delete an execution."""
        async with self._session_factory() as session:
            result = await session.execute(
                delete(ExecutionStateORM).where(ExecutionStateORM.id == execution_id)
            )
            await session.commit()
            return result.rowcount > 0


# ============================================================================
# Factory function
# ============================================================================

def create_repositories(
    session_factory: Callable[[], AsyncSession],
    use_postgres: bool = True,
):
    """
    Create repository instances.
    
    Args:
        session_factory: Session factory for PostgreSQL
        use_postgres: If True, use PostgreSQL; if False, use in-memory
        
    Returns:
        Tuple of (DocumentRepository, ExecutionRepository)
    """
    if use_postgres:
        return (
            PostgresDocumentRepository(session_factory),
            PostgresExecutionRepository(session_factory),
        )
    
    from app.persistence.repositories import (
        InMemoryDocumentRepository,
        InMemoryExecutionRepository,
    )
    return (
        InMemoryDocumentRepository(),
        InMemoryExecutionRepository(),
    )
