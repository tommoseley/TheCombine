"""
Abstract Mentor Base Class with Streaming Support

Each mentor (PM, BA, Developer, QA) extends this and defines their own specifics.
Common functionality is maximized here.

Dependencies are injected - this class has no direct imports from app.api.
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, Any, List, Optional, Protocol, Callable, Awaitable
from dataclasses import dataclass
import json
import asyncio
import logging
import jsonschema
from anthropic import Anthropic
import httpx

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
        task_name: str,
        pipeline_id: str = None,
        phase: str = None,
        epic_context: str = ""
    ) -> tuple[str, str]:
        """Build system prompt, returns (prompt, task_id)"""
        ...
    
    async def get_prompt_by_id(self, task_id: str) -> Any:
        """Get task record by ID"""
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
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProgressStep":
        """Create ProgressStep from dictionary (for DB loading)"""
        return cls(
            key=data.get("key", "unknown"),
            message=data.get("message", "Processing..."),
            icon=data.get("icon", "⏳"),
            progress_percent=data.get("progress", 50)
        )


# ============================================================================
# DEFAULT PROGRESS STEPS
# ============================================================================

DEFAULT_PROGRESS_STEPS = [
    ProgressStep("building_prompt", "Reading instructions", "📋", 10),
    ProgressStep("loading_schema", "Loading schema", "📄", 15),
    ProgressStep("calling_llm", "Analyzing request", "🤖", 25),
    ProgressStep("generating", "Generating content", "✨", 45),
    ProgressStep("streaming", "Processing response", "💭", 65),
    ProgressStep("parsing", "Parsing response", "🔧", 80),
    ProgressStep("validating", "Validating output", "✅", 88),
    ProgressStep("saving", "Saving artifact", "💾", 95),
    ProgressStep("complete", "Complete!", "🎉", 100),
    ProgressStep("error", "Something went wrong", "❌", 0),
    ProgressStep("validation_failed", "Validation issues detected", "⚠️", 88)
]


# ============================================================================
# VALIDATION HELPERS
# ============================================================================

def validate_with_json_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> tuple[bool, str]:
    """
    Validate data against JSON Schema.
    
    Args:
        data: The data to validate
        schema: JSON Schema to validate against
        
    Returns:
        (is_valid, error_message)
    """
    if not schema:
        # No schema defined, skip validation
        return True, ""
    
    try:
        jsonschema.validate(instance=data, schema=schema)
        return True, ""
    except jsonschema.ValidationError as e:
        return False, f"Schema validation failed: {e.message}"
    except jsonschema.SchemaError as e:
        logger.warning(f"Invalid schema: {e.message}")
        return True, ""  # Don't fail on bad schema, just warn


def validate_required_fields(
    data: Dict[str, Any], 
    required_fields: List[str]
) -> tuple[bool, str]:
    """
    Simple validation for required top-level fields.
    
    Args:
        data: The data to validate
        required_fields: List of field names that must exist
        
    Returns:
        (is_valid, error_message)
    """
    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: '{field}'"
        if data[field] is None:
            return False, f"Field '{field}' cannot be null"
    return True, ""


def validate_non_empty_array(
    data: Dict[str, Any], 
    field_name: str
) -> tuple[bool, str]:
    """
    Validate that a field is a non-empty array.
    
    Args:
        data: The data containing the field
        field_name: Name of the array field
        
    Returns:
        (is_valid, error_message)
    """
    if field_name not in data:
        return False, f"Missing required field: '{field_name}'"
    
    value = data[field_name]
    if not isinstance(value, list):
        return False, f"Field '{field_name}' must be an array"
    
    if len(value) == 0:
        return False, f"Field '{field_name}' cannot be empty"
    
    return True, ""


# ============================================================================
# STREAMING MENTOR BASE CLASS
# ============================================================================

class StreamingMentor(ABC):
    """
    Abstract base class for all AI mentors with streaming progress updates.
    
    Dependencies are injected via constructor - no direct database or API imports.
    
    Each mentor defines:
    1. Their role name (for prompt lookup)
    2. Their task name (for prompt lookup)
    3. How to build their user message
    4. What validation rules to apply
    5. What artifact(s) to create
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
        self.anthropic_client = Anthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            timeout=httpx.Timeout(300.0, connect=10.0)
        )
        self._progress_steps: Optional[List[ProgressStep]] = None

    # ========================================================================
    # Properties with sensible defaults
    # ========================================================================

    @property
    def preferred_model(self) -> str:
        """Default model for this mentor. Override in subclasses if needed."""
        return "claude-sonnet-4-20250514"

    @property
    def pipeline_id(self) -> str:
        """Pipeline ID - same for all execution mentors."""
        return "execution"
    
    @property
    def phase_name(self) -> str:
        """Phase name - derived from role_name by default."""
        return f"{self.role_name}_phase"
    
    @property
    def artifact_type(self) -> str:
        """Artifact type - derived from role_name by default. Override if different."""
        # Map common roles to artifact types
        role_to_type = {
            "pm": "epic",
            "architect": "architecture",
            "ba": "story",
            "developer": "code",
            "qa": "test"
        }
        return role_to_type.get(self.role_name, self.role_name)

    @property
    def progress_steps(self) -> List[ProgressStep]:
        """
        Progress steps for this mentor.
        
        Can be overridden by subclass or loaded from DB.
        Falls back to DEFAULT_PROGRESS_STEPS.
        """
        if self._progress_steps:
            return self._progress_steps
        return DEFAULT_PROGRESS_STEPS
    
    def set_progress_steps(self, steps: List[Dict[str, Any]]) -> None:
        """
        Set progress steps from a list of dicts (e.g., from DB JSON).
        
        Args:
            steps: List of step dictionaries with key, message, icon, progress
        """
        self._progress_steps = [ProgressStep.from_dict(s) for s in steps]

    # ========================================================================
    # Abstract methods - Each mentor MUST implement these
    # ========================================================================
    
    @property
    @abstractmethod
    def role_name(self) -> str:
        """Return the role name (e.g., 'pm', 'ba', 'architect', 'developer')"""
        pass
    
    @property
    @abstractmethod
    def task_name(self) -> str:
        """Return the task name (e.g., 'preliminary', 'final', 'epic_creation')"""
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
    
    # ========================================================================
    # Optional overrides - Defaults provided
    # ========================================================================
    
    async def validate_response(
        self, 
        parsed_json: Dict[str, Any], 
        schema: Dict[str, Any]
    ) -> tuple[bool, str]:
        """
        Validate the LLM response.
        
        Default: Use JSON Schema validation if schema provided.
        Override for custom validation logic.
        
        Args:
            parsed_json: The parsed JSON response
            schema: The expected schema from role_tasks
            
        Returns:
            (is_valid, error_message)
        """
        return validate_with_json_schema(parsed_json, schema)
    
    async def extract_title(
        self, 
        parsed_json: Dict[str, Any], 
        request_data: Dict[str, Any]
    ) -> str:
        """
        Extract title for the artifact.
        
        Default: Look for common title fields.
        Override for custom title extraction.
        """
        # Try common title locations
        if "title" in parsed_json:
            return parsed_json["title"]
        if "architecture_summary" in parsed_json:
            return parsed_json["architecture_summary"].get("title", "Architecture")
        if "preliminary_summary" in parsed_json:
            return parsed_json["preliminary_summary"].get("problem_understanding", "Preliminary Architecture")[:100]
        if "epic_title" in parsed_json:
            return parsed_json["epic_title"]
        
        # Fallback
        return f"{self.role_name.upper()} Output"
    
    async def build_artifact_path(self, request_data: Dict[str, Any]) -> str:
        """
        Build the artifact path.
        
        Default: Use epic_artifact_path or construct from project_id.
        Override for custom path logic.
        """
        # Try common path sources
        if "epic_artifact_path" in request_data:
            return request_data["epic_artifact_path"]
        if "artifact_path" in request_data:
            return request_data["artifact_path"]
        if "project_id" in request_data:
            project_id = request_data["project_id"]
            if self.id_generator:
                item_id = await self.id_generator(project_id)
                return f"{project_id}/{item_id}"
            return f"{project_id}/UNKNOWN"
        
        raise ValueError("Cannot determine artifact path from request data")
    
    async def create_artifact(
        self,
        request_data: Dict[str, Any],
        parsed_json: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create artifact from the LLM response.
        
        Default: Create a single artifact.
        Override for custom artifact creation (e.g., multiple artifacts).
        
        Args:
            request_data: The original request
            parsed_json: The validated LLM response
            metadata: Additional metadata (tokens, timing, etc.)
            
        Returns:
            Dictionary with artifact details
        """
        artifact_path = await self.build_artifact_path(request_data)
        title = await self.extract_title(parsed_json, request_data)
        
        # Extract project_id from path
        path_parts = artifact_path.split("/")
        project_id = path_parts[0] if path_parts else "UNKNOWN"
        
        # Create breadcrumbs
        breadcrumbs = {
            "created_by": f"{self.role_name}_mentor",
            "task": self.task_name,
            "source_path": artifact_path,
            **metadata
        }
        
        artifact = await self.artifact_service.create_artifact(
            artifact_path=artifact_path,
            artifact_type=self.artifact_type,
            title=title,
            content=parsed_json,
            breadcrumbs=breadcrumbs
        )
        
        return {
            "artifact_path": artifact_path,
            "artifact_id": str(artifact.id),
            "project_id": project_id,
            "title": title,
            "artifact_type": self.artifact_type
        }
    
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
        All mentors use this shared implementation.
        """
        try:
            # Step 1: Build prompt
            yield await self.emit_progress("building_prompt")
            await asyncio.sleep(0.1)
            
            system_prompt, task_id = await self.prompt_service.build_prompt(
                role_name=self.role_name,
                task_name=self.task_name,
                epic_context=request_data.get("user_query", "")
            )
            
            # Step 2: Load schema
            yield await self.emit_progress("loading_schema")
            
            prompt_record = await self.prompt_service.get_prompt_by_id(task_id)
            if not prompt_record:
                yield await self.emit_progress("error", message="Prompt not found")
                return
            
            schema = prompt_record.expected_schema or {}
            
            # Load progress steps from prompt if available
            if prompt_record.progress_steps:
                self.set_progress_steps(prompt_record.progress_steps)
            
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
            
            logger.debug(f"Raw LLM response (first 500 chars): {accumulated_text[:500]}")
            logger.debug(f"Raw LLM response (last 500 chars): {accumulated_text[-500:]}")

            # Step 6: Parse response
            yield await self.emit_progress("parsing")
            
            parse_result = self.llm_parser.parse(accumulated_text)
            parsed_json = parse_result.data if parse_result.success else None
            
            if not parsed_json:
                yield await self.emit_progress(
                    "error",
                    message=f"Failed to parse response: {parse_result.error_messages}"
                )
                return
            
            # Step 7: Validate (uses default or overridden method)
            yield await self.emit_progress("validating")
            
            is_valid, error_message = await self.validate_response(parsed_json, schema)
            
            if not is_valid:
                yield await self.emit_progress(
                    "validation_failed",
                    message=f"⚠️ Validation failed: {error_message}"
                )
                # Continue anyway, but flag it
            
            # Step 8: Save artifact (uses default or overridden method)
            yield await self.emit_progress("saving")
            
            metadata = {
                "task_id": task_id,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "model": model,
                "role": self.role_name,
                "task": self.task_name
            }
            
            artifact_result = await self.create_artifact(
                request_data,
                parsed_json,
                metadata
            )
            
            # Step 9: Complete!
            result = {
                "status": "complete",
                "message": f"🎉 {self.role_name.upper()} {self.task_name} completed!",
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
            logger.error(f"{self.role_name} {self.task_name} stream error: {e}", exc_info=True)
            yield await self.emit_progress("error", message=f"Error: {str(e)}")