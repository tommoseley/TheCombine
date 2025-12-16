"""
PM Mentor - Extends StreamingMentor with PM-specific logic

Transforms user queries into Epic artifacts with streaming progress updates.
"""

from typing import Dict, Any, List
from pydantic import BaseModel, Field

from app.domain.mentors.base_mentor import StreamingMentor, ProgressStep


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class PMRequest(BaseModel):
    """Request to PM Mentor"""
    user_query: str = Field(..., description="User's natural language request")
    project_id: str = Field(..., description="Project ID for artifact path (e.g., 'PROJ')")
    model: str = Field(default="claude-sonnet-4-20250514", description="Model to use")
    max_tokens: int = Field(default=4096, description="Maximum tokens")
    temperature: float = Field(default=0.7, description="Temperature for generation")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_query": "I want to build a user authentication system with email/password login and password reset.",
                "project_id": "AUTH"
            }
        }


# ============================================================================
# PM MENTOR IMPLEMENTATION
# ============================================================================

class PMMentor(StreamingMentor):
    """
    Product Manager Mentor - Creates epic definitions from user queries
    
    Progress Steps:
    1. Reading PM instructions (10%)
    2. Loading epic schema (20%)
    3. Analyzing your request (30%)
    4. Crafting epic definition (50%)
    5. Building epic structure (70%)
    6. Parsing epic JSON (80%)
    7. Validating epic completeness (85%)
    8. Saving epic to project (95%)
    9. Epic created successfully! (100%)
    """
    
    @property
    def role_name(self) -> str:
        return "pm"
    
    @property
    def pipeline_id(self) -> str:
        return "execution"
    
    @property
    def phase_name(self) -> str:
        return "pm_phase"
    
    @property
    def progress_steps(self) -> List[ProgressStep]:
        """PM-specific progress steps"""
        return [
            ProgressStep("building_prompt", "Reading PM instructions", "📋", 10),
            ProgressStep("loading_schema", "Loading epic schema", "📄", 20),
            ProgressStep("calling_llm", "Analyzing your request", "🤖", 30),
            ProgressStep("generating", "Crafting epic definition", "✨", 50),
            ProgressStep("streaming", "Building epic structure", "💭", 70),
            ProgressStep("parsing", "Parsing epic JSON", "🔧", 80),
            ProgressStep("validating", "Validating epic completeness", "✅", 85),
            ProgressStep("saving", "Saving epic to project", "💾", 95),
            ProgressStep("complete", "Epic created successfully!", "🎉", 100),
            ProgressStep("error", "Something went wrong", "❌", 0),
            ProgressStep("validation_failed", "Validation issues detected", "⚠️", 85)
        ]
    
    async def build_user_message(self, request_data: Dict[str, Any]) -> str:
        """Build PM-specific user message"""
        user_query = request_data.get("user_query", "")
        
        return f"""Create an Epic definition for the following user request:

{user_query}

Remember: Output ONLY valid JSON matching the schema. No markdown, no prose."""
    
    async def validate_response(
        self, 
        parsed_json: Dict[str, Any], 
        schema: Dict[str, Any]
    ) -> tuple[bool, str]:
        """
        Validate PM epic response
        
        Checks for required fields:
        - epic_id or title
        - objectives (must be a list with at least one item)
        """
        # Check for title or epic_id
        if "title" not in parsed_json and "epic_id" not in parsed_json:
            return False, "Missing required field: 'title' or 'epic_id'"
        
        # Check for objectives
        if "objectives" not in parsed_json:
            return False, "Missing required field: 'objectives'"
        
        objectives = parsed_json.get("objectives")
        if not isinstance(objectives, list):
            return False, "Field 'objectives' must be a list"
        
        if len(objectives) == 0:
            return False, "Epic must have at least one objective"
        
        return True, ""
    
    async def create_artifact(
        self,
        request_data: Dict[str, Any],
        parsed_json: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create PM epic artifact
        
        Uses injected id_generator to generate epic IDs.
        
        Returns:
            Dictionary with:
            - project_id: Project identifier
            - epic_id: Generated epic ID
            - epic_path: Full RSP-1 path
            - artifact_id: Database artifact ID
            - title: Epic title
        """
        project_id = request_data.get("project_id")
        
        # Generate epic ID using injected generator
        epic_id = parsed_json.get("epic_id")
        if not epic_id:
            if self.id_generator is None:
                raise ValueError("No ID generator provided and epic_id not in response")
            epic_id = await self.id_generator(project_id)
            parsed_json["epic_id"] = epic_id
        
        epic_path = f"{project_id}/{epic_id}"
        
        # Extract title
        title = parsed_json.get("title") or parsed_json.get("epic_title") or f"Epic {epic_id}"
        
        # Create artifact with breadcrumbs
        breadcrumbs = {
            "created_by": "pm_mentor",
            "user_query": request_data.get("user_query", ""),
            **metadata
        }
        
        artifact = await self.artifact_service.create_artifact(
            artifact_path=epic_path,
            artifact_type="epic",
            title=title,
            content=parsed_json,
            breadcrumbs=breadcrumbs
        )
        
        return {
            "project_id": project_id,
            "epic_id": epic_id,
            "epic_path": epic_path,
            "artifact_id": str(artifact.id),
            "title": title
        }