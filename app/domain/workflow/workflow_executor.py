"""Workflow executor - orchestrate multi-step workflow execution.

Coordinates step sequencing, iteration expansion, acceptance pauses,
and state management for complete workflow execution.
"""

import logging
from dataclasses import dataclass
from typing import Dict, Optional

from app.domain.workflow.context import WorkflowContext
from app.domain.workflow.gates.acceptance import AcceptanceGate
from app.domain.workflow.iteration import IterationHandler
from app.domain.workflow.models import Workflow, WorkflowStep
from app.domain.workflow.step_executor import StepExecutor
from app.domain.workflow.step_state import StepState, StepStatus
from app.domain.workflow.workflow_state import (
    WorkflowState, WorkflowStatus, IterationProgress, AcceptanceDecision
)


logger = logging.getLogger(__name__)


@dataclass
class WorkflowExecutionResult:
    """Result of workflow execution."""
    state: WorkflowState
    context: WorkflowContext
    paused: bool = False
    pause_reason: Optional[str] = None


class WorkflowExecutor:
    """Execute complete workflow with iteration and acceptance."""
    
    def __init__(
        self,
        step_executor: StepExecutor,
        iteration_handler_factory=None,
        acceptance_gate_factory=None,
    ):
        self.step_executor = step_executor
        self._iteration_handler_factory = iteration_handler_factory or IterationHandler
        self._acceptance_gate_factory = acceptance_gate_factory or AcceptanceGate
    
    async def start(
        self,
        workflow: Workflow,
        project_id: str,
    ) -> WorkflowExecutionResult:
        """Start new workflow execution."""
        state = WorkflowState(
            workflow_id=workflow.workflow_id,
            project_id=project_id,
        )
        context = WorkflowContext(workflow, project_id)
        state.start()
        logger.info(f"Starting workflow {workflow.workflow_id} for project {project_id}")
        return await self.run_until_pause(workflow, state, context)
    
    async def resume(
        self,
        workflow: Workflow,
        state: WorkflowState,
        context: WorkflowContext,
    ) -> WorkflowExecutionResult:
        """Resume paused workflow."""
        state.resume()
        logger.info(f"Resuming workflow {workflow.workflow_id}")
        return await self.run_until_pause(workflow, state, context)

    
    async def run_until_pause(
        self,
        workflow: Workflow,
        state: WorkflowState,
        context: WorkflowContext,
    ) -> WorkflowExecutionResult:
        """Execute steps until completion, failure, or pause."""
        iteration_handler = self._iteration_handler_factory(workflow)
        acceptance_gate = self._acceptance_gate_factory(workflow)
        
        while True:
            next_step = self._get_next_step(workflow, state)
            
            if next_step is None:
                state.complete()
                logger.info(f"Workflow {workflow.workflow_id} completed")
                return WorkflowExecutionResult(state=state, context=context)
            
            state.current_step_id = next_step.step_id
            logger.info(f"Executing step {next_step.step_id}")
            
            if next_step.is_iteration:
                result = await self._execute_iteration_step(
                    next_step, workflow, state, context, iteration_handler, acceptance_gate
                )
            else:
                result = await self._execute_production_step(
                    next_step, workflow, state, context, acceptance_gate
                )
            
            if result.paused:
                return result
            
            if state.status == WorkflowStatus.FAILED:
                return WorkflowExecutionResult(state=state, context=context)
    
    async def process_acceptance(
        self,
        workflow: Workflow,
        state: WorkflowState,
        context: WorkflowContext,
        decision: AcceptanceDecision,
    ) -> WorkflowExecutionResult:
        """Process acceptance decision and continue if approved."""
        acceptance_gate = self._acceptance_gate_factory(workflow)
        key = acceptance_gate.make_decision_key(decision.doc_type, decision.scope_id)
        state.acceptance_decisions[key] = decision
        
        if decision.accepted:
            logger.info(f"Document {decision.doc_type} accepted, resuming workflow")
            return await self.resume(workflow, state, context)
        else:
            logger.info(f"Document {decision.doc_type} rejected")
            state.fail(f"Document {decision.doc_type} rejected: {decision.comment or 'No reason given'}")
            return WorkflowExecutionResult(state=state, context=context)
    
    async def process_clarification(
        self,
        workflow: Workflow,
        state: WorkflowState,
        context: WorkflowContext,
        answers: Dict[str, str],
    ) -> WorkflowExecutionResult:
        """Process clarification answers and continue."""
        step_id = state.pending_clarification_step_id
        if not step_id:
            state.fail("No pending clarification")
            return WorkflowExecutionResult(state=state, context=context)
        
        step = workflow.get_step(step_id)
        if not step:
            state.fail(f"Step {step_id} not found")
            return WorkflowExecutionResult(state=state, context=context)
        
        step_state = state.get_step_state(step_id)
        if not step_state:
            state.fail(f"No state for step {step_id}")
            return WorkflowExecutionResult(state=state, context=context)
        
        result = await self.step_executor.continue_after_clarification(
            step, workflow, context, step_state, answers,
            scope_id=context.current_scope().scope_id if context.current_scope() else None,
            parent_scope_ids=context.get_scope_chain(),
        )
        
        state.set_step_state(step_id, result.state)
        
        if result.state.status == StepStatus.COMPLETED:
            if result.output and step.produces:
                context.store_document(step.produces, result.output)
            state.mark_step_complete(step_id)
            state.resume()
            return await self.run_until_pause(workflow, state, context)
        elif result.state.status == StepStatus.CLARIFYING:
            state.wait_for_clarification(step_id)
            return WorkflowExecutionResult(
                state=state, context=context, paused=True,
                pause_reason=f"Step {step_id} needs clarification"
            )
        else:
            state.fail(f"Step {step_id} failed: {result.state.error}")
            return WorkflowExecutionResult(state=state, context=context)

    
    def _get_next_step(
        self,
        workflow: Workflow,
        state: WorkflowState,
    ) -> Optional[WorkflowStep]:
        """Determine next step to execute."""
        for step in workflow.steps:
            if not state.is_step_complete(step.step_id):
                return step
        return None
    
    async def _execute_production_step(
        self,
        step: WorkflowStep,
        workflow: Workflow,
        state: WorkflowState,
        context: WorkflowContext,
        acceptance_gate: AcceptanceGate,
    ) -> WorkflowExecutionResult:
        """Execute a single production step."""
        step_state = state.get_step_state(step.step_id)
        if step_state is None:
            step_state = StepState(step_id=step.step_id)
        
        result = await self.step_executor.execute(
            step, workflow, context, step_state,
            scope_id=context.current_scope().scope_id if context.current_scope() else None,
            parent_scope_ids=context.get_scope_chain(),
        )
        
        state.set_step_state(step.step_id, result.state)
        
        if result.state.status == StepStatus.CLARIFYING:
            state.wait_for_clarification(step.step_id)
            return WorkflowExecutionResult(
                state=state, context=context, paused=True,
                pause_reason=f"Step {step.step_id} needs clarification"
            )
        
        if result.state.status == StepStatus.FAILED:
            state.fail(f"Step {step.step_id} failed: {result.state.error}")
            return WorkflowExecutionResult(state=state, context=context)
        
        if result.output and step.produces:
            context.store_document(step.produces, result.output)
            
            if acceptance_gate.requires_acceptance(step.produces):
                scope_id = context.current_scope().scope_id if context.current_scope() else None
                if acceptance_gate.is_pending(step.produces, scope_id, state.acceptance_decisions):
                    state.wait_for_acceptance(step.produces, scope_id)
                    return WorkflowExecutionResult(
                        state=state, context=context, paused=True,
                        pause_reason=f"Document {step.produces} requires acceptance"
                    )
        
        state.mark_step_complete(step.step_id)
        return WorkflowExecutionResult(state=state, context=context)

    
    async def _execute_iteration_step(
        self,
        step: WorkflowStep,
        workflow: Workflow,
        state: WorkflowState,
        context: WorkflowContext,
        iteration_handler: IterationHandler,
        acceptance_gate: AcceptanceGate,
    ) -> WorkflowExecutionResult:
        """Execute an iteration step."""
        progress = state.iteration_progress.get(step.step_id)
        
        if progress is None:
            instances = iteration_handler.expand(step, context)
            if not instances:
                state.mark_step_complete(step.step_id)
                return WorkflowExecutionResult(state=state, context=context)
            
            progress = IterationProgress(
                step_id=step.step_id,
                total=len(instances),
                completed=0,
                current_index=0,
                entity_ids=[inst.entity_id for inst in instances],
            )
            state.iteration_progress[step.step_id] = progress
        
        instances = iteration_handler.expand(step, context)
        
        while progress.current_index < progress.total:
            instance = instances[progress.current_index]
            context.push_scope(instance.scope, instance.scope_id, instance.entity_data)
            
            try:
                for nested_step in instance.steps:
                    nested_result = await self._execute_production_step(
                        nested_step, workflow, state, context, acceptance_gate
                    )
                    
                    if nested_result.paused:
                        return nested_result
                    
                    if state.status == WorkflowStatus.FAILED:
                        return WorkflowExecutionResult(state=state, context=context)
                
                progress.completed += 1
                progress.current_index += 1
                
            finally:
                context.pop_scope()
        
        state.mark_step_complete(step.step_id)
        return WorkflowExecutionResult(state=state, context=context)
