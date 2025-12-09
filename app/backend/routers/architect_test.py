"""
Architect Mentor Test API - Release 1

Test Architect Mentor integration with full transparency.

Endpoints:
- POST /api/architect/preview - Show what will be sent (no API call)
- POST /api/architect/execute - Call LLM and return architecture
- GET /api/architect/health - Health check
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, ValidationError, Field
from typing import List, Literal, Dict, Any, Optional  # ← Add Optional here
from datetime import datetime
import json
import logging

from app.orchestrator_api.services.llm_caller import LLMCaller
from app.orchestrator_api.services.llm_response_parser import LLMResponseParser
from app.orchestrator_api.services.role_prompt_service import RolePromptService
from config import settings

# Import architecture models from common
from app.common.models.architecture_models import ArchitectureDocument

try:
    import anthropic
except ImportError:
    anthropic = None

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/architect", tags=["Architect Mentor Test"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class ArchitectTestRequest(BaseModel):
    """Request to test Architect Mentor - requires PM Epic as input"""
    pm_epic: Dict[str, Any]  # The complete PM Epic JSON
    
    class Config:
        json_schema_extra = {
            "example": {
                "pm_epic": {
                    "project_name": "calculator-cli",
                    "epic_id": "CALC-100",
                    "epic_summary": {
                        "title": "Command Line Calculator",
                        "refined_description": "A CLI tool for numeric addition",
                        "business_value": "Enable script automation",
                        "primary_users": ["developers"],
                        "success_metrics": ["Correct calculations"]
                    },
                    "goals": ["Accept numeric input", "Return JSON"],
                    "stories": []
                }
            }
        }

class ArchitectPreviewResponse(BaseModel):
    """Preview of what will be sent to Architect Mentor"""
    system_prompt: str
    user_message: str
    expected_schema: Dict[str, Any]
    model: str
    max_tokens: int
    temperature: float
    estimated_input_tokens: int


class ValidationResult(BaseModel):
    """Result of Pydantic validation"""
    valid: bool
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    validation_errors: Optional[List[Dict[str, Any]]] = None
    validated_data: Optional[Dict[str, Any]] = None


class ArchitectExecuteResponse(BaseModel):
    """Result of actually calling Architect Mentor"""
    system_prompt: str
    user_message: str
    expected_schema: Dict[str, Any]
    model: str
    
    raw_response: str
    parsed_json: Optional[Dict[str, Any]]
    validation_result: ValidationResult
    
    input_tokens: int
    output_tokens: int
    total_tokens: int
    execution_time_ms: int
    timestamp: str
    prompt_id: str


# ============================================================================
# DEPENDENCIES
# ============================================================================

def get_llm_caller() -> LLMCaller:
    """Get LLM caller instance with Anthropic client"""
    if anthropic is None:
        raise HTTPException(500, "anthropic package not installed")
    
    api_key = settings.ANTHROPIC_API_KEY
    if not api_key or api_key == "false":
        raise HTTPException(500, "WORKBENCH_ANTHROPIC_API_KEY not configured")
    
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
    """Rough token estimate (~4 chars per token)"""
    return len(text) // 4


def validate_architecture(data: Dict[str, Any]) -> ValidationResult:
    """
    Validate parsed data against ArchitectureDocument.
    
    NOTE: Uses hardcoded Pydantic model for validation.
    Schema displayed to users comes from database (single source of truth).
    
    TODO (Release 3+): Generate Pydantic model dynamically from database schema.
    """
    try:
        arch = ArchitectureDocument(**data)
        return ValidationResult(
            valid=True,
            validated_data=arch.model_dump()
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

@router.post("/preview", response_model=ArchitectPreviewResponse)
async def preview_architect_request(
    request: ArchitectTestRequest,
    prompt_service: RolePromptService = Depends(get_role_prompt_service)
) -> ArchitectPreviewResponse:
    """
    Preview what will be sent to Architect Mentor WITHOUT calling the LLM.
    Shows the system prompt, user message with PM Epic, and expected schema.
    """
    try:
        # Build Architect prompt from database
        system_prompt, prompt_id = prompt_service.build_prompt(
            role_name="architect",
            pipeline_id="preview",
            phase="arch_phase",
            epic_context=None,  # Not used for Architect
            pipeline_state=None,
            artifacts=None
        )
        
        # Get schema from database
        from app.orchestrator_api.persistence.repositories.role_prompt_repository import RolePromptRepository
        prompt_repo = RolePromptRepository()
        prompt_record = prompt_repo.get_by_id(prompt_id)
        
        if not prompt_record:
            raise HTTPException(404, f"Prompt not found: {prompt_id}")
        
        schema = prompt_record.working_schema or {}
        
        # Build user message with PM Epic
        user_message = f"""Transform the following PM Epic into a complete architectural specification:

