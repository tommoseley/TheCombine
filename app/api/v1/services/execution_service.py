"""Execution service - business logic for workflow execution management."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.domain.workflow import (
    Workflow,
    WorkflowExecutor,
    WorkflowState,
    WorkflowStatus,
    WorkflowContext,
    StatePersistence,
    StepExecutor,
    AcceptanceDecision,
)


class ExecutionNotFoundError(Exception):
    """Raised when execution is not found."""
    pass


class InvalidExecutionStateError(Exception):
    """Raised when operation is invalid for current execution state."""
    pass


class ExecutionInfo:
    """Lightweight execution info for listing."""
    
    def __init__(
        self,
        execution_id: str,
        workflow_id: str,
        project_id: str,
        status: WorkflowStatus,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
    ):
        self.execution_id = execution_id
        self.workflow_id = workflow_id
        self.project_id = project_id
        self.status = status
        self.started_at = started_at
        self.completed_at = completed_at


class ExecutionService:
    """Service for managing workflow executions."""
    
    def __init__(
        self,
        persistence: StatePersistence,
        step_executor: Optional[StepExecutor] = None,
    ):
        self._persistence = persistence
        self._step_executor = step_executor
        self._active_executions: Dict[str, tuple[WorkflowState, WorkflowContext]] = {}
    
    def _generate_execution_id(self) -> str:
        """Generate unique execution ID."""
        return f"exec_{uuid.uuid4().hex[:12]}"

    async def start_execution(
        self,
        workflow: Workflow,
        project_id: str,
        initial_context: Optional[Dict[str, Any]] = None,
    ) -> tuple[str, WorkflowState]:
        """Start a new workflow execution."""
        execution_id = self._generate_execution_id()
        
        state = WorkflowState(
            workflow_id=workflow.workflow_id,
            project_id=project_id,
        )
        state.start()
        
        context = WorkflowContext(workflow, project_id)
        
        if initial_context:
            for doc_type, content in initial_context.items():
                if isinstance(content, dict):
                    context.store_document(doc_type, content)
        
        self._active_executions[execution_id] = (state, context)
        await self._persistence.save(state, context)
        
        return execution_id, state
    
    async def get_execution(
        self,
        execution_id: str,
        workflow: Optional[Workflow] = None,
    ) -> tuple[WorkflowState, Optional[WorkflowContext]]:
        """Get execution state by ID."""
        if execution_id in self._active_executions:
            return self._active_executions[execution_id]
        raise ExecutionNotFoundError(f"Execution not found: {execution_id}")
    
    async def list_executions(
        self,
        workflow_id: Optional[str] = None,
        project_id: Optional[str] = None,
        status: Optional[WorkflowStatus] = None,
    ) -> List[ExecutionInfo]:
        """List executions with optional filters."""
        results = []
        
        for exec_id, (state, context) in self._active_executions.items():
            if workflow_id and state.workflow_id != workflow_id:
                continue
            if project_id and state.project_id != project_id:
                continue
            if status and state.status != status:
                continue
            
            results.append(ExecutionInfo(
                execution_id=exec_id,
                workflow_id=state.workflow_id,
                project_id=state.project_id,
                status=state.status,
                started_at=getattr(state, 'started_at', None),
                completed_at=getattr(state, 'completed_at', None),
            ))
        
        return results

    async def cancel_execution(self, execution_id: str) -> WorkflowState:
        """Cancel a running execution."""
        if execution_id not in self._active_executions:
            raise ExecutionNotFoundError(f"Execution not found: {execution_id}")
        
        state, context = self._active_executions[execution_id]
        
        if state.status in (WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED):
            raise InvalidExecutionStateError(
                f"Cannot cancel execution in state: {state.status.value}"
            )
        
        state.cancel()
        state.completed_at = datetime.now(timezone.utc)
        await self._persistence.save(state, context)
        return state
    
    async def get_execution_state(self, execution_id: str) -> WorkflowState:
        """Get just the execution state (no context)."""
        if execution_id not in self._active_executions:
            raise ExecutionNotFoundError(f"Execution not found: {execution_id}")
        state, _ = self._active_executions[execution_id]
        return state
    
    async def submit_acceptance(
        self,
        execution_id: str,
        accepted: bool,
        comment: Optional[str] = None,
        decided_by: str = "user",
    ) -> WorkflowState:
        """Submit acceptance decision for pending document."""
        if execution_id not in self._active_executions:
            raise ExecutionNotFoundError(f"Execution not found: {execution_id}")
        
        state, context = self._active_executions[execution_id]
        
        if state.status != WorkflowStatus.WAITING_ACCEPTANCE:
            raise InvalidExecutionStateError(
                f"Execution not waiting for acceptance. Current state: {state.status.value}"
            )
        
        if not state.pending_acceptance:
            raise InvalidExecutionStateError("No pending acceptance found")
        
        decision = AcceptanceDecision(
            doc_type=state.pending_acceptance,
            scope_id=state.pending_acceptance_scope_id,
            accepted=accepted,
            comment=comment,
            decided_by=decided_by,
        )
        
        decision_key = f"{state.pending_acceptance}:{state.pending_acceptance_scope_id or 'default'}"
        state.acceptance_decisions[decision_key] = decision
        
        if accepted:
            state.status = WorkflowStatus.RUNNING
            state.pending_acceptance = None
            state.pending_acceptance_scope_id = None
        else:
            state.fail(f"Document rejected: {comment or 'No reason provided'}")
        
        await self._persistence.save(state, context)
        return state

    async def submit_clarification(
        self,
        execution_id: str,
        answers: Dict[str, str],
    ) -> WorkflowState:
        """Submit clarification answers."""
        if execution_id not in self._active_executions:
            raise ExecutionNotFoundError(f"Execution not found: {execution_id}")
        
        state, context = self._active_executions[execution_id]
        
        if state.status != WorkflowStatus.WAITING_CLARIFICATION:
            raise InvalidExecutionStateError(
                f"Execution not waiting for clarification. Current state: {state.status.value}"
            )
        
        context.store_entity("clarification_answers", execution_id, answers)
        
        state.status = WorkflowStatus.RUNNING
        state.pending_clarification_step_id = None
        
        await self._persistence.save(state, context)
        return state
    
    async def resume_execution(self, execution_id: str) -> WorkflowState:
        """Resume a paused execution."""
        if execution_id not in self._active_executions:
            raise ExecutionNotFoundError(f"Execution not found: {execution_id}")
        
        state, context = self._active_executions[execution_id]
        
        resumable = (
            state.status == WorkflowStatus.RUNNING or
            (state.status == WorkflowStatus.WAITING_ACCEPTANCE and not state.pending_acceptance) or
            (state.status == WorkflowStatus.WAITING_CLARIFICATION and not state.pending_clarification_step_id)
        )
        
        if not resumable:
            raise InvalidExecutionStateError(
                f"Execution cannot be resumed. Current state: {state.status.value}"
            )
        
        state.status = WorkflowStatus.RUNNING
        await self._persistence.save(state, context)
        return state
    
    def set_waiting_acceptance(
        self,
        execution_id: str,
        doc_type: str,
        scope_id: Optional[str] = None,
    ) -> None:
        """Set execution to waiting for acceptance (for testing)."""
        if execution_id not in self._active_executions:
            raise ExecutionNotFoundError(f"Execution not found: {execution_id}")
        
        state, _ = self._active_executions[execution_id]
        state.status = WorkflowStatus.WAITING_ACCEPTANCE
        state.pending_acceptance = doc_type
        state.pending_acceptance_scope_id = scope_id
    
    def set_waiting_clarification(
        self,
        execution_id: str,
        step_id: str,
    ) -> None:
        """Set execution to waiting for clarification (for testing)."""
        if execution_id not in self._active_executions:
            raise ExecutionNotFoundError(f"Execution not found: {execution_id}")
        
        state, _ = self._active_executions[execution_id]
        state.status = WorkflowStatus.WAITING_CLARIFICATION
        state.pending_clarification_step_id = step_id
