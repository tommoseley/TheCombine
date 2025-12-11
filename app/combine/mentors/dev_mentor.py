"""
Developer Mentor - Release 1

Developer Mentor that transforms User Stories into code implementation artifacts.

Endpoints:
- POST /api/developer/preview - Show what will be sent (no API call)
- POST /api/developer/execute - Call LLM and return code artifacts
- GET /api/developer/health - Health check
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
router = APIRouter(prefix="/api/developer", tags=["Developer Mentor"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class DeveloperRequest(BaseModel):
    """Request to Developer Mentor - requires story artifact"""
    story_artifact_path: str = Field(..., description="RSP-1 path to Story (e.g., 'PROJ/E001/S001')")


class DeveloperPreviewResponse(BaseModel):
    """Preview of what will be sent to Developer Mentor"""
    story_artifact_path: str
    story_content: Dict[str, Any]
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


class CodeArtifact(BaseModel):
    """Individual code artifact created"""
    artifact_path: str
    artifact_id: str
    title: str
    file_path: str


class DeveloperExecuteResponse(BaseModel):
    """Result of actually calling Developer Mentor"""
    story_artifact_path: str
    code_artifacts_created: List[CodeArtifact]
    
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


def validate_code_schema(data: Dict[str, Any], expected_schema: Dict[str, Any]) -> ValidationResult:
    """
    Validate parsed data against expected schema.
    
    For now, does basic validation that required fields exist.
    TODO: Implement full JSON schema validation
    """
    try:
        # Basic validation - check that we have code files array
        if "files" not in data:
            return ValidationResult(
                valid=False,
                error_type="missing_files",
                error_message="Response must contain 'files' array"
            )
        
        files = data.get("files", [])
        if not isinstance(files, list):
            return ValidationResult(
                valid=False,
                error_type="invalid_files",
                error_message="'files' must be an array"
            )
        
        # Check each file has required fields
        for idx, file_data in enumerate(files):
            if not isinstance(file_data, dict):
                return ValidationResult(
                    valid=False,
                    error_type="invalid_file_format",
                    error_message=f"File {idx} is not an object"
                )
            
            required = ["file_path", "content"]
            missing = [f for f in required if f not in file_data]
            if missing:
                return ValidationResult(
                    valid=False,
                    error_type="missing_file_fields",
                    error_message=f"File {idx} missing: {', '.join(missing)}"
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

@router.post("/preview", response_model=DeveloperPreviewResponse)
async def preview_developer_request(
    request: DeveloperRequest,
    db: Session = Depends(get_db),
    prompt_service: RolePromptService = Depends(get_role_prompt_service)
) -> DeveloperPreviewResponse:
    """
    Preview what will be sent to Developer Mentor WITHOUT calling the LLM.
    Shows the system prompt with Story content.
    """
    try:
        # Get Story artifact
        artifact_service = ArtifactService(db)
        
        story_artifact = artifact_service.get_artifact(request.story_artifact_path)
        if not story_artifact:
            raise HTTPException(404, f"Story artifact not found: {request.story_artifact_path}")
        
        if story_artifact.artifact_type != "story":
            raise HTTPException(400, f"Artifact is not a story: {story_artifact.artifact_type}")
        
        # Build Developer prompt from database
        system_prompt, prompt_id = prompt_service.build_prompt(
            role_name="developer",
            pipeline_id="preview",
            phase="dev_phase"
        )
        
        # Get schema from database
        prompt_record = RolePromptRepository.get_by_id(prompt_id)
        
        if not prompt_record:
            raise HTTPException(404, f"Prompt not found: {prompt_id}")
        
        schema = prompt_record.expected_schema or {}
        
        # Build user message with Story
        user_message = f"""Implement the following User Story with complete, production-ready code:

Story: {story_artifact.title}
Path: {story_artifact.artifact_path}

{json.dumps(story_artifact.content, indent=2)}

Generate implementation that:
1. Includes all necessary files (code, tests, configs)
2. Follows best practices and coding standards
3. Is complete and ready to run
4. Includes inline documentation

