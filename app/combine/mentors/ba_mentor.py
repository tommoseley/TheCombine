"""
BA Mentor - Release 1

BA Mentor that transforms Epic + Architecture into User Stories as artifacts.

Endpoints:
- POST /api/ba/preview - Show what will be sent (no API call)
- POST /api/ba/execute - Call LLM and return story artifacts
- GET /api/ba/health - Health check
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, ValidationError, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import json
import logging

from app.combine.services.llm_caller import LLMCaller
from app.combine.services.llm_response_parser import LLMResponseParser
from app.combine.services.role_prompt_service import RolePromptService
from app.combine.services.artifact_service import ArtifactService
from app.combine.models import Artifact
from app.combine.persistence.repositories.role_prompt_repository import RolePromptRepository
from database import get_db
from config import settings

try:
    import anthropic
except ImportError:
    anthropic = None

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ba", tags=["BA Mentor"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class BARequest(BaseModel):
    """Request to BA Mentor - requires both Epic and Architecture artifacts"""
    epic_artifact_path: str = Field(..., description="RSP-1 path to Epic (e.g., 'PROJ/E001')")
    architecture_artifact_path: str = Field(..., description="RSP-1 path to Architecture (e.g., 'PROJ/E001/ARCH')")


class BAPreviewResponse(BaseModel):
    """Preview of what will be sent to BA Mentor"""
    epic_artifact_path: str
    architecture_artifact_path: str
    epic_content: Dict[str, Any]
    architecture_content: Dict[str, Any]
    system_prompt: str
    user_message: str
    expected_schema: Dict[str, Any]
    model: str
    max_tokens: int
    temperature: float
    estimated_input_tokens: int


class ValidationResult(BaseModel):
    """Result of schema validation"""
    valid: bool
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    validation_errors: Optional[List[Dict[str, Any]]] = None
    validated_data: Optional[Dict[str, Any]] = None


class StoryArtifact(BaseModel):
    """Individual story artifact created"""
    artifact_path: str
    artifact_id: str
    title: str


class BAExecuteResponse(BaseModel):
    """Result of actually calling BA Mentor"""
    epic_artifact_path: str
    architecture_artifact_path: str
    stories_created: List[StoryArtifact]
    
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


def validate_ba_schema(data: Dict[str, Any], expected_schema: Dict[str, Any]) -> ValidationResult:
    """
    Validate parsed data against expected schema.
    
    For now, does basic validation that required fields exist.
    TODO: Implement full JSON schema validation
    """
    try:
        # Basic validation - check that we have stories array
        if "stories" not in data:
            return ValidationResult(
                valid=False,
                error_type="missing_stories",
                error_message="Response must contain 'stories' array"
            )
        
        stories = data.get("stories", [])
        if not isinstance(stories, list):
            return ValidationResult(
                valid=False,
                error_type="invalid_stories",
                error_message="'stories' must be an array"
            )
        
        # Check each story has required fields
        for idx, story in enumerate(stories):
            if not isinstance(story, dict):
                return ValidationResult(
                    valid=False,
                    error_type="invalid_story_format",
                    error_message=f"Story {idx} is not an object"
                )
        
        return ValidationResult(
            valid=True,
            validated_data=data
        )
        
    except Exception as e:
        return ValidationResult(
            valid=False,
            error_type="validation_error",
            error_message=str(e)
        )


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/preview", response_model=BAPreviewResponse)
async def preview_ba_request(
    request: BARequest,
    db: Session = Depends(get_db),
    prompt_service: RolePromptService = Depends(get_role_prompt_service)
) -> BAPreviewResponse:
    """
    Preview what will be sent to BA Mentor WITHOUT calling the LLM.
    Shows the system prompt with both Epic and Architecture content.
    """
    try:
        # Get Epic and Architecture artifacts
        artifact_service = ArtifactService(db)
        
        epic_artifact = artifact_service.get_artifact(request.epic_artifact_path)
        if not epic_artifact:
            raise HTTPException(404, f"Epic artifact not found: {request.epic_artifact_path}")
        
        arch_artifact = artifact_service.get_artifact(request.architecture_artifact_path)
        if not arch_artifact:
            raise HTTPException(404, f"Architecture artifact not found: {request.architecture_artifact_path}")
        
        # Build BA prompt from database
        system_prompt, prompt_id = prompt_service.build_prompt(
            role_name="ba",
            pipeline_id="preview",
            phase="ba_phase"
        )
        
        # Get schema from database
        prompt_record = RolePromptRepository.get_by_id(prompt_id)
        
        if not prompt_record:
            raise HTTPException(404, f"Prompt not found: {prompt_id}")
        
        schema = prompt_record.expected_schema or {}
        
        # Build user message with both Epic and Architecture
        user_message = f"""Please analyze this PM Epic and Architecture to generate implementation-ready BA stories.

PM EPIC:
Epic: {epic_artifact.title}
Path: {epic_artifact.artifact_path}
{json.dumps(epic_artifact.content, indent=2)}

ARCHITECTURE:
Architecture: {arch_artifact.title}
Path: {arch_artifact.artifact_path}
{json.dumps(arch_artifact.content, indent=2)}

Generate BA stories that:
1. Map PM stories to specific architectural components
2. Include detailed, testable acceptance criteria
3. Reference both PM story IDs and architecture component IDs
4. Are atomic and implementable by developers