{json.dumps(request.pm_epic, indent=2)}

Output ONLY valid JSON matching the architecture schema. No markdown, no prose."""
        
        estimated_tokens = estimate_tokens(system_prompt + user_message)
        
        return ArchitectPreviewResponse(
            system_prompt=system_prompt,
            user_message=user_message,
            expected_schema=schema,
            model="claude-sonnet-4-20250514",
            max_tokens=8192,  # Larger for architecture
            temperature=0.7,
            estimated_input_tokens=estimated_tokens
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error previewing Architect request: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to preview request: {str(e)}")


@router.post("/execute", response_model=ArchitectExecuteResponse)
async def execute_architect_request(
    request: ArchitectTestRequest,
    prompt_service: RolePromptService = Depends(get_role_prompt_service),
    llm_caller: LLMCaller = Depends(get_llm_caller),
    llm_parser: LLMResponseParser = Depends(get_llm_parser)
) -> ArchitectExecuteResponse:
    """
    Actually execute Architect Mentor request with Anthropic API.
    This COSTS MONEY - each call uses API tokens.
    """
    try:
        # Build Architect prompt
        system_prompt, prompt_id = prompt_service.build_prompt(
            role_name="architect",
            pipeline_id="test_execution",
            phase="arch_phase"
        )
        
        # Get schema from database
        from app.orchestrator_api.persistence.repositories.role_prompt_repository import RolePromptRepository
        prompt_repo = RolePromptRepository()
        prompt_record = prompt_repo.get_by_id(prompt_id)
        
        if not prompt_record:
            raise HTTPException(404, f"Prompt not found: {prompt_id}")
        
        schema = prompt_record.working_schema or {}
        
        # Build user message
        user_message = f"""Transform the following PM Epic into a complete architectural specification:

{json.dumps(request.pm_epic, indent=2)}

Output ONLY valid JSON matching the architecture schema. No markdown, no prose."""
        
        # Call LLM
        logger.info("Calling Anthropic API for Architect request")
        
        llm_result = llm_caller.call(
            system_prompt=system_prompt,
            user_message=user_message,
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            temperature=0.7
        )
        
        if not llm_result.success:
            raise HTTPException(500, f"LLM call failed: {llm_result.error}")
        
        raw_response = llm_result.response_text
        input_tokens = llm_result.token_usage["input_tokens"]
        output_tokens = llm_result.token_usage["output_tokens"]
        total_tokens = input_tokens + output_tokens
        execution_time_ms = llm_result.execution_time_ms
        
        # Parse JSON
        parse_result = llm_parser.parse(raw_response)
        parsed_json = parse_result.data if parse_result.success else None
        
        # Validate
        if parsed_json:
            validation_result = validate_architecture(parsed_json)
        else:
            validation_result = ValidationResult(
                valid=False,
                error_type="json_parse_error",
                error_message="Failed to parse JSON from LLM response",
                validation_errors=[
                    {"error": msg} for msg in parse_result.error_messages
                ]
            )
        
        return ArchitectExecuteResponse(
            system_prompt=system_prompt,
            user_message=user_message,
            expected_schema=schema,
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
        logger.error(f"Error executing Architect request: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to execute request: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "architect_test"}