Output ONLY valid JSON matching the code files schema. No markdown, no prose."""
        
        estimated_tokens = estimate_tokens(system_prompt + user_message)
        
        return DeveloperPreviewResponse(
            story_artifact_path=request.story_artifact_path,
            story_content=story_artifact.content,
            system_prompt=system_prompt,
            user_message=user_message,
            expected_schema=schema,
            model="claude-sonnet-4-20250514",
            max_tokens=32000,
            temperature=0.7,
            estimated_input_tokens=estimated_tokens
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Preview failed: {e}", exc_info=True)
        raise HTTPException(500, f"Preview failed: {str(e)}")


@router.post("/execute", response_model=DeveloperExecuteResponse)
async def execute_developer_request(
    request: DeveloperRequest,
    db: Session = Depends(get_db),
    prompt_service: RolePromptService = Depends(get_role_prompt_service),
    llm_caller: LLMCaller = Depends(get_llm_caller),
    llm_parser: LLMResponseParser = Depends(get_llm_parser)
) -> DeveloperExecuteResponse:
    """
    Execute Developer Mentor request with full transparency.
    This COSTS MONEY - each call uses API tokens (~$0.20-0.50 per call).
    
    Accepts: Path to Story artifact
    Returns: Creates Code artifacts at {story_path}/CODE001, CODE002, etc.
    """
    try:
        # Get Story artifact
        artifact_service = ArtifactService(db)
        
        story_artifact = artifact_service.get_artifact(request.story_artifact_path)
        if not story_artifact:
            raise HTTPException(404, f"Story artifact not found: {request.story_artifact_path}")
        
        if story_artifact.artifact_type != "story":
            raise HTTPException(400, f"Artifact is not a story: {story_artifact.artifact_type}")
        
        # Build Developer prompt from database
        system_prompt, prompt_id = prompt_service.build_prompt(
            role_name="developer",
            pipeline_id="execution",
            phase="dev_phase"
        )
        
        # Get schema from database
        prompt_record = RolePromptRepository.get_by_id(prompt_id)
        
        if not prompt_record:
            raise HTTPException(404, f"Prompt not found: {prompt_id}")
        
        schema = prompt_record.expected_schema or {}
        
        # Build user message
        user_message = f"""Implement the following User Story with complete, production-ready code:

Story: {story_artifact.title}
Path: {story_artifact.artifact_path}

{json.dumps(story_artifact.content, indent=2)}

Generate implementation that:
1. Includes all necessary files (code, tests, configs)
2. Follows best practices and coding standards
3. Is complete and ready to run
4. Includes inline documentation

Output ONLY valid JSON matching the code files schema. No markdown, no prose."""
        
        # Call LLM
        logger.info(f"Calling Anthropic API for Developer Mentor")
        
        llm_result = llm_caller.call(
            system_prompt=system_prompt,
            user_message=user_message,
            model="claude-sonnet-4-20250514",
            max_tokens=32000,
            temperature=0.7
        )
        
        if not llm_result.success:
            raise HTTPException(500, f"LLM call failed: {llm_result.error}")
        
        raw_response = llm_result.response_text
        input_tokens = llm_result.token_usage["input_tokens"]
        output_tokens = llm_result.token_usage["output_tokens"]
        total_tokens = input_tokens + output_tokens
        execution_time_ms = llm_result.execution_time_ms
        
        logger.info(f"Developer LLM call completed: {input_tokens} in / {output_tokens} out / {total_tokens} total")
        
        # Parse JSON
        parse_result = llm_parser.parse(raw_response)
        parsed_json = parse_result.data if parse_result.success else None
        
        # Validate
        code_artifacts_created = []
        
        if parsed_json:
            validation_result = validate_code_schema(parsed_json, schema)
            
            if validation_result.valid:
                logger.info(f"Developer validation passed")
                
                # Create Code artifacts
                files_data = parsed_json.get("files", [])
                
                for idx, file_data in enumerate(files_data, start=1):
                    code_id = f"CODE{idx:03d}"
                    code_path = f"{request.story_artifact_path}/{code_id}"
                    
                    # Extract file info
                    file_path = file_data.get("file_path", f"unknown_{idx}")
                    title = f"Code: {file_path}"
                    
                    code_artifact = artifact_service.create_artifact(
                        artifact_path=code_path,
                        artifact_type="code",
                        title=title,
                        content=file_data,
                        breadcrumbs={
                            "created_by": "developer_mentor",
                            "prompt_id": prompt_id,
                            "story_path": request.story_artifact_path,
                            "file_path": file_path
                        }
                    )
                    
                    code_artifacts_created.append(CodeArtifact(
                        artifact_path=code_artifact.artifact_path,
                        artifact_id=str(code_artifact.id),
                        title=code_artifact.title,
                        file_path=file_path
                    ))
                    
                    logger.info(f"Created code artifact: {code_path}")
                
            else:
                logger.warning(f"Developer validation failed: {validation_result.error_message}")
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
            logger.error(f"Failed to parse Developer response: {parse_result.error_messages}")
        
        return DeveloperExecuteResponse(
            story_artifact_path=request.story_artifact_path,
            code_artifacts_created=code_artifacts_created,
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
        logger.error(f"Developer Mentor execution failed: {e}", exc_info=True)
        raise HTTPException(500, f"Execution failed: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check for Developer Mentor API"""
    return {
        "status": "healthy",
        "service": "developer_mentor",
        "version": "1.0"
    }