"""
Architect Mentor - Extends StreamingMentor with Architect-specific logic

Transforms PM Epics into architectural specifications with streaming progress updates.
"""

from typing import Dict, Any, List, Optional, Callable, Awaitable
from pydantic import BaseModel, Field

from app.domain.mentors.base_mentor import StreamingMentor, ProgressStep


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class ArchitectRequest(BaseModel):
    """Request to Architect Mentor"""
    epic_artifact_path: str = Field(..., description="RSP-1 path to PM epic (e.g., 'PROJ/E001')")
    model: str = Field(default="claude-opus-4-20250514", description="Model to use (defaults to Opus for architecture)")
    max_tokens: int = Field(default=8192, description="Maximum tokens (higher for architecture)")
    temperature: float = Field(default=0.5, description="Temperature for generation")
    
    class Config:
        json_schema_extra = {
            "example": {
                "epic_artifact_path": "AUTH/E001"
            }
        }


# ============================================================================
# ARCHITECT MENTOR IMPLEMENTATION
# ============================================================================

class ArchitectMentor(StreamingMentor):
    """
    Architect Mentor - Creates architectural specifications from PM epics
    
    Uses Claude Opus for superior architectural reasoning and system design.
    
    Progress Steps:
    1. Reading architecture guidelines (8%)
    2. Loading architecture schema (12%)
    3. Loading epic context (20%)
    4. Analyzing epic requirements (28%)
    5. Designing system architecture (40%)
    6. Defining components and interfaces (55%)
    7. Creating data models (70%)
    8. Parsing architecture JSON (82%)
    9. Validating architecture completeness (88%)
    10. Saving architecture (95%)
    11. Architecture created successfully! (100%)
    """
    
    @property
    def role_name(self) -> str:
        return "architect"
    
    @property
    def pipeline_id(self) -> str:
        return "execution"
    
    @property
    def phase_name(self) -> str:
        return "architect_phase"
    
    @property
    def preferred_model(self) -> str:
        """
        Use Claude Opus for architecture.
        Architecture requires deep strategic thinking and system design reasoning.
        """
        return "claude-opus-4-20250514"
    
    @property
    def progress_steps(self) -> List[ProgressStep]:
        """Architect-specific progress steps"""
        return [
            ProgressStep("building_prompt", "Reading architecture guidelines", "📋", 8),
            ProgressStep("loading_schema", "Loading architecture schema", "📄", 12),
            ProgressStep("loading_epic", "Loading epic context", "📖", 20),
            ProgressStep("calling_llm", "Analyzing epic requirements", "🤖", 28),
            ProgressStep("generating", "Designing system architecture", "✨", 40),
            ProgressStep("streaming", "Defining components and interfaces", "💭", 55),
            ProgressStep("building_models", "Creating data models", "🗄️", 70),
            ProgressStep("parsing", "Parsing architecture JSON", "🔧", 82),
            ProgressStep("validating", "Validating architecture completeness", "✅", 88),
            ProgressStep("saving", "Saving architecture", "💾", 95),
            ProgressStep("complete", "Architecture created successfully!", "🎉", 100),
            ProgressStep("error", "Something went wrong", "❌", 0),
            ProgressStep("validation_failed", "Validation issues detected", "⚠️", 88)
        ]
    
    async def build_user_message(self, request_data: Dict[str, Any]) -> str:
        """
        Build Architect-specific user message
        
        Includes epic content for context
        """
        epic_content = request_data.get("epic_content", {})
        
        # Extract epic details
        epic_title = epic_content.get("title", "Epic")
        epic_objectives = epic_content.get("objectives", [])
        epic_description = epic_content.get("description", "")
        user_stories = epic_content.get("user_stories", [])
        
        # Format objectives
        objectives_text = "\n".join([f"- {obj}" for obj in epic_objectives])
        
        # Format user stories if present
        stories_text = ""
        if user_stories:
            stories_text = "\n\nUser Stories:\n" + "\n".join([
                f"- {story.get('title', 'Story')}: {story.get('description', '')}" 
                for story in user_stories[:5]  # Limit to first 5
            ])
        
        return f"""Create a comprehensive architecture specification for the following epic:

Epic: {epic_title}

Description:
{epic_description}

Objectives:
{objectives_text}
{stories_text}

Provide a complete architecture including:
1. Architecture summary with style and key decisions
2. System components with responsibilities and technologies
3. Data models and schemas
4. API interfaces and endpoints
5. Quality attributes (performance, security, scalability)
6. Key workflows
7. Risks and mitigations

Remember: Output ONLY valid JSON matching the schema. No markdown, no prose."""
    
    async def validate_response(
        self, 
        parsed_json: Dict[str, Any], 
        schema: Dict[str, Any]
    ) -> tuple[bool, str]:
        """
        Validate Architect response
        
        Checks for required architecture sections:
        - architecture_summary
        - components
        - data_model (optional but recommended)
        - interfaces (optional but recommended)
        """
        # Check for architecture_summary
        if "architecture_summary" not in parsed_json:
            return False, "Missing required section: 'architecture_summary'"
        
        # Check for components
        if "components" not in parsed_json:
            return False, "Missing required section: 'components'"
        
        components = parsed_json.get("components", [])
        if not isinstance(components, list):
            return False, "Section 'components' must be a list"
        
        if len(components) == 0:
            return False, "Architecture must define at least one component"
        
        # Validate component structure
        for idx, component in enumerate(components):
            if not isinstance(component, dict):
                return False, f"Component {idx+1} must be an object"
            if "name" not in component:
                return False, f"Component {idx+1} missing 'name'"
            if "purpose" not in component:
                return False, f"Component {idx+1} missing 'purpose'"
        
        return True, ""
    
    async def create_artifact(
        self,
        request_data: Dict[str, Any],
        parsed_json: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create Architect artifact
        
        Returns:
            Dictionary with:
            - epic_artifact_path: Source epic path
            - architecture_artifact_path: Generated architecture path
            - artifact_id: Database artifact ID
            - project_id: Extracted project ID
            - epic_id: Extracted epic ID
        """
        epic_artifact_path = request_data.get("epic_artifact_path")
        
        # Parse project and epic from path (e.g., "PROJ/E001")
        path_parts = epic_artifact_path.split("/")
        if len(path_parts) != 2:
            raise ValueError(f"Invalid epic path: {epic_artifact_path}. Expected format: PROJECT/EPIC")
        
        project_id, epic_id = path_parts
        
        # Architecture artifact path is same as epic path
        # (architecture is a special artifact type within the epic)
        architecture_path = epic_artifact_path
        
        # Extract title from architecture summary
        arch_summary = parsed_json.get("architecture_summary", {})
        title = arch_summary.get("title", f"Architecture for {epic_id}")
        
        # Create artifact with breadcrumbs
        breadcrumbs = {
            "created_by": "architect_mentor",
            "epic_artifact_path": epic_artifact_path,
            "epic_id": epic_id,
            **metadata
        }
        
        artifact = await self.artifact_service.create_artifact(
            artifact_path=architecture_path,
            artifact_type="architecture",
            title=title,
            content=parsed_json,
            breadcrumbs=breadcrumbs
        )
        
        return {
            "epic_artifact_path": epic_artifact_path,
            "architecture_artifact_path": architecture_path,
            "artifact_id": str(artifact.id),
            "project_id": project_id,
            "epic_id": epic_id,
            "title": title
        }