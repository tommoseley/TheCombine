"""
Abstract Mentor Base Class with Streaming Support

Each mentor (PM, BA, Developer, QA) extends this and defines their own progress steps.

Dependencies are injected - this class has no direct imports from app.api.
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, Any, List, Optional, Protocol, Callable, Awaitable
from dataclasses import dataclass
import json
import asyncio
import logging
from anthropic import Anthropic

from config import settings
from app.domain.services.llm_response_parser import LLMResponseParser

logger = logging.getLogger(__name__)


# ============================================================================
# PROTOCOLS (Interfaces for dependency injection)
# ============================================================================

class PromptServiceProtocol(Protocol):
    """Interface for prompt service - allows dependency injection"""
    
    async def build_prompt(
        self,
        role_name: str,
        pipeline_id: str,
        phase: str,
        epic_context: str = ""
    ) -> tuple[str, str]:
        """Build system prompt, returns (prompt, prompt_id)"""
        ...
    
    async def get_prompt_by_id(self, prompt_id: str) -> Any:
        """Get prompt record by ID"""
        ...


class ArtifactServiceProtocol(Protocol):
    """Interface for artifact service - allows dependency injection"""
    
    async def create_artifact(
        self,
        artifact_path: str,
        artifact_type: str,
        title: str,
        content: Dict[str, Any],
        breadcrumbs: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Create and save an artifact"""
        ...


# Type alias for ID generator functions
IdGeneratorFunc = Callable[[str], Awaitable[str]]


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class ProgressStep:
    """Represents a single progress step in the mentor workflow"""
    key: str
    message: str
    icon: str
    progress_percent: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.key,
            "message": f"{self.icon} {self.message}",
            "progress": self.progress_percent
        }


# ============================================================================
# STREAMING MENTOR BASE CLASS
# ============================================================================

