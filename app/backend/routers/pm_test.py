"""
PM Mentor Test API - Release 1

New router for testing PM Mentor integration with full transparency.
Lives in existing orchestrator app.

Endpoints:
- POST /api/pm/preview - Show what will be sent to LLM (no API call)
- POST /api/pm/execute - Actually call LLM and return results
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, ValidationError, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import logging

# Use the actual LLM adapter components
from app.orchestrator_api.services.llm_caller import LLMCaller
from app.orchestrator_api.services.llm_response_parser import LLMResponseParser
from app.orchestrator_api.services.role_prompt_service import RolePromptService
from config import settings

# Import Epic models from common
from app.common.models.epic_models import EpicSchema

try:
    import anthropic
except ImportError:
    anthropic = None

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pm", tags=["PM Mentor Test"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class PMTestRequest(BaseModel):
    """Request to test PM Mentor"""
    user_query: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_query": "I want to build a user authentication system with email/password login and password reset."
            }
        }


class PMPreviewResponse(BaseModel):
    """Preview of what will be sent to LLM (no actual API call)"""
    system_prompt: str
    user_message: str
    expected_schema: Dict[str, Any]
    model: str
    max_tokens: int
    temperature: float
    estimated_input_tokens: int  # Rough estimate


class ValidationResult(BaseModel):
    """Result of Pydantic validation"""
    valid: bool
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    validation_errors: Optional[List[Dict[str, Any]]] = None
    validated_data: Optional[Dict[str, Any]] = None


class PMExecuteResponse(BaseModel):
    """Result of actually calling LLM"""
    # What was sent
    system_prompt: str
    user_message: str
    expected_schema: Dict[str, Any]
    model: str
    
    # What came back
    raw_response: str
    parsed_json: Optional[Dict[str, Any]]
    validation_result: ValidationResult
    
    # Metadata
    input_tokens: int
    output_tokens: int
    total_tokens: int
    execution_time_ms: int
    timestamp: str
    prompt_id: str  # Which prompt was used from DB


# ============================================================================
# DEPENDENCIES
# ============================================================================

def get_llm_caller() -> LLMCaller:
    """Get LLM caller instance with Anthropic client"""
    if anthropic is None:
        raise HTTPException(500, "anthropic package not installed")
    
    api_key = settings.ANTHROPIC_API_KEY
    if not api_key or api_key == "false":
        raise HTTPException(
            500, 
            "WORKBENCH_ANTHROPIC_API_KEY not configured in .env"
        )
    
    client = anthropic.Anthropic(api_key=api_key)
    return LLMCaller(client)


def get_llm_parser() -> LLMResponseParser:
    """Get LLM response parser instance"""
    return LLMResponseParser()


def get_role_prompt_service() -> RolePromptService:
    """Get role prompt service instance"""
    return RolePromptService()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def estimate_tokens(text: str) -> int:
    """
    Rough token estimate (Claude uses ~4 chars per token).
    This is NOT accurate but gives a ballpark.
    """
    return len(text) // 4


def validate_epic(data: Dict[str, Any]) -> ValidationResult:
    """
    Validate parsed data against EpicSchema.
    
    NOTE: This uses a hardcoded Pydantic model for validation.
    The schema displayed to users comes from the database (single source of truth).
    
    TODO (Release 3+): Generate Pydantic model dynamically from database schema
    to eliminate this duplication. For now, manually keep EpicSchema in sync
    with role_prompts.working_schema in the database.
    
    Returns:
        ValidationResult with details
    """
    try:
        epic = EpicSchema(**data)
        return ValidationResult(
            valid=True,
            validated_data=epic.model_dump()
        )
    except ValidationError as ve:
        errors = json.loads(ve.json())
        return ValidationResult(
            valid=False,
            error_type="validation_error",
            error_message="Pydantic validation failed",
            validation_errors=errors
        )
    except Exception as e:
        return ValidationResult(
            valid=False,
            error_type="unexpected_error",
            error_message=str(e),
            validation_errors=None
        )


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/preview", response_model=PMPreviewResponse)
async def preview_pm_request(
    request: PMTestRequest,
    prompt_service: RolePromptService = Depends(get_role_prompt_service)
) -> PMPreviewResponse:
    """
    Preview what will be sent to PM Mentor WITHOUT calling the LLM.
    
    Shows:
    - The system prompt from database (built from parts)
    - The formatted user message
    - The expected schema (from database)
    - Token estimates
    
    Use this to validate prompt construction before burning tokens.
    """
    try:
        # Build PM prompt from database using service
        # For now, minimal context - just the user query as epic_context
        system_prompt, prompt_id = prompt_service.build_prompt(
            role_name="pm",
            pipeline_id="preview",  # Dummy ID for preview
            phase="pm_phase",
            epic_context=request.user_query,
            pipeline_state=None,
            artifacts=None
        )
        
        # Get the prompt record to access working_schema
        from app.orchestrator_api.persistence.repositories.role_prompt_repository import RolePromptRepository
        prompt_repo = RolePromptRepository()
        prompt_record = prompt_repo.get_by_id(prompt_id)
        
        if not prompt_record:
            raise HTTPException(404, f"Prompt not found: {prompt_id}")
        
        # Get schema from database (single source of truth)
        schema = prompt_record.working_schema or {}
        
        # Build user message
        user_message = f"""Create an Epic definition for the following user request:

