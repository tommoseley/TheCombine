"""LLM Execution Service - bridges API to LLMStepExecutor."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, AsyncGenerator
from uuid import UUID

from app.execution import (
    ExecutionContext,
    LLMStepExecutor,
    StepInput,
    StepOutput,
    WorkflowDefinition,
    WorkflowLoader,
)
from app.persistence import (
    DocumentRepository,
    ExecutionRepository,
    ExecutionStatus,
)
from app.llm import TelemetryService


class LLMExecutionNotFoundError(Exception):
    """Raised when execution is not found."""
    pass


class LLMInvalidStateError(Exception):
    """Raised when operation is invalid for current state."""
    pass


class WorkflowNotFoundError(Exception):
    """Raised when workflow is not found."""
    pass


@dataclass
class ProgressEvent:
    """Event published during execution progress."""
    event_type: str
    execution_id: UUID
    step_id: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ExecutionInfo:
    """Execution information for API responses."""
    execution_id: UUID
    workflow_id: str
    scope_type: str
    scope_id: str
    status: str
    current_step_id: Optional[str]
    completed_steps: List[str]
    step_statuses: Dict[str, str]
    needs_clarification: bool
    clarification_questions: Optional[List[str]]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error: Optional[str]
    total_cost_usd: Decimal


class ProgressPublisher:
    """Publishes execution progress for SSE consumers."""
    
    def __init__(self):
        self._subscribers: Dict[UUID, List[asyncio.Queue]] = {}
    
    def subscribe(self, execution_id: UUID) -> asyncio.Queue:
        """Subscribe to execution progress events."""
        if execution_id not in self._subscribers:
            self._subscribers[execution_id] = []
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers[execution_id].append(queue)
        return queue
    
    def unsubscribe(self, execution_id: UUID, queue: asyncio.Queue) -> None:
        """Unsubscribe from execution progress."""
        if execution_id in self._subscribers:
            try:
                self._subscribers[execution_id].remove(queue)
            except ValueError:
                pass
            if not self._subscribers[execution_id]:
                del self._subscribers[execution_id]
    
    async def publish(self, event: ProgressEvent) -> None:
        """Publish event to all subscribers for this execution."""
        if event.execution_id in self._subscribers:
            for queue in self._subscribers[event.execution_id]:
                await queue.put(event)
    
    def subscriber_count(self, execution_id: UUID) -> int:
        """Get number of subscribers for an execution."""
        return len(self._subscribers.get(execution_id, []))


class LLMExecutionService:
    """
    Service for managing LLM-powered workflow executions.
    Bridges the API layer to the LLMStepExecutor.
    """
    
    def __init__(
        self,
        executor: LLMStepExecutor,
        workflow_loader: WorkflowLoader,
        document_repo: DocumentRepository,
        execution_repo: ExecutionRepository,
        telemetry: Optional[TelemetryService] = None,
        progress_publisher: Optional[ProgressPublisher] = None,
    ):
        self._executor = executor
        self._workflow_loader = workflow_loader
        self._document_repo = document_repo
        self._execution_repo = execution_repo
        self._telemetry = telemetry
        self._progress = progress_publisher or ProgressPublisher()
        self._contexts: Dict[UUID, ExecutionContext] = {}
    
    @property
    def progress_publisher(self) -> ProgressPublisher:
        """Get the progress publisher for SSE subscriptions."""
        return self._progress
    
    async def start_execution(
        self,
        workflow_id: str,
        scope_type: str,
        scope_id: str,
        user_id: Optional[str] = None,
        initial_input: Optional[Dict[str, Any]] = None,
    ) -> ExecutionInfo:
        """Start a new workflow execution."""
        workflow = self._workflow_loader.load(workflow_id)
        if workflow is None:
            raise WorkflowNotFoundError(f"Workflow not found: {workflow_id}")
        
        errors = workflow.validate()
        if errors:
            raise ValueError(f"Invalid workflow: {errors}")
        
        context = await ExecutionContext.create(
            workflow_id=workflow_id,
            scope_type=scope_type,
            scope_id=scope_id,
            document_repo=self._document_repo,
            execution_repo=self._execution_repo,
        )
        
        self._contexts[context.execution_id] = context
        
        if initial_input:
            await context.save_output_document(
                document_type="user-input",
                title="Initial Input",
                content=initial_input,
                step_id="initialization",
            )
        
        await self._progress.publish(ProgressEvent(
            event_type="execution_started",
            execution_id=context.execution_id,
            data={"workflow_id": workflow_id},
        ))
        
        return self._context_to_info(context, workflow)
    
    async def get_execution(self, execution_id: UUID) -> ExecutionInfo:
        """Get execution details."""
        context = await self._get_context(execution_id)
        workflow = self._workflow_loader.load(context.workflow_id)
        return self._context_to_info(context, workflow)

    
    async def execute_step(
        self,
        execution_id: UUID,
        step_id: Optional[str] = None,
    ) -> StepOutput:
        """Execute the next step (or specified step) in the workflow."""
        context = await self._get_context(execution_id)
        workflow = self._workflow_loader.load(context.workflow_id)
        
        if step_id is None:
            step_id = self._get_next_step(context, workflow)
            if step_id is None:
                raise LLMInvalidStateError("No pending steps to execute")
        
        step = workflow.get_step(step_id)
        if step is None:
            raise ValueError(f"Step not found: {step_id}")
        
        await self._progress.publish(ProgressEvent(
            event_type="step_started",
            execution_id=execution_id,
            step_id=step_id,
            data={"role": step.role},
        ))
        
        inputs = await self._gather_inputs(context, step.inputs)
        
        output = await self._executor.execute(
            step_id=step_id,
            role=step.role,
            task_prompt=step.task_prompt_id,
            context=context,
            inputs=inputs,
            output_type=step.outputs[0] if step.outputs else step_id,
            output_schema=None,  # Schema validation handled separately
            allow_clarification=step.allow_clarification,
            model=step.model,
        )
        
        if output.needs_clarification:
            await self._progress.publish(ProgressEvent(
                event_type="clarification_needed",
                execution_id=execution_id,
                step_id=step_id,
                data={"questions": output.clarification_questions},
            ))
        elif output.success:
            await self._progress.publish(ProgressEvent(
                event_type="step_completed",
                execution_id=execution_id,
                step_id=step_id,
                data={"document_id": str(output.document.document_id) if output.document else None},
            ))
            if step.is_final:
                await self._progress.publish(ProgressEvent(
                    event_type="execution_completed",
                    execution_id=execution_id,
                ))
        else:
            await self._progress.publish(ProgressEvent(
                event_type="step_failed",
                execution_id=execution_id,
                step_id=step_id,
                data={"error": output.error_message},
            ))
        
        return output

    
    async def submit_clarification(
        self,
        execution_id: UUID,
        step_id: str,
        answers: Dict[str, str],
    ) -> StepOutput:
        """Submit clarification answers and continue execution."""
        context = await self._get_context(execution_id)
        workflow = self._workflow_loader.load(context.workflow_id)
        
        step = workflow.get_step(step_id)
        if step is None:
            raise ValueError(f"Step not found: {step_id}")
        
        progress = context.step_progress.get(step_id)
        if not progress or progress.status != "waiting_input":
            raise LLMInvalidStateError(f"Step {step_id} is not waiting for clarification")
        
        inputs = await self._gather_inputs(context, step.inputs)
        
        output = await self._executor.continue_with_clarification(
            step_id=step_id,
            role=step.role,
            task_prompt=step.task_prompt_id,
            context=context,
            clarification_answers=answers,
            inputs=inputs,
            output_type=step.outputs[0] if step.outputs else step_id,
            output_schema=None,  # Schema validation handled separately
        )
        
        if output.success:
            await self._progress.publish(ProgressEvent(
                event_type="step_completed",
                execution_id=execution_id,
                step_id=step_id,
            ))
        
        return output
    
    async def cancel_execution(self, execution_id: UUID) -> ExecutionInfo:
        """Cancel a running execution."""
        context = await self._get_context(execution_id)
        
        state = await self._execution_repo.get(execution_id)
        if state and state.status in (ExecutionStatus.COMPLETED, ExecutionStatus.CANCELLED):
            raise LLMInvalidStateError(f"Cannot cancel execution in {state.status} state")
        
        if state:
            state.status = ExecutionStatus.CANCELLED
            await self._execution_repo.save(state)
        
        await self._progress.publish(ProgressEvent(
            event_type="execution_cancelled",
            execution_id=execution_id,
        ))
        
        workflow = self._workflow_loader.load(context.workflow_id)
        return self._context_to_info(context, workflow)

    
    async def list_executions(
        self,
        scope_type: Optional[str] = None,
        scope_id: Optional[str] = None,
        status: Optional[ExecutionStatus] = None,
    ) -> List[ExecutionInfo]:
        """List executions with optional filters."""
        if scope_type and scope_id:
            states = await self._execution_repo.list_by_scope(scope_type, scope_id)
        else:
            states = await self._execution_repo.list_active()
        
        if status:
            states = [s for s in states if s.status == status]
        
        results = []
        for state in states:
            workflow = self._workflow_loader.load(state.workflow_id)
            if workflow:
                info = ExecutionInfo(
                    execution_id=state.execution_id,
                    workflow_id=state.workflow_id,
                    scope_type=state.scope_type,
                    scope_id=state.scope_id,
                    status=state.status.value,
                    current_step_id=None,
                    completed_steps=[],
                    step_statuses={},
                    needs_clarification=False,
                    clarification_questions=None,
                    started_at=state.started_at,
                    completed_at=state.completed_at,
                    error=None,
                    total_cost_usd=Decimal("0"),
                )
                results.append(info)
        
        return results
    
    async def stream_progress(
        self,
        execution_id: UUID,
    ) -> AsyncGenerator[ProgressEvent, None]:
        """Stream progress events for an execution."""
        queue = self._progress.subscribe(execution_id)
        try:
            while True:
                event = await queue.get()
                yield event
                if event.event_type in ("execution_completed", "execution_cancelled", "execution_failed"):
                    break
        finally:
            self._progress.unsubscribe(execution_id, queue)

    
    async def _get_context(self, execution_id: UUID) -> ExecutionContext:
        """Get or load execution context."""
        if execution_id in self._contexts:
            return self._contexts[execution_id]
        
        context = await ExecutionContext.load(
            execution_id=execution_id,
            document_repo=self._document_repo,
            execution_repo=self._execution_repo,
        )
        
        if context is None:
            raise LLMExecutionNotFoundError(f"Execution not found: {execution_id}")
        
        self._contexts[execution_id] = context
        return context
    
    def _get_next_step(
        self,
        context: ExecutionContext,
        workflow: WorkflowDefinition,
    ) -> Optional[str]:
        """Determine the next step to execute."""
        order = workflow.get_execution_order()
        
        for step_id in order:
            progress = context.step_progress.get(step_id)
            if progress is None or progress.status == "pending":
                return step_id
            if progress.status == "waiting_input":
                return step_id
        
        return None
    
    async def _gather_inputs(
        self,
        context: ExecutionContext,
        input_types: List[str],
    ) -> List[StepInput]:
        """Gather input documents for a step."""
        inputs = []
        for doc_type in input_types:
            doc = await context.get_input_document(doc_type)
            if doc:
                inputs.append(StepInput(
                    document_type=doc_type,
                    content=doc.content,
                    title=doc.title,
                ))
        return inputs
    
    def _context_to_info(
        self,
        context: ExecutionContext,
        workflow: Optional[WorkflowDefinition],
    ) -> ExecutionInfo:
        """Convert ExecutionContext to ExecutionInfo."""
        current_step = None
        needs_clarification = False
        clarification_questions = None
        completed_steps = []
        step_statuses = {}
        
        if workflow:
            for step_id in workflow.get_execution_order():
                progress = context.step_progress.get(step_id)
                if progress:
                    step_statuses[step_id] = progress.status
                    if progress.status == "completed":
                        completed_steps.append(step_id)
                    elif progress.status == "running":
                        current_step = step_id
                    elif progress.status == "waiting_input":
                        current_step = step_id
                        needs_clarification = True
                else:
                    step_statuses[step_id] = "pending"
        
        status = "pending"
        if any(p.status == "running" for p in context.step_progress.values()):
            status = "running"
        elif needs_clarification:
            status = "waiting_clarification"
        elif workflow and len(completed_steps) == len(workflow.steps):
            status = "completed"
        elif any(p.status == "failed" for p in context.step_progress.values()):
            status = "failed"
        
        return ExecutionInfo(
            execution_id=context.execution_id,
            workflow_id=context.workflow_id,
            scope_type=context.scope_type,
            scope_id=context.scope_id,
            status=status,
            current_step_id=current_step,
            completed_steps=completed_steps,
            step_statuses=step_statuses,
            needs_clarification=needs_clarification,
            clarification_questions=clarification_questions,
            started_at=None,
            completed_at=None,
            error=None,
            total_cost_usd=Decimal("0"),
        )