class StreamingMentor(ABC):
    """
    Abstract base class for all AI mentors with streaming progress updates.
    
    Dependencies are injected via constructor - no direct database or API imports.
    
    Each mentor defines:
    1. Their progress steps
    2. How to build their prompt
    3. How to validate their response
    4. What artifact to create
    """
    
    def __init__(
        self,
        prompt_service: PromptServiceProtocol,
        artifact_service: ArtifactServiceProtocol,
        id_generator: Optional[IdGeneratorFunc] = None,
        model: Optional[str] = None
    ):
        """
        Initialize mentor with injected dependencies.
        
        Args:
            prompt_service: Service for building/retrieving prompts
            artifact_service: Service for creating artifacts
            id_generator: Optional async function for generating IDs
            model: Optional model override (defaults to preferred_model)
        """
        self.prompt_service = prompt_service
        self.artifact_service = artifact_service
        self.id_generator = id_generator
        self.model = model or self.preferred_model
        self.llm_parser = LLMResponseParser()
        self.anthropic_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    
    # ========================================================================
    # Properties
    # ========================================================================

    @property
    def preferred_model(self) -> str:
        """Default model for this mentor. Override in subclasses."""
        return "claude-sonnet-4-20250514"

    # ========================================================================
    # Abstract methods - Each mentor MUST implement these
    # ========================================================================
    
    @property
    @abstractmethod
    def role_name(self) -> str:
        """Return the role name (e.g., 'pm', 'ba', 'developer', 'qa')"""
        pass
    
    @property
    @abstractmethod
    def pipeline_id(self) -> str:
        """Return the pipeline ID (e.g., 'execution', 'refinement')"""
        pass
    
    @property
    @abstractmethod
    def phase_name(self) -> str:
        """Return the phase name (e.g., 'pm_phase', 'ba_phase')"""
        pass
    
    @property
    @abstractmethod
    def progress_steps(self) -> List[ProgressStep]:
        """
        Define the progress steps for this mentor.
        
        Example:
            return [
                ProgressStep("building_prompt", "Reading instructions", "📋", 10),
                ProgressStep("calling_llm", "Analyzing request", "🤖", 30),
                ProgressStep("generating", "Creating epic", "✨", 60),
                ProgressStep("saving", "Saving to database", "💾", 90),
                ProgressStep("complete", "Done!", "🎉", 100)
            ]
        """
        pass
    
    @abstractmethod
    async def build_user_message(self, request_data: Dict[str, Any]) -> str:
        """
        Build the user message for the LLM.
        
        Args:
            request_data: The incoming request data
            
        Returns:
            Formatted user message string
        """
        pass
    
    @abstractmethod
    async def validate_response(
        self, 
        parsed_json: Dict[str, Any], 
        schema: Dict[str, Any]
    ) -> tuple[bool, str]:
        """
        Validate the LLM response.
        
        Args:
            parsed_json: The parsed JSON response
            schema: The expected schema
            
        Returns:
            (is_valid, error_message)
        """
        pass
    
    @abstractmethod
    async def create_artifact(
        self,
        request_data: Dict[str, Any],
        parsed_json: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create the appropriate artifact from the LLM response.
        
        Args:
            request_data: The original request
            parsed_json: The validated LLM response
            metadata: Additional metadata (tokens, timing, etc.)
            
        Returns:
            Dictionary with artifact details (id, path, etc.)
        """
        pass
    
    # ========================================================================
    # Concrete methods - Shared streaming logic
    # ========================================================================
    
    def get_step_by_key(self, key: str) -> ProgressStep:
        """Get a progress step by its key"""
        for step in self.progress_steps:
            if step.key == key:
                return step
        # Return a default if not found
        return ProgressStep(key, "Processing...", "⏳", 50)
    
    async def emit_progress(self, step_key: str, **extra_data) -> str:
        """
        Emit a progress update as Server-Sent Event.
        
        Args:
            step_key: The progress step key
            extra_data: Additional data to include in the event
            
        Returns:
            Formatted SSE string
        """
        step = self.get_step_by_key(step_key)
        data = step.to_dict()
        data.update(extra_data)
        return f"data: {json.dumps(data)}\n\n"
    
    async def stream_execution(
        self,
        request_data: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        """
        Main streaming execution method.
        All mentors use this, with their specific implementations.
        """
        try:
            # Step 1: Build prompt
            yield await self.emit_progress("building_prompt")
            await asyncio.sleep(0.1)  # Give UI time to update
            
            system_prompt, prompt_id = await self.prompt_service.build_prompt(
                role_name=self.role_name,
                pipeline_id=self.pipeline_id,
                phase=self.phase_name,
                epic_context=request_data.get("user_query", "")
            )
            
            # Step 2: Load schema
            yield await self.emit_progress("loading_schema")
            
            prompt_record = await self.prompt_service.get_prompt_by_id(prompt_id)
            if not prompt_record:
                yield await self.emit_progress("error", message="Prompt not found")
                return
            
            schema = prompt_record.expected_schema or {}
            
            # Step 3: Build user message (mentor-specific)
            user_message = await self.build_user_message(request_data)
            
            # Step 4: Call LLM
            yield await self.emit_progress("calling_llm")
            
            model = request_data.get("model", self.model)
            max_tokens = request_data.get("max_tokens", 4096)
            temperature = request_data.get("temperature", 0.7)
            
            # Step 5: Stream generation
            yield await self.emit_progress("generating")
            
            accumulated_text = ""
            
            with self.anthropic_client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}]
            ) as stream:
                for text in stream.text_stream:
                    accumulated_text += text
                    # Send periodic updates during generation
                    if len(accumulated_text) % 100 < len(text):
                        yield await self.emit_progress(
                            "streaming",
                            partial=accumulated_text[:150] + "..." if len(accumulated_text) > 150 else accumulated_text
                        )
            
            # Get final message with usage stats
            final_message = stream.get_final_message()
            input_tokens = final_message.usage.input_tokens
            output_tokens = final_message.usage.output_tokens
            total_tokens = input_tokens + output_tokens
            
            # Step 6: Parse response
            yield await self.emit_progress("parsing")
            
            parse_result = self.llm_parser.parse(accumulated_text)
            parsed_json = parse_result.data if parse_result.success else None
            
            if not parsed_json:
                yield await self.emit_progress(
                    "error",
                    message=f"Failed to parse response: {parse_result.error_message}"
                )
                return
            
            # Step 7: Validate (mentor-specific)
            yield await self.emit_progress("validating")
            
            is_valid, error_message = await self.validate_response(parsed_json, schema)
            
            if not is_valid:
                yield await self.emit_progress(
                    "validation_failed",
                    message=f"⚠️ Validation failed: {error_message}"
                )
                # Continue anyway, but flag it
            
            # Step 8: Save artifact (mentor-specific)
            yield await self.emit_progress("saving")
            
            metadata = {
                "prompt_id": prompt_id,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "model": model,
                "role": self.role_name
            }
            
            artifact_result = await self.create_artifact(
                request_data,
                parsed_json,
                metadata
            )
            
            # Step 9: Complete!
            result = {
                "status": "complete",
                "message": f"🎉 {self.role_name.upper()} task completed!",
                "progress": 100,
                "data": {
                    **artifact_result,
                    "tokens": {
                        "input": input_tokens,
                        "output": output_tokens,
                        "total": total_tokens
                    }
                }
            }
            
            yield f"data: {json.dumps(result)}\n\n"
            
        except Exception as e:
            logger.error(f"{self.role_name} stream error: {e}", exc_info=True)
            yield await self.emit_progress("error", message=f"Error: {str(e)}")