{request.user_query}

Remember: Output ONLY valid JSON matching the schema. No markdown, no prose."""
        
        # Estimate tokens
        combined_text = system_prompt + user_message
        estimated_tokens = estimate_tokens(combined_text)
        
        return PMPreviewResponse(
            system_prompt=system_prompt,
            user_message=user_message,
            expected_schema=schema,  # From database, not generated
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            temperature=0.7,
            estimated_input_tokens=estimated_tokens
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error previewing PM request: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to preview request: {str(e)}")


@router.post("/execute", response_model=PMExecuteResponse)
async def execute_pm_request(
    request: PMTestRequest,
    prompt_service: RolePromptService = Depends(get_role_prompt_service),
    llm_caller: LLMCaller = Depends(get_llm_caller),
    llm_parser: LLMResponseParser = Depends(get_llm_parser)
) -> PMExecuteResponse:
    """
    Actually execute PM Mentor request with Anthropic API.
    
    Shows:
    - Everything from preview
    - Raw LLM response
    - Parsed JSON (if parseable)
    - Validation results
    - Actual token usage
    - Execution time
    
    This COSTS MONEY - each call uses API tokens.
    """
    try:
        # Build PM prompt from database using service
        system_prompt, prompt_id = prompt_service.build_prompt(
            role_name="pm",
            pipeline_id="test_execution",  # Dummy ID for testing
            phase="pm_phase",
            epic_context=request.user_query,
            pipeline_state=None,
            artifacts=None
        )
        
        # Get the prompt record to access working_schema
        from app.orchestrator_api.persistence.repositories.role_prompt_repository import RolePromptRepository
        prompt_repo = RolePromptRepository()
        prompt_record = prompt_repo.get_by_id(prompt_id)
        
        if not prompt_record:
            raise HTTPException(404, f"Prompt not found: {prompt_id}")
        
        # Get schema from database (single source of truth)
        schema = prompt_record.working_schema or {}
        
        # Build user message (same as preview)
        user_message = f"""Create an Epic definition for the following user request:

{request.user_query}

Remember: Output ONLY valid JSON matching the schema. No markdown, no prose."""
        
        # Call LLM using LLMCaller
        logger.info(f"Calling Anthropic API for PM request")
        
        llm_result = llm_caller.call(
            system_prompt=system_prompt,
            user_message=user_message,
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            temperature=0.7
        )
        
        # Check if LLM call succeeded
        if not llm_result.success:
            raise HTTPException(500, f"LLM call failed: {llm_result.error}")
        
        raw_response = llm_result.response_text
        input_tokens = llm_result.token_usage["input_tokens"]
        output_tokens = llm_result.token_usage["output_tokens"]
        total_tokens = input_tokens + output_tokens
        execution_time_ms = llm_result.execution_time_ms
        
        # Parse JSON using LLMResponseParser
        parse_result = llm_parser.parse(raw_response)
        
        parsed_json = parse_result.data if parse_result.success else None
        
        # Validate using Pydantic (still hardcoded for now, but displayed schema is from DB)
        if parsed_json:
            validation_result = validate_epic(parsed_json)
        else:
            # Parse failed
            validation_result = ValidationResult(
                valid=False,
                error_type="json_parse_error",
                error_message="Failed to parse JSON from LLM response",
                validation_errors=[
                    {"error": msg} for msg in parse_result.error_messages
                ]
            )
        
        return PMExecuteResponse(
            system_prompt=system_prompt,
            user_message=user_message,
            expected_schema=schema,  # From database, not generated
            model="claude-sonnet-4-20250514",
            raw_response=raw_response,
            parsed_json=parsed_json,
            validation_result=validation_result,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            execution_time_ms=execution_time_ms,
            timestamp=datetime.utcnow().isoformat(),
            prompt_id=prompt_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing PM request: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to execute request: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check for PM test endpoints"""
    return {
        "status": "ok",
        "service": "PM Mentor Test API",
        "release": "R1"
    }