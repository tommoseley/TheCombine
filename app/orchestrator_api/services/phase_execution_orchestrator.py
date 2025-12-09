"""
Phase Execution Orchestrator - Coordinate phase execution across components.

This module orchestrates the execution flow by coordinating all components
in the correct sequence. It remains thin (<150 lines) by delegating all
business logic to specialized components.

Author: D-1 (Senior Developer)
Epic: PIPELINE-175B
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
import logging

from app.orchestrator_api.services.llm_response_parser import LLMResponseParser
from app.orchestrator_api.services.llm_caller import LLMCaller
from app.orchestrator_api.services.configuration_loader import ConfigurationLoader, ConfigurationError
from app.orchestrator_api.services.usage_recorder import UsageRecorder, UsageRecord
from app.orchestrator_api.services.role_prompt_service import RolePromptService

logger = logging.getLogger(__name__)


@dataclass
class PhaseExecutionResult:
    """Result of phase execution."""
    success: bool
    artifact: Dict[str, Any]
    artifact_type: str
    next_phase: Optional[str]
    prompt_id: str
    llm_response_raw: str
    execution_time_ms: int
    error: Optional[str] = None


class ExecutionError(Exception):
    """Base exception for phase execution errors."""
    def __init__(self, message: str, phase_name: str, pipeline_id: str):
        self.message = message
        self.phase_name = phase_name
        self.pipeline_id = pipeline_id
        super().__init__(f"[{pipeline_id}:{phase_name}] {message}")


class PromptBuildError(ExecutionError):
    """Prompt building error."""
    pass


class LLMError(ExecutionError):
    """LLM API call error."""
    pass


class ParseError(ExecutionError):
    """Response parsing error."""
    pass


class PhaseExecutionOrchestrator:
    """Coordinate phase execution across components."""
    
    def __init__(
        self,
        config_loader: ConfigurationLoader,
        prompt_builder: RolePromptService,
        llm_caller: LLMCaller,
        parser: LLMResponseParser,
        usage_recorder: UsageRecorder
    ):
        """
        Initialize orchestrator with all dependencies.
        
        Args:
            config_loader: Configuration loader instance
            prompt_builder: Prompt builder service instance
            llm_caller: LLM caller instance
            parser: Response parser instance
            usage_recorder: Usage recorder instance
        """
        self._config_loader = config_loader
        self._prompt_builder = prompt_builder
        self._llm_caller = llm_caller
        self._parser = parser
        self._usage_recorder = usage_recorder
    
    def execute_phase(
        self,
        pipeline_id: str,
        phase_name: str,
        epic_context: str,
        pipeline_state: Dict[str, Any],
        artifacts: Dict[str, Any]
    ) -> PhaseExecutionResult:
        """
        Execute phase by coordinating all components.
        
        Flow:
        1. Load phase configuration
        2. Build prompt with context
        3. Call LLM
        4. Parse response
        5. Record usage (best-effort)
        6. Return result
        
        Args:
            pipeline_id: Pipeline identifier
            phase_name: Phase to execute
            epic_context: Epic description
            pipeline_state: Current pipeline state (IMMUTABLE)
            artifacts: Previous phase artifacts (IMMUTABLE)
            
        Returns:
            PhaseExecutionResult with artifact and next phase
            
        Raises:
            ConfigurationError: Phase config not found
            PromptBuildError: Failed to build prompt
            LLMError: LLM API call failed
            ParseError: Failed to parse response
            ExecutionError: Unexpected internal error
        """
        logger.info(f"Executing phase {phase_name} for pipeline {pipeline_id}")
        
        try:
            # Step 1: Load configuration
            config = self._config_loader.load_config(phase_name)
            logger.debug(f"Loaded config: role={config.role_name}, artifact={config.artifact_type}")
            
            # Step 2: Build prompt
            try:
                prompt_text, prompt_id = self._prompt_builder.build_prompt(
                    role_name=config.role_name,
                    pipeline_id=pipeline_id,
                    phase=phase_name,
                    epic_context=epic_context,
                    pipeline_state=pipeline_state,
                    artifacts=artifacts
                )
                logger.debug(f"Built prompt using {prompt_id}")
            except ValueError as e:
                raise PromptBuildError(str(e), phase_name, pipeline_id)
            
            # Step 3: Call LLM
            llm_result = self._llm_caller.call(
                system_prompt=prompt_text,
                user_message="Please proceed with this phase."
            )
            
            if not llm_result.success:
                raise LLMError(f"LLM call failed: {llm_result.error}", phase_name, pipeline_id)
            
            logger.debug(f"LLM responded in {llm_result.execution_time_ms}ms")
            
            # Step 4: Parse response
            parse_result = self._parser.parse(llm_result.response_text)
            
            if not parse_result.success:
                error_msg = "; ".join(parse_result.error_messages)
                raise ParseError(f"Parse failed: {error_msg}", phase_name, pipeline_id)
            
            logger.debug(f"Parsed artifact using strategy: {parse_result.strategy_used}")
            
            # Step 5: Record usage (best-effort, non-blocking)
            usage = UsageRecord(
                pipeline_id=pipeline_id,
                prompt_id=prompt_id,
                role_name=config.role_name,
                phase_name=phase_name
            )
            recorded = self._usage_recorder.record_usage(usage)
            if recorded:
                logger.debug("Recorded prompt usage")
            else:
                logger.warning("Failed to record usage (non-fatal)")
            
            # Step 6: Assemble result
            return PhaseExecutionResult(
                success=True,
                artifact=parse_result.data,
                artifact_type=config.artifact_type,
                next_phase=config.next_phase,
                prompt_id=prompt_id,
                llm_response_raw=llm_result.response_text,
                execution_time_ms=llm_result.execution_time_ms,
                error=None
            )
            
        except ConfigurationError as e:
            logger.error(f"Configuration error: {e}")
            raise
        except PromptBuildError as e:
            logger.error(f"Prompt build error: {e}")
            raise
        except LLMError as e:
            logger.error(f"LLM error: {e}")
            raise
        except ParseError as e:
            logger.error(f"Parse error: {e}")
            raise
        except Exception as e:
            # QA Issue #1: Catch-all for unexpected errors
            logger.error(
                f"Unexpected internal error during phase execution: {e}",
                exc_info=True
            )
            raise ExecutionError(
                message=f"Unexpected internal error: {type(e).__name__}: {str(e)}",
                phase_name=phase_name,
                pipeline_id=pipeline_id
            ) from e