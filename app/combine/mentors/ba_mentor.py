"""
BA Mentor - Extends StreamingMentor with BA-specific logic

Transforms Epic + Architecture into User Stories with streaming progress updates.
"""

from typing import Dict, Any, List
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.combine.mentors.base_mentor import StreamingMentor, ProgressStep
from app.combine.models import Artifact
from app.combine.utils.id_generators import generate_story_id


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class BARequest(BaseModel):
    """Request to BA Mentor"""
    epic_artifact_path: str = Field(..., description="RSP-1 path to Epic (e.g., 'PROJ/E001')")
    architecture_artifact_path: str = Field(
        ..., 
        description="RSP-1 path to Architecture (e.g., 'PROJ/E001' - same as epic)"
    )
    model: str = Field(default="claude-sonnet-4-20250514", description="Model to use")
    max_tokens: int = Field(default=8192, description="Maximum tokens (higher for stories)")
    temperature: float = Field(default=0.6, description="Temperature for generation")
    
    class Config:
        json_schema_extra = {
            "example": {
                "epic_artifact_path": "AUTH/E001",
                "architecture_artifact_path": "AUTH/E001"
            }
        }


class StoryArtifact(BaseModel):
    """Individual story artifact created"""
    artifact_path: str
    artifact_id: str
    title: str


# ============================================================================
# BA MENTOR IMPLEMENTATION
# ============================================================================

