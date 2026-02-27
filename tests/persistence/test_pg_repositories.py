"""Tests for PostgreSQL repository implementations."""

from uuid import uuid4
from datetime import datetime, timezone

from app.persistence.models import (
    StoredDocument,
    StoredExecutionState,
    DocumentStatus,
    ExecutionStatus,
)
from app.persistence.pg_repositories import (
    _stored_to_orm_document,
    _orm_to_stored_execution,
    _stored_to_orm_execution,
    PostgresDocumentRepository,
    PostgresExecutionRepository,
    create_repositories,
)


class TestDocumentConversion:
    """Tests for ORM <-> domain model conversion."""
    
    def test_stored_to_orm_document(self):
        """Convert StoredDocument to ORM Document."""
        stored = StoredDocument(
            document_id=uuid4(),
            document_type="strategy",
            scope_type="project",
            scope_id=str(uuid4()),
            version=1,
            title="Test Document",
            content={"key": "value"},
            status=DocumentStatus.DRAFT,
        )
        
        orm_doc = _stored_to_orm_document(stored)
        
        assert orm_doc.id == stored.document_id
        assert orm_doc.doc_type_id == "strategy"
        assert orm_doc.title == "Test Document"
        assert orm_doc.content == {"key": "value"}
    
    def test_stored_to_orm_preserves_metadata(self):
        """Metadata is preserved in conversion."""
        stored = StoredDocument(
            document_id=uuid4(),
            document_type="test",
            scope_type="project",
            scope_id=str(uuid4()),
            version=1,
            title="Test",
            content={},
            created_by_step="discovery",
            execution_id=uuid4(),
        )
        
        orm_doc = _stored_to_orm_document(stored)
        
        assert orm_doc.builder_metadata["step_id"] == "discovery"
        assert "execution_id" in orm_doc.builder_metadata


class TestExecutionConversion:
    """Tests for execution state ORM conversion."""
    
    def test_stored_to_orm_execution(self):
        """Convert StoredExecutionState to ORM."""
        stored = StoredExecutionState(
            execution_id=uuid4(),
            workflow_id="test-workflow",
            scope_type="project",
            scope_id="proj-123",
            status=ExecutionStatus.RUNNING,
            current_step="discovery",
        )
        
        orm_exec = _stored_to_orm_execution(stored)
        
        assert orm_exec.id == stored.execution_id
        assert orm_exec.workflow_id == "test-workflow"
        assert orm_exec.status == "running"
        assert orm_exec.current_step == "discovery"
    
    def test_orm_to_stored_execution(self):
        """Convert ORM to StoredExecutionState."""
        from app.persistence.pg_repositories import ExecutionStateORM
        
        orm_exec = ExecutionStateORM()
        orm_exec.id = uuid4()
        orm_exec.workflow_id = "test-workflow"
        orm_exec.scope_type = "project"
        orm_exec.scope_id = "proj-1"
        orm_exec.status = "completed"
        orm_exec.current_step = None
        orm_exec.step_states = {"step1": "done"}
        orm_exec.context_data = {}
        orm_exec.started_at = datetime.now(timezone.utc)
        orm_exec.completed_at = datetime.now(timezone.utc)
        orm_exec.error_message = None
        orm_exec.created_by = "user-1"
        
        stored = _orm_to_stored_execution(orm_exec)
        
        assert stored.execution_id == orm_exec.id
        assert stored.workflow_id == "test-workflow"
        assert stored.status == ExecutionStatus.COMPLETED
        assert stored.step_states == {"step1": "done"}


class TestCreateRepositories:
    """Tests for repository factory."""
    
    def test_create_in_memory_repositories(self):
        """Creates in-memory repositories when use_postgres=False."""
        doc_repo, exec_repo = create_repositories(
            session_factory=None,
            use_postgres=False,
        )
        
        from app.persistence.repositories import (
            InMemoryDocumentRepository,
            InMemoryExecutionRepository,
        )
        
        assert isinstance(doc_repo, InMemoryDocumentRepository)
        assert isinstance(exec_repo, InMemoryExecutionRepository)
    
    def test_create_postgres_repositories(self):
        """Creates PostgreSQL repositories when use_postgres=True."""
        def mock_session_factory():
            pass
        
        doc_repo, exec_repo = create_repositories(
            session_factory=mock_session_factory,
            use_postgres=True,
        )
        
        assert isinstance(doc_repo, PostgresDocumentRepository)
        assert isinstance(exec_repo, PostgresExecutionRepository)


class TestPostgresDocumentRepository:
    """Tests for PostgresDocumentRepository structure."""
    
    def test_repository_has_required_methods(self):
        """Repository implements protocol methods."""
        def mock_factory():
            pass
        
        repo = PostgresDocumentRepository(mock_factory)
        
        assert hasattr(repo, 'save')
        assert hasattr(repo, 'get')
        assert hasattr(repo, 'get_by_scope_type')
        assert hasattr(repo, 'list_by_scope')
        assert hasattr(repo, 'delete')


class TestPostgresExecutionRepository:
    """Tests for PostgresExecutionRepository structure."""
    
    def test_repository_has_required_methods(self):
        """Repository implements protocol methods."""
        def mock_factory():
            pass
        
        repo = PostgresExecutionRepository(mock_factory)
        
        assert hasattr(repo, 'save')
        assert hasattr(repo, 'get')
        assert hasattr(repo, 'list_by_scope')
        assert hasattr(repo, 'list_active')
        assert hasattr(repo, 'delete')
