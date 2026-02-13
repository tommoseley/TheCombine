"""Step executor - execute a single workflow step per ADR-012.

This is the main orchestrator for step-level execution, combining:
- Prompt loading
- Input resolution
- LLM execution
- Clarification gate
- QA gate
- Remediation loop
"""

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol

from app.domain.workflow.gates.clarification import ClarificationGate, ClarificationResult
from app.domain.workflow.gates.qa import QAGate
from app.domain.workflow.input_resolver import DocumentStore, InputResolver, InputResolutionResult
from app.domain.workflow.models import Workflow, WorkflowStep
from app.domain.workflow.prompt_loader import PromptLoader
from app.domain.workflow.remediation import RemediationLoop
from app.domain.workflow.step_state import ClarificationQuestion, QAFinding, QAResult, StepState, StepStatus


logger = logging.getLogger(__name__)


class LLMService(Protocol):
    """Protocol for LLM completion service."""
    
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs
    ) -> str:
        """Generate completion from LLM."""
        ...


@dataclass
class ExecutionResult:
    """Result of step execution."""
    
    state: StepState
    clarification_result: Optional[ClarificationResult] = None
    qa_result: Optional[QAResult] = None
    output: Optional[Dict[str, Any]] = None


class StepExecutor:
    """Execute a single workflow step per ADR-012."""
    
    def __init__(
        self,
        prompt_loader: PromptLoader,
        clarification_gate: ClarificationGate,
        qa_gate: QAGate,
        llm_service: LLMService,
        max_remediation_attempts: int = 3,
    ):
        self.prompt_loader = prompt_loader
        self.clarification_gate = clarification_gate
        self.qa_gate = qa_gate
        self.llm_service = llm_service
        self.remediation_loop = RemediationLoop(max_remediation_attempts)
    
    async def execute(
        self,
        step: WorkflowStep,
        workflow: Workflow,
        store: DocumentStore,
        state: StepState,
        scope_id: Optional[str] = None,
        parent_scope_ids: Optional[Dict[str, str]] = None,
    ) -> ExecutionResult:
        """Execute step and return result."""
        logger.info(f"Executing step {step.step_id} (attempt {state.attempt + 1})")
        
        state.start()
        
        try:
            role_prompt = self._load_role_prompt(step)
            task_prompt = self._load_task_prompt(step)
            
            input_resolver = InputResolver(workflow, store)
            input_result = input_resolver.resolve(
                step, 
                scope_id=scope_id,
                parent_scope_ids=parent_scope_ids
            )
            
            if not input_result.success:
                state.fail(
                    f"Input resolution failed: {'; '.join(input_result.errors)}",
                    details={"errors": input_result.errors}
                )
                return ExecutionResult(state=state)
            
            user_prompt = self._build_user_prompt(task_prompt, input_result)
            
            return await self._execute_with_remediation(
                step, state, role_prompt, task_prompt, user_prompt
            )
            
        except Exception as e:
            logger.exception(f"Step {step.step_id} failed with exception")
            state.fail(str(e), details={"exception_type": type(e).__name__})
            return ExecutionResult(state=state)
    
    async def continue_after_clarification(
        self,
        step: WorkflowStep,
        workflow: Workflow,
        store: DocumentStore,
        state: StepState,
        answers: Dict[str, str],
        scope_id: Optional[str] = None,
        parent_scope_ids: Optional[Dict[str, str]] = None,
    ) -> ExecutionResult:
        """Continue execution after clarification answers received."""
        if state.status != StepStatus.CLARIFYING:
            logger.warning(f"continue_after_clarification called but state is {state.status}")
        
        state.provide_answers(answers)
        logger.info(f"Continuing step {step.step_id} after clarification")
        
        try:
            role_prompt = self._load_role_prompt(step)
            task_prompt = self._load_task_prompt(step)
            
            input_resolver = InputResolver(workflow, store)
            input_result = input_resolver.resolve(
                step,
                scope_id=scope_id,
                parent_scope_ids=parent_scope_ids
            )
            
            if not input_result.success:
                state.fail(f"Input resolution failed: {'; '.join(input_result.errors)}")
                return ExecutionResult(state=state)
            
            user_prompt = self._build_user_prompt_with_answers(
                task_prompt, input_result, state.clarification_questions, answers
            )
            
            return await self._execute_with_remediation(
                step, state, role_prompt, task_prompt, user_prompt,
                allow_clarification=False
            )
            
        except Exception as e:
            logger.exception(f"Step {step.step_id} failed after clarification")
            state.fail(str(e), details={"exception_type": type(e).__name__})
            return ExecutionResult(state=state)
    
    async def _execute_with_remediation(
        self,
        step: WorkflowStep,
        state: StepState,
        role_prompt: str,
        task_prompt: str,
        user_prompt: str,
        allow_clarification: bool = True,
    ) -> ExecutionResult:
        """Execute step with remediation loop."""
        current_prompt = user_prompt
        
        while True:
            logger.debug(f"Calling LLM for step {step.step_id}")
            response = await self.llm_service.complete(
                system_prompt=role_prompt,
                user_prompt=current_prompt,
            )
            state.raw_llm_response = response
            
            if allow_clarification and state.attempt == 1:
                clarification_result = self.clarification_gate.check(response)
                if clarification_result.needs_clarification:
                    if clarification_result.questions:
                        logger.info(f"Step {step.step_id} needs clarification")
                        state.request_clarification(clarification_result.questions)
                        return ExecutionResult(
                            state=state,
                            clarification_result=clarification_result
                        )
            
            output = self._parse_output(response)
            if output is None:
                qa_result = QAResult(
                    passed=False,
                    findings=[
                        QAFinding(
                            path="$",
                            message="Response is not valid JSON",
                            severity="error",
                            rule="json_parse"
                        )
                    ]
                )
            else:
                state.output_document = output
                state.status = StepStatus.QA_CHECKING
                qa_result = self.qa_gate.check(output, doc_type=step.produces or "unknown")
            
            state.record_qa_result(qa_result)
            
            if qa_result.passed:
                logger.info(f"Step {step.step_id} completed successfully")
                return ExecutionResult(
                    state=state,
                    qa_result=qa_result,
                    output=output
                )
            
            if self.remediation_loop.should_retry(state, qa_result):
                logger.info(f"Step {step.step_id} QA failed, retrying")
                
                context = self.remediation_loop.build_context(
                    task_prompt, state, qa_result
                )
                current_prompt = self.remediation_loop.build_remediation_prompt(context)
                
                state.attempt += 1
                state.status = StepStatus.REMEDIATING
                continue
            
            logger.error(f"Step {step.step_id} failed after {state.attempt} attempts")
            return ExecutionResult(
                state=state,
                qa_result=qa_result,
                output=output
            )
    
    def _load_role_prompt(self, step: WorkflowStep) -> str:
        if not step.role:
            return ""
        return self.prompt_loader.load_role(step.role)
    
    def _load_task_prompt(self, step: WorkflowStep) -> str:
        if not step.task_prompt:
            return ""
        return self.prompt_loader.load_task(step.task_prompt)
    
    def _build_user_prompt(
        self,
        task_prompt: str,
        input_result: InputResolutionResult,
    ) -> str:
        sections = []
        
        sections.append("## Task")
        sections.append(task_prompt)
        sections.append("")
        
        if input_result.inputs:
            sections.append("## Inputs")
            for key, resolved in input_result.inputs.items():
                if resolved.found and resolved.value is not None:
                    sections.append(f"### {key}")
                    sections.append("```json")
                    sections.append(json.dumps(resolved.value, indent=2))
                    sections.append("```")
                    sections.append("")
        
        return "\n".join(sections)
    
    def _build_user_prompt_with_answers(
        self,
        task_prompt: str,
        input_result: InputResolutionResult,
        questions: List[ClarificationQuestion],
        answers: Dict[str, str],
    ) -> str:
        sections = []
        
        sections.append("## Task")
        sections.append(task_prompt)
        sections.append("")
        
        if input_result.inputs:
            sections.append("## Inputs")
            for key, resolved in input_result.inputs.items():
                if resolved.found and resolved.value is not None:
                    sections.append(f"### {key}")
                    sections.append("```json")
                    sections.append(json.dumps(resolved.value, indent=2))
                    sections.append("```")
                    sections.append("")
        
        if questions and answers:
            sections.append("## Clarification Answers")
            sections.append("You previously asked clarification questions. Here are the answers:")
            sections.append("")
            for q in questions:
                answer = answers.get(q.id, "(no answer provided)")
                sections.append(f"**Q: {q.text}**")
                sections.append(f"A: {answer}")
                sections.append("")
            sections.append("Please proceed with the task using these answers.")
        
        return "\n".join(sections)
    
    def _parse_output(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse LLM response as JSON."""
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        import re
        patterns = [
            r'```json\s*([\s\S]*?)\s*```',
            r'```\s*([\s\S]*?)\s*```',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response)
            for match in matches:
                try:
                    return json.loads(match)
                except json.JSONDecodeError:
                    continue
        
        return None