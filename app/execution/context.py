"""Execution context for workflow runs."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.persistence.models import StoredDocument, StoredExecutionState, ExecutionStatus
from app.persistence.repositories import DocumentRepository, ExecutionRepository


@dataclass
class StepProgress:
    """Progress tracking for a step."""
    step_id: str
    status: str  # pending, running, completed, failed, waiting_input
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    attempt: int = 1
    error_message: Optional[str] = None
    output_document_id: Optional[UUID] = None


@dataclass
class ExecutionContext:
    """
    Context for a workflow execution.
    
    Manages state, documents, and progress for a single execution run.
    """
    execution_id: UUID
    workflow_id: str
    scope_type: str
    scope_id: str
    document_repo: DocumentRepository
    execution_repo: ExecutionRepository
    created_by: Optional[str] = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    current_step: Optional[str] = None
    step_progress: Dict[str, StepProgress] = field(default_factory=dict)
    context_data: Dict[str, Any] = field(default_factory=dict)
    _state: Optional[StoredExecutionState] = field(default=None, repr=False)
    
    @classmethod
    async def create(
        cls,
        workflow_id: str,
        scope_type: str,
        scope_id: str,
        document_repo: DocumentRepository,
        execution_repo: ExecutionRepository,
        created_by: Optional[str] = None,
    ) -> "ExecutionContext":
        """Create a new execution context and persist initial state."""
        state = StoredExecutionState.create(
            workflow_id=workflow_id,
            scope_type=scope_type,
            scope_id=scope_id,
            created_by=created_by,
        )
        await execution_repo.save(state)
        
        return cls(
            execution_id=state.execution_id,
            workflow_id=workflow_id,
            scope_type=scope_type,
            scope_id=scope_id,
            document_repo=document_repo,
            execution_repo=execution_repo,
            created_by=created_by,
            _state=state,
        )
    
    @classmethod
    async def load(
        cls,
        execution_id: UUID,
        document_repo: DocumentRepository,
        execution_repo: ExecutionRepository,
    ) -> Optional["ExecutionContext"]:
        """Load an existing execution context."""
        state = await execution_repo.get(execution_id)
        if not state:
            return None
        
        ctx = cls(
            execution_id=state.execution_id,
            workflow_id=state.workflow_id,
            scope_type=state.scope_type,
            scope_id=state.scope_id,
            document_repo=document_repo,
            execution_repo=execution_repo,
            created_by=state.created_by,
            started_at=state.started_at,
            current_step=state.current_step,
            context_data=state.context_data,
            _state=state,
        )
        
        # Restore step progress from state
        for step_id, step_data in state.step_states.items():
            ctx.step_progress[step_id] = StepProgress(
                step_id=step_id,
                status=step_data.get("status", "pending"),
                attempt=step_data.get("attempt", 1),
            )
        
        return ctx
    
    async def get_input_document(
        self, 
        document_type: str,
        version: Optional[int] = None,
    ) -> Optional[StoredDocument]:
        """Retrieve an input document from the repository."""
        return await self.document_repo.get_by_scope_type(
            scope_type=self.scope_type,
            scope_id=self.scope_id,
            document_type=document_type,
            version=version,
        )
    
    async def get_input_documents(
        self,
        document_types: List[str],
    ) -> Dict[str, Optional[StoredDocument]]:
        """Retrieve multiple input documents."""
        result = {}
        for doc_type in document_types:
            result[doc_type] = await self.get_input_document(doc_type)
        return result
    
    async def save_output_document(
        self,
        document_type: str,
        title: str,
        content: Dict[str, Any],
        step_id: str,
        summary: Optional[str] = None,
    ) -> StoredDocument:
        """Save a step's output document."""
        doc = StoredDocument.create(
            document_type=document_type,
            scope_type=self.scope_type,
            scope_id=self.scope_id,
            title=title,
            content=content,
            summary=summary,
            created_by=self.created_by,
            created_by_step=step_id,
            execution_id=self.execution_id,
        )
        await self.document_repo.save(doc)
        
        # Update step progress
        if step_id in self.step_progress:
            self.step_progress[step_id].output_document_id = doc.document_id
        
        return doc
    
    def start_step(self, step_id: str) -> None:
        """Mark a step as started."""
        self.current_step = step_id
        self.step_progress[step_id] = StepProgress(
            step_id=step_id,
            status="running",
            started_at=datetime.now(timezone.utc),
        )
    
    def complete_step(self, step_id: str) -> None:
        """Mark a step as completed."""
        if step_id in self.step_progress:
            self.step_progress[step_id].status = "completed"
            self.step_progress[step_id].completed_at = datetime.now(timezone.utc)
    
    def fail_step(self, step_id: str, error: str) -> None:
        """Mark a step as failed."""
        if step_id in self.step_progress:
            self.step_progress[step_id].status = "failed"
            self.step_progress[step_id].error_message = error
            self.step_progress[step_id].completed_at = datetime.now(timezone.utc)
    
    def wait_for_input(self, step_id: str) -> None:
        """Mark a step as waiting for input."""
        if step_id in self.step_progress:
            self.step_progress[step_id].status = "waiting_input"
    
    async def save_state(self) -> None:
        """Persist current execution state."""
        if self._state is None:
            self._state = StoredExecutionState.create(
                workflow_id=self.workflow_id,
                scope_type=self.scope_type,
                scope_id=self.scope_id,
                created_by=self.created_by,
            )
            self._state.execution_id = self.execution_id
        
        self._state.current_step = self.current_step
        self._state.context_data = self.context_data
        
        # Serialize step progress
        self._state.step_states = {
            step_id: {
                "status": progress.status,
                "attempt": progress.attempt,
                "started_at": progress.started_at.isoformat() if progress.started_at else None,
                "completed_at": progress.completed_at.isoformat() if progress.completed_at else None,
                "error_message": progress.error_message,
            }
            for step_id, progress in self.step_progress.items()
        }
        
        # Determine overall status
        statuses = {p.status for p in self.step_progress.values()}
        if "failed" in statuses:
            self._state.status = ExecutionStatus.FAILED
        elif "waiting_input" in statuses:
            self._state.status = ExecutionStatus.WAITING_INPUT
        elif "running" in statuses:
            self._state.status = ExecutionStatus.RUNNING
        elif all(p.status == "completed" for p in self.step_progress.values()):
            self._state.status = ExecutionStatus.COMPLETED
            self._state.completed_at = datetime.now(timezone.utc)
        
        await self.execution_repo.save(self._state)
    
    @property
    def status(self) -> ExecutionStatus:
        """Get current execution status."""
        if self._state:
            return self._state.status
        return ExecutionStatus.PENDING