class BAMentor(StreamingMentor):
    """
    Business Analyst Mentor - Creates user stories from epic and architecture
    
    Progress Steps:
    1. Reading BA guidelines (8%)
    2. Loading story schema (12%)
    3. Loading epic context (18%)
    4. Loading architecture context (24%)
    5. Analyzing requirements (30%)
    6. Breaking down into stories (45%)
    7. Defining acceptance criteria (60%)
    8. Adding technical details (75%)
    9. Parsing stories JSON (82%)
    10. Validating story structure (88%)
    11. Creating story artifacts (95%)
    12. Stories created successfully! (100%)
    """
    
    @property
    def role_name(self) -> str:
        return "ba"
    
    @property
    def pipeline_id(self) -> str:
        return "execution"
    
    @property
    def phase_name(self) -> str:
        return "ba_phase"
    
    @property
    def progress_steps(self) -> List[ProgressStep]:
        """BA-specific progress steps"""
        return [
            ProgressStep("building_prompt", "Reading BA guidelines", "📋", 8),
            ProgressStep("loading_schema", "Loading story schema", "🔍", 12),
            ProgressStep("loading_epic", "Loading epic context", "📖", 18),
            ProgressStep("loading_architecture", "Loading architecture context", "🏗️", 24),
            ProgressStep("calling_llm", "Analyzing requirements", "🤖", 30),
            ProgressStep("generating", "Breaking down into stories", "✨", 45),
            ProgressStep("streaming", "Defining acceptance criteria", "💭", 60),
            ProgressStep("adding_details", "Adding technical details", "📝", 75),
            ProgressStep("parsing", "Parsing stories JSON", "🔧", 82),
            ProgressStep("validating", "Validating story structure", "✅", 88),
            ProgressStep("saving", "Creating story artifacts", "💾", 95),
            ProgressStep("complete", "Stories created successfully!", "🎉", 100),
            ProgressStep("error", "Something went wrong", "❌", 0),
            ProgressStep("validation_failed", "Validation issues detected", "⚠️", 88)
        ]
    
    async def build_user_message(self, request_data: Dict[str, Any]) -> str:
        """
        Build BA-specific user message with epic and architecture context
        """
        epic_content = request_data.get("epic_content", {})
        architecture_content = request_data.get("architecture_content", {})
        
        # Extract epic details
        epic_title = epic_content.get("title", "Epic")
        epic_objectives = epic_content.get("objectives", [])
        epic_description = epic_content.get("description", "")
        
        # Extract architecture details
        arch_summary = architecture_content.get("architecture_summary", {})
        arch_style = arch_summary.get("style", "N/A")
        components = architecture_content.get("components", [])
        data_model = architecture_content.get("data_model", {})
        
        # Format objectives
        objectives_text = "\n".join([f"- {obj}" for obj in epic_objectives])
        
        # Format components
        components_text = "\n".join([
            f"- {comp.get('name', 'Component')}: {comp.get('purpose', '')}" 
            for comp in components[:10]  # Limit to first 10
        ])
        
        # Format data entities
        entities = data_model.get("entities", [])
        entities_text = "\n".join([
            f"- {entity.get('name', 'Entity')}: {entity.get('description', '')}" 
            for entity in entities[:10]  # Limit to first 10
        ])
        
        return f"""Break down the following epic into detailed user stories:

Epic: {epic_title}

Description:
{epic_description}

Objectives:
{objectives_text}

Architecture Context:
Style: {arch_style}

Components:
{components_text if components_text else "- See architecture for details"}

Data Model:
{entities_text if entities_text else "- See architecture for details"}

Create comprehensive user stories with:
1. Clear user story in "As a [role], I want [feature], so that [benefit]" format
2. Detailed acceptance criteria (test-driven)
3. Technical considerations from the architecture
4. Dependencies on other stories or components
5. Estimated complexity (1-5 story points)

Ensure stories are:
- Small enough to implement in one sprint
- Testable with clear acceptance criteria
- Aligned with architecture components
- Properly sequenced with dependencies

Remember: Output ONLY valid JSON matching the schema. No markdown, no prose."""
    
    async def validate_response(
        self, 
        parsed_json: Dict[str, Any], 
        schema: Dict[str, Any]
    ) -> tuple[bool, str]:
        """
        Validate BA stories response
        
        Checks for:
        - stories array exists
        - Each story has required fields
        - Acceptance criteria are present
        """
        # Check for stories array
        if "stories" not in parsed_json:
            return False, "Response must contain 'stories' array"
        
        stories = parsed_json.get("stories", [])
        
        if not isinstance(stories, list):
            return False, "Field 'stories' must be an array"
        
        if len(stories) == 0:
            return False, "Must create at least one story"
        
        # Validate each story structure
        for idx, story in enumerate(stories):
            story_num = idx + 1
            
            if not isinstance(story, dict):
                return False, f"Story {story_num} must be an object"
            
            # Check required fields
            if "title" not in story:
                return False, f"Story {story_num} missing 'title'"
            
            if "user_story" not in story:
                return False, f"Story {story_num} missing 'user_story'"
            
            if "acceptance_criteria" not in story:
                return False, f"Story {story_num} missing 'acceptance_criteria'"
            
            # Validate acceptance criteria
            acceptance_criteria = story.get("acceptance_criteria")
            if not isinstance(acceptance_criteria, list):
                return False, f"Story {story_num} 'acceptance_criteria' must be an array"
            
            if len(acceptance_criteria) == 0:
                return False, f"Story {story_num} must have at least one acceptance criterion"
        
        return True, ""
    
    async def create_artifact(
        self,
        request_data: Dict[str, Any],
        parsed_json: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create BA story artifacts
        
        Creates one artifact per story in the response.
        
        Returns:
            Dictionary with:
            - epic_artifact_path: Source epic path
            - architecture_artifact_path: Source architecture path
            - stories_created: List of created story artifacts
            - project_id: Extracted project ID
            - epic_id: Extracted epic ID
        """
        epic_artifact_path = request_data.get("epic_artifact_path")
        architecture_artifact_path = request_data.get("architecture_artifact_path")
        
        # Parse project and epic from path (e.g., "PROJ/E001")
        path_parts = epic_artifact_path.split("/")
        if len(path_parts) != 2:
            raise ValueError(f"Invalid epic path: {epic_artifact_path}. Expected format: PROJECT/EPIC")
        
        project_id, epic_id = path_parts
        
        # Get stories array
        stories = parsed_json.get("stories", [])
        created_stories = []
        
        # Create an artifact for each story
        for idx, story_data in enumerate(stories):
            # Generate story ID
            story_id = await generate_story_id(project_id, epic_id, self.db)
            story_path = f"{project_id}/{epic_id}/{story_id}"
            
            # Extract title
            title = story_data.get("title") or f"Story {idx+1}"
            
            # Create breadcrumbs
            breadcrumbs = {
                "created_by": "ba_mentor",
                "epic_id": epic_id,
                "epic_artifact_path": epic_artifact_path,
                "architecture_artifact_path": architecture_artifact_path,
                "story_number": idx + 1,
                "total_stories": len(stories),
                **metadata
            }
            
            # Create artifact
            artifact = await self.artifact_service.create_artifact(
                artifact_path=story_path,
                artifact_type="story",
                title=title,
                content=story_data,
                breadcrumbs=breadcrumbs
            )
            
            created_stories.append({
                "artifact_path": story_path,
                "artifact_id": str(artifact.id),
                "title": title,
                "story_id": story_id
            })
        
        return {
            "epic_artifact_path": epic_artifact_path,
            "architecture_artifact_path": architecture_artifact_path,
            "stories_created": created_stories,
            "project_id": project_id,
            "epic_id": epic_id,
            "total_stories": len(created_stories)
        }
    
    async def _load_epic_content(self, epic_artifact_path: str) -> Dict[str, Any]:
        """
        Helper method to load epic content from database
        """
        query = (
            select(Artifact)
            .where(Artifact.artifact_path == epic_artifact_path)
            .where(Artifact.artifact_type == "epic")
        )
        
        result = await self.db.execute(query)
        epic_artifact = result.scalar_one_or_none()
        
        if not epic_artifact:
            raise ValueError(f"Epic not found at path: {epic_artifact_path}")
        
        return epic_artifact.content or {}
    
    async def _load_architecture_content(self, architecture_artifact_path: str) -> Dict[str, Any]:
        """
        Helper method to load architecture content from database
        """
        query = (
            select(Artifact)
            .where(Artifact.artifact_path == architecture_artifact_path)
            .where(Artifact.artifact_type == "architecture")
        )
        
        result = await self.db.execute(query)
        arch_artifact = result.scalar_one_or_none()
        
        if not arch_artifact:
            raise ValueError(f"Architecture not found at path: {architecture_artifact_path}")
        
        return arch_artifact.content or {}