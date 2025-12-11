"""
Architect Mentor - Release 1

Architect Mentor that transforms PM Epics into architectural specifications using Artifacts.

Endpoints:
- POST /api/architect/preview - Show what will be sent (no API call)
- POST /api/architect/execute - Call LLM and return architecture artifact
- GET /api/architect/health - Health check
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, ValidationError, Field
from typing import List, Literal, Dict, Any, Optional
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
router = APIRouter(prefix="/api/architect", tags=["Architect Mentor"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class ArchitectRequest(BaseModel):
    """Request to architect mentor - accepts artifact path to PM epic"""
    epic_artifact_path: str = Field(..., description="RSP-1 path to PM epic (e.g., 'PROJ/E001')")


class ArchitectPreviewResponse(BaseModel):
    """Preview of what will be sent to Architect Mentor"""
    epic_artifact_path: str
    epic_content: Dict[str, Any]
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


class ArchitectExecuteResponse(BaseModel):
    """Result of actually calling Architect Mentor"""
    epic_artifact_path: str
    architecture_artifact_path: str
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


def validate_architecture_schema(data: Dict[str, Any], expected_schema: Dict[str, Any]) -> ValidationResult:
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
            error_type="validation_error",
            error_message=str(e)
        )


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/preview", response_model=ArchitectPreviewResponse)
async def preview_architect_request(
    request: ArchitectRequest,
    db: Session = Depends(get_db),
    prompt_service: RolePromptService = Depends(get_role_prompt_service)
) -> ArchitectPreviewResponse:
    """
    Preview what will be sent to Architect Mentor WITHOUT calling the LLM.
    Shows the system prompt, user message with PM Epic, and expected schema.
    
    Accepts: RSP-1 path to PM Epic artifact
    """
    try:
        # Get PM Epic artifact
        artifact_service = ArtifactService(db)
        epic_artifact = artifact_service.get_artifact(request.epic_artifact_path)
        
        if not epic_artifact:
            raise HTTPException(404, f"Epic artifact not found: {request.epic_artifact_path}")
        
        if epic_artifact.artifact_type != "epic":
            raise HTTPException(400, f"Artifact is not an epic: {epic_artifact.artifact_type}")
        
        # Build Architect prompt from database
        system_prompt, prompt_id = prompt_service.build_prompt(
            role_name="architect",
            pipeline_id="preview",
            phase="arch_phase"
        )
        
        # Get schema from database
        prompt_record = RolePromptRepository.get_by_id(prompt_id)
        
        if not prompt_record:
            raise HTTPException(404, f"Prompt not found: {prompt_id}")
        
        schema = prompt_record.expected_schema or {}
        
        # Build user message with PM Epic content
        user_message = f"""Transform the following PM Epic into a complete architectural specification:

Epic: {epic_artifact.title}
Path: {epic_artifact.artifact_path}

{json.dumps(epic_artifact.content, indent=2)}

Output ONLY valid JSON matching the architecture schema. No markdown, no prose."""
        
        estimated_tokens = estimate_tokens(system_prompt + user_message)
        
        return ArchitectPreviewResponse(
            epic_artifact_path=request.epic_artifact_path,
            epic_content=epic_artifact.content,
            system_prompt=system_prompt,
            user_message=user_message,
            expected_schema=schema,
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
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
    request: ArchitectRequest,
    db: Session = Depends(get_db),
    prompt_service: RolePromptService = Depends(get_role_prompt_service),
    llm_caller: LLMCaller = Depends(get_llm_caller),
    llm_parser: LLMResponseParser = Depends(get_llm_parser)
) -> ArchitectExecuteResponse:
    """
    Actually execute Architect Mentor request with Anthropic API.
    This COSTS MONEY - each call uses API tokens (~$0.05-0.10 per call).
    
    Accepts: RSP-1 path to PM Epic artifact
    Returns: Creates and returns Architecture artifact at {epic_path}/ARCH
    """
    try:
        # Get PM Epic artifact
        artifact_service = ArtifactService(db)
        epic_artifact = artifact_service.get_artifact(request.epic_artifact_path)
        
        if not epic_artifact:
            raise HTTPException(404, f"Epic artifact not found: {request.epic_artifact_path}")
        
        if epic_artifact.artifact_type != "epic":
            raise HTTPException(400, f"Artifact is not an epic: {epic_artifact.artifact_type}")
        
        # Build Architect prompt
        system_prompt, prompt_id = prompt_service.build_prompt(
            role_name="architect",
            pipeline_id="execution",
            phase="arch_phase"
        )
        
        # Get schema from database
        prompt_record = RolePromptRepository.get_by_id(prompt_id)
        
        if not prompt_record:
            raise HTTPException(404, f"Prompt not found: {prompt_id}")
        
        schema = prompt_record.expected_schema or {}
        
        # Build user message
        user_message = f"""Transform the following PM Epic into a complete architectural specification:

