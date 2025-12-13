"""
PM Mentor - Release 1 (ASYNC VERSION)

PM Mentor that transforms user requests into Epic artifacts.

Endpoints:
- POST /api/pm/preview - Show what will be sent (no API call)
- POST /api/pm/execute - Call LLM and return epic artifact
- GET /api/pm/health - Health check
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, ValidationError, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json
import logging

from app.combine.services.llm_caller import LLMCaller
from app.combine.services.llm_response_parser import LLMResponseParser
from app.combine.services.role_prompt_service import RolePromptService
from app.combine.services.artifact_service import ArtifactService
from app.combine.models import Artifact, Project
from app.combine.repositories.role_prompt_repository import RolePromptRepository
from database import get_db
from config import settings

try:
    import anthropic
except ImportError:
    anthropic = None

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/pm", tags=["PM Mentor"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class PMRequest(BaseModel):
    """Request to PM Mentor"""
    user_query: str = Field(..., description="User's natural language request")
    project_id: str = Field(..., description="Project ID for artifact path (e.g., 'PROJ')")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_query": "I want to build a user authentication system with email/password login and password reset.",
                "project_id": "AUTH"
            }
        }


class PMPreviewResponse(BaseModel):
    """Preview of what will be sent to LLM (no actual API call)"""
    project_id: str
    user_query: str
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


class PMExecuteResponse(BaseModel):
    """Result of actually calling PM Mentor"""
    project_id: str
    epic_artifact_path: str
    artifact_id: str
    
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


async def ensure_project_exists(project_id: str, db: AsyncSession) -> None:
    """
    Ensure project exists, create if it doesn't.
    
    Args:
        project_id: Project identifier
        db: Database session
    """
    # Check if project exists
    result = await db.execute(
        select(Project).where(Project.project_id == project_id)
    )
    existing = result.scalar_one_or_none()
    
    if not existing:
        # Create new project
        project = Project(
            project_id=project_id,
            name=project_id,
            description=f"Auto-created project: {project_id}",
            status="active"
        )
        db.add(project)
        await db.commit()
        logger.info(f"Auto-created project: {project_id}")


async def generate_epic_id(project_id: str, db: AsyncSession) -> str:
    """
    Generate next epic ID for project.
    
    Format: E001, E002, etc.
    """
    artifact_service = ArtifactService(db)
    
    # Find highest epic number for this project
    existing_epics = await artifact_service.list_artifacts(
        artifact_type="epic",
        project_id=project_id
    )
    
    if not existing_epics:
        return "E001"
    
    # Extract numbers from epic IDs
    epic_numbers = []
    for epic in existing_epics:
        # Epic path is like "PROJ/E001"
        epic_id = epic.epic_id
        if epic_id and epic_id.startswith("E"):
            try:
                num = int(epic_id[1:])
                epic_numbers.append(num)
            except ValueError:
                continue
    
    if not epic_numbers:
        return "E001"
    
    next_num = max(epic_numbers) + 1
    return f"E{next_num:03d}"


def validate_epic_schema(data: Dict[str, Any], expected_schema: Dict[str, Any]) -> ValidationResult:
    """
    Validate parsed data against expected schema.
    
    For now, does basic validation that required fields exist.
    TODO: Implement full JSON schema validation
    """
    try:
        # Basic validation - check required fields from schema
        if "properties" in expected_schema:
            required_fields = expected_schema.get("required", [])
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                return ValidationResult(
                    valid=False,
                    error_type="missing_required_fields",
                    error_message=f"Missing required fields: {', '.join(missing_fields)}",
                    validation_errors=[{"field": f, "error": "required"} for f in missing_fields]
                )
        
        return ValidationResult(
            valid=True,
            validated_data=data
        )
        
    except Exception as e:
        return ValidationResult(
            valid=False,
            error_type="validation_exception",
            error_message=str(e)
        )


# ============================================================================
# ROUTES
# ============================================================================

@router.post("/preview", response_model=PMPreviewResponse)
async def preview_pm_request(
    request: PMRequest,
    prompt_service: RolePromptService = Depends(get_role_prompt_service)
) -> PMPreviewResponse:
    """
    Preview what will be sent to LLM (NO API CALL - FREE).
    
    Shows the exact system prompt, user message, and schema that would be used.
    Useful for debugging and understanding what the PM Mentor does.
    """
    try:
        # Build PM prompt from database
        system_prompt, prompt_id = await prompt_service.build_prompt(
            role_name="pm",
            pipeline_id="preview",
            phase="pm_phase",
            epic_context=request.user_query
        )
        
        # Get schema from database
        prompt_record = await RolePromptRepository.get_by_id(prompt_id)
        
        if not prompt_record:
            raise HTTPException(404, f"Prompt not found: {prompt_id}")
        
        schema = prompt_record.expected_schema or {}
        
        # Build user message
        user_message = f"""Create an Epic definition for the following user request:

{request.user_query}