Output ONLY valid JSON matching the BA Story Set schema."""
        
        estimated_tokens = estimate_tokens(system_prompt + user_message)
        
        return BAPreviewResponse(
            epic_artifact_path=request.epic_artifact_path,
            architecture_artifact_path=request.architecture_artifact_path,
            epic_content=epic_artifact.content,
            architecture_content=arch_artifact.content,
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
    request: BARequest,
    db: Session = Depends(get_db),
    prompt_service: RolePromptService = Depends(get_role_prompt_service),
    llm_caller: LLMCaller = Depends(get_llm_caller),
    llm_parser: LLMResponseParser = Depends(get_llm_parser)
) -> BAExecuteResponse:
    """
    Execute BA Mentor request with full transparency.
    This COSTS MONEY - each call uses API tokens (~$0.10-0.20 per call).
    
    Accepts: Paths to Epic and Architecture artifacts
    Returns: Creates Story artifacts at {epic_path}/S001, S002, etc.
    """
    try:
        # Get Epic and Architecture artifacts
        artifact_service = ArtifactService(db)
        
        epic_artifact = artifact_service.get_artifact(request.epic_artifact_path)
        if not epic_artifact:
            raise HTTPException(404, f"Epic artifact not found: {request.epic_artifact_path}")
        
        arch_artifact = artifact_service.get_artifact(request.architecture_artifact_path)
        if not arch_artifact:
            raise HTTPException(404, f"Architecture artifact not found: {request.architecture_artifact_path}")
        
        # Build BA prompt from database
        system_prompt, prompt_id = prompt_service.build_prompt(
            role_name="ba",
            pipeline_id="execution",
            phase="ba_phase"
        )
        
        # Get schema from database
        prompt_record = RolePromptRepository.get_by_id(prompt_id)
        
        if not prompt_record:
            raise HTTPException(404, f"Prompt not found: {prompt_id}")
        
        schema = prompt_record.expected_schema or {}
        
        # Build user message
        user_message = f"""Please analyze this PM Epic and Architecture to generate implementation-ready BA stories.

PM EPIC:
Epic: {epic_artifact.title}
Path: {epic_artifact.artifact_path}
{json.dumps(epic_artifact.content, indent=2)}

ARCHITECTURE:
Architecture: {arch_artifact.title}
Path: {arch_artifact.artifact_path}
{json.dumps(arch_artifact.content, indent=2)}

Generate BA stories that:
1. Map PM stories to specific architectural components
2. Include detailed, testable acceptance criteria
3. Reference both PM story IDs and architecture component IDs
4. Are atomic and implementable by developers

Output ONLY valid JSON matching the BA Story Set schema."""
        
        # Call LLM
        logger.info(f"Calling Anthropic API for BA Mentor")
        
        llm_result = llm_caller.call(
            system_prompt=system_prompt,
            user_message=user_message,
            model="claude-sonnet-4-20250514",
            max_tokens=16384,
            temperature=1.0
        )
        
        if not llm_result.success:
            raise HTTPException(500, f"LLM call failed: {llm_result.error}")
        
        raw_response = llm_result.response_text
        input_tokens = llm_result.token_usage["input_tokens"]
        output_tokens = llm_result.token_usage["output_tokens"]
        total_tokens = input_tokens + output_tokens
        execution_time_ms = llm_result.execution_time_ms
        
        logger.info(f"BA LLM call completed: {input_tokens} in / {output_tokens} out / {total_tokens} total")
        
        # Parse JSON
        parse_result = llm_parser.parse(raw_response)
        parsed_json = parse_result.data if parse_result.success else None
        
        # Validate
        stories_created = []
        
        if parsed_json:
            validation_result = validate_ba_schema(parsed_json, schema)
            
            if validation_result.valid:
                logger.info(f"BA validation passed")
                
                # Create Story artifacts
                stories_data = parsed_json.get("stories", [])
                
                for idx, story_data in enumerate(stories_data, start=1):
                    story_id = f"S{idx:03d}"
                    story_path = f"{request.epic_artifact_path}/{story_id}"
                    
                    # Extract title from story data
                    title = story_data.get("title") or story_data.get("story_title") or f"Story {story_id}"
                    
                    story_artifact = artifact_service.create_artifact(
                        artifact_path=story_path,
                        artifact_type="story",
                        title=title,
                        content=story_data,
                        breadcrumbs={
                            "created_by": "ba_mentor",
                            "prompt_id": prompt_id,
                            "epic_path": request.epic_artifact_path,
                            "architecture_path": request.architecture_artifact_path
                        }
                    )
                    
                    stories_created.append(StoryArtifact(
                        artifact_path=story_artifact.artifact_path,
                        artifact_id=str(story_artifact.id),
                        title=story_artifact.title
                    ))
                    
                    logger.info(f"Created story artifact: {story_path}")
                
            else:
                logger.warning(f"BA validation failed: {validation_result.error_message}")
                validation_result = validation_result
        else:
            validation_result = ValidationResult(
                valid=False,
                error_type="json_parse_error",
                error_message="Failed to parse JSON from LLM response",
                validation_errors=[
                    {"error": msg} for msg in parse_result.error_messages
                ]
            )
            logger.error(f"Failed to parse BA response: {parse_result.error_messages}")
        
        return BAExecuteResponse(
            epic_artifact_path=request.epic_artifact_path,
            architecture_artifact_path=request.architecture_artifact_path,
            stories_created=stories_created,
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


@router.get("/health")
async def health_check():
    """Health check for BA Mentor API"""
    return {
        "status": "healthy",
        "service": "ba_mentor",
        "version": "1.0"
    }