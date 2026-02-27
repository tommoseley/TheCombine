"""LLM-integrated step executor."""

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from app.llm import (
    LLMProvider,
    LLMResponse,
    LLMException,
    PromptBuilder,
    PromptContext,
    OutputParser,
    DocumentCondenser,
    TelemetryService,
)
from app.persistence import StoredDocument
from app.execution.context import ExecutionContext


logger = logging.getLogger(__name__)


@dataclass
class StepInput:
    """Input document for a step."""
    document_type: str
    content: Dict[str, Any]
    title: str


@dataclass
class StepOutput:
    """Output from step execution."""
    success: bool
    document: Optional[StoredDocument] = None
    error_message: Optional[str] = None
    needs_clarification: bool = False
    clarification_questions: Optional[List[str]] = None
    validation_errors: Optional[List[str]] = None
    llm_response: Optional[LLMResponse] = None


class LLMStepExecutor:
    """Execute workflow steps using LLM providers."""
    
    def __init__(
        self,
        llm_provider: LLMProvider,
        prompt_builder: PromptBuilder,
        output_parser: OutputParser,
        telemetry: TelemetryService,
        condenser: Optional[DocumentCondenser] = None,
        default_model: str = "sonnet",
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ):
        self._llm = llm_provider
        self._prompt_builder = prompt_builder
        self._output_parser = output_parser
        self._telemetry = telemetry
        self._condenser = condenser or DocumentCondenser()
        self._default_model = default_model
        self._max_tokens = max_tokens
        self._temperature = temperature
    
    async def execute(
        self,
        step_id: str,
        role: str,
        task_prompt: str,
        context: ExecutionContext,
        inputs: Optional[List[StepInput]] = None,
        output_type: str = "document",
        output_schema: Optional[Dict[str, Any]] = None,
        required_fields: Optional[List[str]] = None,
        allow_clarification: bool = True,
        model: Optional[str] = None,
    ) -> StepOutput:
        """Execute a workflow step."""
        context.start_step(step_id)
        call_id = uuid4()
        
        try:
            input_docs = self._prepare_inputs(inputs, role) if inputs else None
            
            prompt_context = PromptContext(
                workflow_name=context.workflow_id,
                step_name=step_id,
                scope_id=context.scope_id,
            )
            
            system_prompt, messages = self._prompt_builder.build_messages(
                role=role,
                task_prompt=task_prompt,
                input_documents=input_docs,
                context=prompt_context,
            )
            
            model_to_use = model or self._default_model
            logger.info(f"Calling LLM for step {step_id} with model {model_to_use}")
            
            response = await self._llm.complete_with_retry(
                messages=messages,
                model=model_to_use,
                max_tokens=self._max_tokens,
                temperature=self._temperature,
                system_prompt=system_prompt,
            )
            
            await self._telemetry.log_call(
                call_id=call_id,
                execution_id=context.execution_id,
                step_id=step_id,
                model=response.model,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                latency_ms=response.latency_ms,
                cached=response.cached,
            )
            
            return await self._process_response(
                step_id, context, response, output_type, 
                output_schema, required_fields, allow_clarification
            )
            
        except LLMException as e:
            return await self._handle_llm_error(e, call_id, step_id, context, model)
        except Exception as e:
            logger.exception(f"Unexpected error in step {step_id}")
            context.fail_step(step_id, str(e))
            await context.save_state()
            return StepOutput(success=False, error_message=str(e))

    async def _process_response(
        self,
        step_id: str,
        context: ExecutionContext,
        response: LLMResponse,
        output_type: str,
        output_schema: Optional[Dict[str, Any]],
        required_fields: Optional[List[str]],
        allow_clarification: bool,
    ) -> StepOutput:
        """Process LLM response and return step output."""
        parse_result, validation, clarification = self._output_parser.parse(
            response.content,
            schema=output_schema,
            required_fields=required_fields,
            check_clarification=allow_clarification,
        )
        
        if clarification and clarification.needs_clarification:
            context.wait_for_input(step_id)
            await context.save_state()
            questions = [q.question for q in clarification.questions]
            return StepOutput(
                success=False,
                needs_clarification=True,
                clarification_questions=questions,
                llm_response=response,
            )
        
        if not parse_result.success:
            context.fail_step(step_id, "Failed to parse LLM response")
            await context.save_state()
            return StepOutput(
                success=False,
                error_message="; ".join(parse_result.error_messages),
                llm_response=response,
            )
        
        if not validation.valid:
            context.fail_step(step_id, "Output validation failed")
            await context.save_state()
            errors = [f"{e.field}: {e.message}" for e in validation.errors]
            return StepOutput(
                success=False,
                validation_errors=errors,
                llm_response=response,
            )
        
        document = await context.save_output_document(
            document_type=output_type,
            title=f"{step_id} Output",
            content=parse_result.data,
            step_id=step_id,
        )
        
        context.complete_step(step_id)
        await context.save_state()
        
        return StepOutput(success=True, document=document, llm_response=response)
    
    async def _handle_llm_error(
        self,
        e: LLMException,
        call_id: UUID,
        step_id: str,
        context: ExecutionContext,
        model: Optional[str],
    ) -> StepOutput:
        """Handle LLM exception."""
        logger.error(f"LLM error in step {step_id}: {e.error.message}")
        
        await self._telemetry.log_call(
            call_id=call_id,
            execution_id=context.execution_id,
            step_id=step_id,
            model=model or self._default_model,
            input_tokens=0,
            output_tokens=0,
            latency_ms=0,
            error_type=e.error.error_type,
            error_message=e.error.message,
        )
        
        context.fail_step(step_id, e.error.message)
        await context.save_state()
        
        return StepOutput(success=False, error_message=e.error.message)
    
    async def continue_with_clarification(
        self,
        step_id: str,
        role: str,
        task_prompt: str,
        context: ExecutionContext,
        clarification_answers: Dict[str, str],
        inputs: Optional[List[StepInput]] = None,
        output_type: str = "document",
        output_schema: Optional[Dict[str, Any]] = None,
        required_fields: Optional[List[str]] = None,
        model: Optional[str] = None,
    ) -> StepOutput:
        """Continue step with clarification answers."""
        if step_id in context.step_progress:
            context.step_progress[step_id].attempt += 1
        context.start_step(step_id)
        
        call_id = uuid4()
        
        try:
            input_docs = self._prepare_inputs(inputs, role) if inputs else None
            
            prompt_context = PromptContext(
                workflow_name=context.workflow_id,
                step_name=step_id,
                scope_id=context.scope_id,
                clarification_answers=clarification_answers,
            )
            
            system_prompt, messages = self._prompt_builder.build_messages(
                role=role,
                task_prompt=task_prompt,
                input_documents=input_docs,
                context=prompt_context,
            )
            
            model_to_use = model or self._default_model
            
            response = await self._llm.complete_with_retry(
                messages=messages,
                model=model_to_use,
                max_tokens=self._max_tokens,
                temperature=self._temperature,
                system_prompt=system_prompt,
            )
            
            await self._telemetry.log_call(
                call_id=call_id,
                execution_id=context.execution_id,
                step_id=step_id,
                model=response.model,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                latency_ms=response.latency_ms,
                cached=response.cached,
            )
            
            return await self._process_response(
                step_id, context, response, output_type,
                output_schema, required_fields, False
            )
            
        except LLMException as e:
            return await self._handle_llm_error(e, call_id, step_id, context, model)
        except Exception as e:
            context.fail_step(step_id, str(e))
            await context.save_state()
            return StepOutput(success=False, error_message=str(e))
    
    def _prepare_inputs(self, inputs: List[StepInput], role: str) -> List[Dict[str, str]]:
        """Prepare and condense input documents."""
        result = []
        for inp in inputs:
            content_str = json.dumps(inp.content, indent=2)
            condensed = self._condenser.condense(content_str, role, inp.document_type)
            result.append({"type": inp.document_type, "content": condensed})
        return result