Remember: Output ONLY valid JSON matching the schema. No markdown, no prose."""
        
        estimated_tokens = estimate_tokens(system_prompt + user_message)
        
        return PMPreviewResponse(
            project_id=request.project_id,
            user_query=request.user_query,
            system_prompt=system_prompt,
            user_message=user_message,
            expected_schema=schema,
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
    request: PMRequest,
    db: AsyncSession = Depends(get_db),
    prompt_service: RolePromptService = Depends(get_role_prompt_service),
    llm_caller: LLMCaller = Depends(get_llm_caller),
    llm_parser: LLMResponseParser = Depends(get_llm_parser)
) -> PMExecuteResponse:
    """
    Actually execute PM Mentor request with Anthropic API.
    This COSTS MONEY - each call uses API tokens (~$0.02-0.05 per call).
    
    Accepts: User query and project ID
    Returns: Creates and returns Epic artifact at {project_id}/{epic_id}
    """
    try:
        # Build PM prompt from database
        system_prompt, prompt_id = await prompt_service.build_prompt(
            role_name="pm",
            pipeline_id="execution",
            phase="pm_phase",
            epic_context=request.user_query
        )
        
        # Get schema from database
        prompt_record = await RolePromptRepository.get_by_id(prompt_id)
        
        if not prompt_record:
            raise HTTPException(404, f"Prompt not found: {prompt_id}")
        
        schema = prompt_record.expected_schema or {}
        
        # Build user message
        user_message = f"""Create an Epic definition for the following user request:

{request.user_query}

Remember: Output ONLY valid JSON matching the schema. No markdown, no prose."""
        
        # Call LLM
        logger.info(f"Calling Anthropic API for PM request (Project: {request.project_id})")
        
        llm_result = llm_caller.call(
            system_prompt=system_prompt,
            user_message=user_message,
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            temperature=0.7
        )
        
        if not llm_result.success:
            raise HTTPException(500, f"LLM call failed: {llm_result.error}")
        
        raw_response = llm_result.response_text
        input_tokens = llm_result.token_usage["input_tokens"]
        output_tokens = llm_result.token_usage["output_tokens"]
        total_tokens = input_tokens + output_tokens
        execution_time_ms = llm_result.execution_time_ms
        
        logger.info(f"PM LLM call completed: {input_tokens} in / {output_tokens} out / {total_tokens} total")
        
        # Parse JSON
        parse_result = llm_parser.parse(raw_response)
        parsed_json = parse_result.data if parse_result.success else None
        
        # Validate
        if parsed_json:
            validation_result = validate_epic_schema(parsed_json, schema)
            
            if validation_result.valid:
                logger.info(f"Epic validation passed for project {request.project_id}")
                
                # Ensure project exists (auto-create if needed)
                await ensure_project_exists(request.project_id, db)
                
                # Generate epic ID
                epic_id = await generate_epic_id(request.project_id, db)
                epic_path = f"{request.project_id}/{epic_id}"
                
                # Extract title from content or use default
                title = parsed_json.get("title") or parsed_json.get("epic_title") or f"Epic {epic_id}"
                
                # Create Epic artifact
                artifact_service = ArtifactService(db)
                epic_artifact = await artifact_service.create_artifact(
                    artifact_path=epic_path,
                    artifact_type="epic",
                    title=title,
                    content=parsed_json,
                    breadcrumbs={
                        "created_by": "pm_mentor",
                        "prompt_id": prompt_id,
                        "user_query": request.user_query,
                        "tokens_used": total_tokens
                    }
                )
                
                logger.info(f"Created epic artifact: {epic_path}")
                
            else:
                logger.warning(f"Epic validation failed: {validation_result.error_message}")
                
                # Still create artifact with validation failure status
                await ensure_project_exists(request.project_id, db)
                epic_id = await generate_epic_id(request.project_id, db)
                epic_path = f"{request.project_id}/{epic_id}"
                
                artifact_service = ArtifactService(db)
                epic_artifact = await artifact_service.create_artifact(
                    artifact_path=epic_path,
                    artifact_type="epic",
                    title=f"Epic {epic_id} (validation failed)",
                    content=parsed_json or {"error": "validation_failed"},
                    status="validation_failed",
                    breadcrumbs={
                        "created_by": "pm_mentor",
                        "prompt_id": prompt_id,
                        "validation_error": validation_result.error_message
                    }
                )
        else:
            validation_result = ValidationResult(
                valid=False,
                error_type="json_parse_error",
                error_message="Failed to parse JSON from LLM response",
                validation_errors=[
                    {"error": msg} for msg in parse_result.error_messages
                ]
            )
            logger.error(f"Failed to parse PM response: {parse_result.error_messages}")
            
            # Create artifact with parse error
            await ensure_project_exists(request.project_id, db)
            epic_id = await generate_epic_id(request.project_id, db)
            epic_path = f"{request.project_id}/{epic_id}"
            
            artifact_service = ArtifactService(db)
            epic_artifact = await artifact_service.create_artifact(
                artifact_path=epic_path,
                artifact_type="epic",
                title=f"Epic {epic_id} (parse failed)",
                content={"error": "parse_failed", "raw_response": raw_response[:500]},
                status="parse_failed",
                breadcrumbs={
                    "created_by": "pm_mentor",
                    "prompt_id": prompt_id,
                    "parse_errors": parse_result.error_messages
                }
            )
        
        return PMExecuteResponse(
            project_id=request.project_id,
            epic_artifact_path=epic_artifact.artifact_path,
            artifact_id=str(epic_artifact.id),
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
        logger.error(f"Error executing PM request: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to execute request: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "pm_mentor",
        "release": "R1"
    }