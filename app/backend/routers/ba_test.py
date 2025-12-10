"""
BA Mentor Test API - Release 1

Test BA Mentor integration with full transparency.

Endpoints:
- POST /api/ba/preview - Show what will be sent (no API call)
- POST /api/ba/execute - Call LLM and return BA stories
- GET /api/ba/health - Health check
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, ValidationError, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import logging

from app.orchestrator_api.services.llm_caller import LLMCaller
from app.orchestrator_api.services.llm_response_parser import LLMResponseParser
from app.orchestrator_api.services.role_prompt_service import RolePromptService
from config import settings

# Import models from common
from app.common.models.epic_models import EpicSchema
from app.common.models.architecture_models import ArchitectureDocument
from app.common.models.ba_models import BAStorySet

try:
    import anthropic
except ImportError:
    anthropic = None

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ba", tags=["BA Mentor Test"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class BATestRequest(BaseModel):
    """Request to test BA Mentor - requires both PM Epic and Architecture"""
    pm_epic: Dict[str, Any] = Field(..., description="Complete PM Epic from PM Mentor")
    architecture: Dict[str, Any] = Field(..., description="Complete Architecture from Architect Mentor")
    
    class Config:
        json_schema_extra = {
            "example": {
                "pm_epic": {
                    "project_name": "Auth System",
                    "epic_id": "AUTH-001",
                    "goals": ["Secure user authentication"],
                    "stories": []
                },
                "architecture": {
                    "project_name": "Auth System",
                    "epic_id": "AUTH-001",
                    "components": []
                }
            }
        }


class BAPreviewResponse(BaseModel):
    """Preview of what will be sent to BA Mentor"""
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


class BAExecuteResponse(BaseModel):
    """Result of actually calling BA Mentor"""
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


def validate_ba_stories(data: Dict[str, Any]) -> ValidationResult:
    """
    Validate parsed data against BAStorySet.
    
    NOTE: Uses hardcoded Pydantic model for validation.
    Schema displayed to users comes from database (single source of truth).
    
    TODO (Release 3+): Generate Pydantic model dynamically from database schema.
    """
    try:
        ba_story_set = BAStorySet(**data)
        return ValidationResult(
            valid=True,
            validated_data=ba_story_set.model_dump()
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

@router.get("/health")
async def health_check():
    """Health check for BA Mentor API"""
    return {
        "status": "healthy",
        "service": "BA Mentor Test API",
        "version": "1.0",
        "anthropic_available": anthropic is not None,
        "api_key_configured": bool(settings.ANTHROPIC_API_KEY and settings.ANTHROPIC_API_KEY != "false")
    }


@router.post("/preview", response_model=BAPreviewResponse)
async def preview_ba_request(
    request: BATestRequest,
    role_prompt_service: RolePromptService = Depends(get_role_prompt_service)
):
    """
    Preview what will be sent to BA Mentor (no actual LLM call).
    
    Shows the exact prompt, schema, and configuration that would be used.
    Useful for debugging and understanding BA Mentor behavior.
    """
    try:
        # Build BA Mentor prompt from database
        system_prompt, prompt_id = role_prompt_service.build_prompt(
            role_name="ba",
            pipeline_id="preview",
            phase="ba_phase",
            epic_context=None,  # Not used for BA
            pipeline_state=None,
            artifacts=None
        )
        
        # Get schema from database
        from app.orchestrator_api.persistence.repositories.role_prompt_repository import RolePromptRepository
        prompt_repo = RolePromptRepository()
        prompt_record = prompt_repo.get_by_id(prompt_id)
        
        if not prompt_record:
            raise HTTPException(404, f"Prompt not found: {prompt_id}")
        
        schema = prompt_record.expected_schema or {}
        
        # Construct user message with both PM Epic and Architecture
        user_message = f"""Please analyze this PM Epic and Architecture to generate implementation-ready BA stories.

PM EPIC:
{json.dumps(request.pm_epic, indent=2)}

ARCHITECTURE:
{json.dumps(request.architecture, indent=2)}