Epic: {epic_artifact.title}
Path: {epic_artifact.artifact_path}

{json.dumps(epic_artifact.content, indent=2)}

Output ONLY valid JSON matching the architecture schema. No markdown, no prose."""
        
        # Call LLM
        logger.info(f"Calling Anthropic API for Architect (Epic: {request.epic_artifact_path})")
        
        llm_result = llm_caller.call(
            system_prompt=system_prompt,
            user_message=user_message,
            model="claude-sonnet-4-20250514",
            max_tokens=16384,
            temperature=0.7
        )
        
        if not llm_result.success:
            raise HTTPException(500, f"LLM call failed: {llm_result.error}")
        
        raw_response = llm_result.response_text
        input_tokens = llm_result.token_usage["input_tokens"]
        output_tokens = llm_result.token_usage["output_tokens"]
        total_tokens = input_tokens + output_tokens
        execution_time_ms = llm_result.execution_time_ms
        
        logger.info(f"Architect LLM call completed: {input_tokens} in / {output_tokens} out / {total_tokens} total")
        
        # Parse JSON
        parse_result = llm_parser.parse(raw_response)
        parsed_json = parse_result.data if parse_result.success else None
        
        # Validate
        if parsed_json:
            validation_result = validate_architecture_schema(parsed_json, schema)
            if validation_result.valid:
                logger.info(f"Architecture validation passed for {request.epic_artifact_path}")
                
                # Create Architecture artifact
                arch_path = f"{request.epic_artifact_path}/ARCH"
                
                architecture_artifact = artifact_service.create_artifact(
                    artifact_path=arch_path,
                    artifact_type="architecture",
                    title=f"Architecture for {epic_artifact.title}",
                    content=parsed_json,
                    breadcrumbs={
                        "created_by": "architect_mentor",
                        "prompt_id": prompt_id,
                        "epic_path": request.epic_artifact_path,
                        "tokens_used": total_tokens
                    }
                )
                
                logger.info(f"Created architecture artifact: {arch_path}")
                
            else:
                logger.warning(f"Architecture validation failed: {validation_result.error_message}")
                # Still create artifact even if validation fails (for debugging)
                arch_path = f"{request.epic_artifact_path}/ARCH"
                architecture_artifact = artifact_service.create_artifact(
                    artifact_path=arch_path,
                    artifact_type="architecture",
                    title=f"Architecture for {epic_artifact.title} (validation failed)",
                    content=parsed_json or {"error": "validation_failed"},
                    parent_path=request.epic_artifact_path,
                    status="validation_failed",
                    breadcrumbs={
                        "created_by": "architect_mentor",
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
            logger.error(f"Failed to parse Architect response: {parse_result.error_messages}")
            
            # Create artifact with error
            arch_path = f"{request.epic_artifact_path}/ARCH"
            architecture_artifact = artifact_service.create_artifact(
                artifact_path=arch_path,
                artifact_type="architecture",
                title=f"Architecture for {epic_artifact.title} (parse failed)",
                content={"error": "parse_failed", "raw_response": raw_response[:500]},
                parent_path=request.epic_artifact_path,
                status="parse_failed",
                breadcrumbs={
                    "created_by": "architect_mentor",
                    "prompt_id": prompt_id,
                    "parse_errors": parse_result.error_messages
                }
            )
        
        return ArchitectExecuteResponse(
            epic_artifact_path=request.epic_artifact_path,
            architecture_artifact_path=architecture_artifact.artifact_path,
            artifact_id=str(architecture_artifact.id),
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
    return {"status": "ok", "service": "architect_mentor"}