Generate BA stories that:
1. Map PM stories to specific architectural components
2. Include detailed, testable acceptance criteria
3. Reference both PM story IDs and architecture component IDs
4. Are atomic and implementable by developers

Output ONLY valid JSON matching the BA Story Set schema."""
        
        estimated_tokens = estimate_tokens(system_prompt + user_message)
        
        return BAPreviewResponse(
            system_prompt=system_prompt,
            user_message=user_message,
            expected_schema=schema,
            model="claude-sonnet-4-20250514",
            max_tokens=16384,
            temperature=1.0,
            estimated_input_tokens=estimated_tokens
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Preview failed: {e}", exc_info=True)
        raise HTTPException(500, f"Preview failed: {str(e)}")


@router.post("/execute", response_model=BAExecuteResponse)
async def execute_ba_request(
    request: BATestRequest,
    llm_caller: LLMCaller = Depends(get_llm_caller),
    llm_parser: LLMResponseParser = Depends(get_llm_parser),
    role_prompt_service: RolePromptService = Depends(get_role_prompt_service)
):
    """
    Execute BA Mentor request with full transparency.
    
    1. Fetches BA Mentor prompt from database
    2. Constructs user message with PM Epic + Architecture
    3. Calls Claude API
    4. Parses JSON response
    5. Validates against BAStorySet schema
    6. Returns everything (prompt, response, validation)
    """
    start_time = datetime.now()
    
    try:
        # Build BA Mentor prompt from database
        system_prompt, prompt_id = role_prompt_service.build_prompt(
            role_name="ba",
            pipeline_id="execute",
            phase="ba_phase",
            epic_context=None,
            pipeline_state=None,
            artifacts=None
        )
        
        # Get schema from database
        from app.orchestrator_api.persistence.repositories.role_prompt_repository import RolePromptRepository
        prompt_repo = RolePromptRepository()
        prompt_record = prompt_repo.get_by_id(prompt_id)
        
        if not prompt_record:
            raise HTTPException(404, f"Prompt not found: {prompt_id}")
        
        schema = prompt_record.expected_schema or {}
        
        # Construct user message with both inputs
        user_message = f"""Please analyze this PM Epic and Architecture to generate implementation-ready BA stories.

PM EPIC:
{json.dumps(request.pm_epic, indent=2)}

ARCHITECTURE:
{json.dumps(request.architecture, indent=2)}

Generate BA stories that:
1. Map PM stories to specific architectural components
2. Include detailed, testable acceptance criteria
3. Reference both PM story IDs and architecture component IDs
4. Are atomic and implementable by developers

Output ONLY valid JSON matching the BA Story Set schema."""
        
        # Call LLM
        logger.info(f"Calling BA Mentor with {estimate_tokens(system_prompt + user_message)} estimated tokens")
        
        llm_result = llm_caller.call(
            system_prompt=system_prompt,
            user_message=user_message,
            model="claude-sonnet-4-20250514",
            max_tokens=16384,
            temperature=1.0
        )
        
        # Check if LLM call succeeded
        if not llm_result.success:
            raise HTTPException(500, f"LLM call failed: {llm_result.error}")
        
        raw_response = llm_result.response_text
        input_tokens = llm_result.token_usage["input_tokens"]
        output_tokens = llm_result.token_usage["output_tokens"]
        total_tokens = input_tokens + output_tokens
        
        # Parse JSON using LLMResponseParser
        parse_result = llm_parser.parse(raw_response)
        parsed_json = parse_result.data if parse_result.success else None
        
        # Validate
        if parsed_json:
            validation_result = validate_ba_stories(parsed_json)
        else:
            validation_result = ValidationResult(
                valid=False,
                error_type="parse_error",
                error_message="Failed to parse JSON from LLM response",
                validation_errors=None
            )
        
        # Calculate execution time
        execution_time_ms = llm_result.execution_time_ms
        
        return BAExecuteResponse(
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
            timestamp=datetime.now().isoformat(),
            prompt_id=prompt_id
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"BA Mentor execution failed: {e}", exc_info=True)
        raise HTTPException(500, f"Execution failed: {str(e)}")