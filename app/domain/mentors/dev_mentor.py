"""
Developer Mentor - Extends StreamingMentor with Developer-specific logic

Transforms User Stories into code implementation with streaming progress updates.
"""

from typing import Dict, Any, List
from pydantic import BaseModel, Field

from app.domain.mentors.base_mentor import StreamingMentor, ProgressStep


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class DeveloperRequest(BaseModel):
    """Request to Developer Mentor"""
    story_artifact_path: str = Field(..., description="RSP-1 path to Story (e.g., 'PROJ/E001/S001')")
    model: str = Field(default="claude-sonnet-4-20250514", description="Model to use")
    max_tokens: int = Field(default=16384, description="Maximum tokens (very high for code)")
    temperature: float = Field(default=0.3, description="Temperature (low for deterministic code)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "story_artifact_path": "AUTH/E001/S001"
            }
        }


class CodeArtifact(BaseModel):
    """Individual code artifact created"""
    artifact_path: str
    artifact_id: str
    title: str
    file_path: str


# ============================================================================
# DEVELOPER MENTOR IMPLEMENTATION
# ============================================================================

class DeveloperMentor(StreamingMentor):
    """
    Developer Mentor - Creates implementation code from user stories
    
    Progress Steps:
    1. Reading development guidelines (5%)
    2. Loading code schema (8%)
    3. Loading story context (12%)
    4. Loading architecture context (18%)
    5. Analyzing technical requirements (25%)
    6. Planning implementation approach (32%)
    7. Writing production code (48%)
    8. Adding unit tests (62%)
    9. Creating documentation (76%)
    10. Parsing code artifacts (84%)
    11. Validating code structure (90%)
    12. Saving implementation (95%)
    13. Code ready for review! (100%)
    """
    
    @property
    def role_name(self) -> str:
        return "developer"
    
    @property
    def pipeline_id(self) -> str:
        return "execution"
    
    @property
    def phase_name(self) -> str:
        return "dev_phase"
    
    @property
    def progress_steps(self) -> List[ProgressStep]:
        """Developer-specific progress steps"""
        return [
            ProgressStep("building_prompt", "Reading development guidelines", "📋", 5),
            ProgressStep("loading_schema", "Loading code schema", "📄", 8),
            ProgressStep("loading_story", "Loading story context", "📖", 12),
            ProgressStep("loading_architecture", "Loading architecture context", "🏗️", 18),
            ProgressStep("calling_llm", "Analyzing technical requirements", "🤖", 25),
            ProgressStep("generating", "Planning implementation approach", "✨", 32),
            ProgressStep("streaming", "Writing production code", "💻", 48),
            ProgressStep("adding_tests", "Adding unit tests", "🧪", 62),
            ProgressStep("documenting", "Creating documentation", "📝", 76),
            ProgressStep("parsing", "Parsing code artifacts", "🔧", 84),
            ProgressStep("validating", "Validating code structure", "✅", 90),
            ProgressStep("saving", "Saving implementation", "💾", 95),
            ProgressStep("complete", "Code ready for review!", "🎉", 100),
            ProgressStep("error", "Something went wrong", "❌", 0),
            ProgressStep("validation_failed", "Validation issues detected", "⚠️", 90)
        ]
    
    async def build_user_message(self, request_data: Dict[str, Any]) -> str:
        """
        Build Developer-specific user message with story and architecture context
        """
        story_content = request_data.get("story_content", {})
        architecture_content = request_data.get("architecture_content", {})
        
        # Extract story details
        story_title = story_content.get("title", "Story")
        user_story = story_content.get("user_story", "")
        acceptance_criteria = story_content.get("acceptance_criteria", [])
        technical_considerations = story_content.get("technical_considerations", [])
        dependencies = story_content.get("dependencies", [])
        
        # Extract architecture details
        arch_summary = architecture_content.get("architecture_summary", {})
        tech_stack = arch_summary.get("technology_stack", {})
        components = architecture_content.get("components", [])
        data_model = architecture_content.get("data_model", {})
        interfaces = architecture_content.get("interfaces", [])
        
        # Format acceptance criteria
        criteria_text = "\n".join([f"{i+1}. {crit}" for i, crit in enumerate(acceptance_criteria)])
        
        # Format technical considerations
        tech_considerations_text = "\n".join([f"- {tc}" for tc in technical_considerations]) if technical_considerations else "None specified"
        
        # Format dependencies
        dependencies_text = "\n".join([f"- {dep}" for dep in dependencies]) if dependencies else "None"
        
        # Format technology stack
        tech_stack_text = "\n".join([f"- {k}: {v}" for k, v in tech_stack.items()]) if tech_stack else "Use best practices"
        
        # Format relevant components
        components_text = "\n".join([
            f"- {comp.get('name', 'Component')}: {comp.get('technologies', [])[0] if comp.get('technologies') else 'N/A'}" 
            for comp in components[:5]
        ]) if components else "See architecture"
        
        # Format data entities (if relevant)
        entities = data_model.get("entities", [])
        entities_text = "\n".join([
            f"- {entity.get('name', 'Entity')}: {', '.join(entity.get('key_attributes', []))}" 
            for entity in entities[:5]
        ]) if entities else "See architecture"
        
        return f"""Implement the following user story:

Story: {story_title}
{user_story}

Acceptance Criteria:
{criteria_text}

Technical Considerations:
{tech_considerations_text}

Dependencies:
{dependencies_text}

Technology Stack:
{tech_stack_text}

Relevant Components:
{components_text}

Data Model:
{entities_text}

Provide a complete implementation including:
1. **Production Code**: Clean, well-structured, production-ready code
   - Follow SOLID principles
   - Use design patterns where appropriate
   - Include proper error handling
   - Add logging and monitoring hooks

2. **Unit Tests**: Comprehensive test coverage
   - Test all acceptance criteria
   - Include edge cases
   - Mock external dependencies
   - Aim for 80%+ coverage

3. **Documentation**:
   - Inline code comments for complex logic
   - Docstrings for public functions/classes
   - README with setup and usage instructions

4. **Database Migrations** (if needed):
   - Schema changes
   - Seed data (if applicable)

5. **API Endpoints** (if applicable):
   - Request/response models
   - Validation
   - Error handling

Code Quality Requirements:
- Type hints for all functions
- Proper exception handling
- Security best practices (input validation, SQL injection prevention, etc.)
- Performance considerations (caching, query optimization)
- Follow the project's coding standards

Remember: Output ONLY valid JSON matching the schema. No markdown, no prose.
The JSON should contain a "code_files" array with objects containing "file_path" and "content" fields."""
    
    async def validate_response(
        self, 
        parsed_json: Dict[str, Any], 
        schema: Dict[str, Any]
    ) -> tuple[bool, str]:
        """
        Validate Developer code response
        
        Checks for:
        - code_files array exists
        - Each file has required fields
        - At least one production code file
        """
        # Check for code_files array
        if "code_files" not in parsed_json:
            return False, "Response must contain 'code_files' array"
        
        code_files = parsed_json.get("code_files", [])
        
        if not isinstance(code_files, list):
            return False, "Field 'code_files' must be an array"
        
        if len(code_files) == 0:
            return False, "Must provide at least one code file"
        
        # Validate each code file structure
        for idx, code_file in enumerate(code_files):
            file_num = idx + 1
            
            if not isinstance(code_file, dict):
                return False, f"File {file_num} must be an object"
            
            # Check required fields
            if "file_path" not in code_file:
                return False, f"File {file_num} missing 'file_path'"
            
            if "content" not in code_file:
                return False, f"File {file_num} missing 'content'"
            
            # Validate file_path is not empty
            file_path = code_file.get("file_path", "").strip()
            if not file_path:
                return False, f"File {file_num} has empty 'file_path'"
            
            # Validate content is not empty
            content = code_file.get("content", "").strip()
            if not content:
                return False, f"File {file_num} has empty 'content'"
        
        return True, ""
    
    async def create_artifact(
        self,
        request_data: Dict[str, Any],
        parsed_json: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create Developer code artifacts
        
        Creates artifacts for the implementation.
        
        Returns:
            Dictionary with:
            - story_artifact_path: Source story path
            - code_artifacts_created: List of created code artifacts
            - project_id: Extracted project ID
            - epic_id: Extracted epic ID
            - story_id: Extracted story ID
            - total_files: Number of code files
        """
        story_artifact_path = request_data.get("story_artifact_path")
        
        # Parse project, epic, and story from path (e.g., "PROJ/E001/S001")
        path_parts = story_artifact_path.split("/")
        if len(path_parts) != 3:
            raise ValueError(
                f"Invalid story path: {story_artifact_path}. Expected format: PROJECT/EPIC/STORY"
            )
        
        project_id, epic_id, story_id = path_parts
        
        # Get code files array
        code_files = parsed_json.get("code_files", [])
        
        # Create a single "code" artifact containing all files
        # (Alternative: create one artifact per file)
        implementation_path = story_artifact_path  # Same path as story
        
        # Extract title from story or use default
        story_content = request_data.get("story_content", {})
        title = f"Implementation: {story_content.get('title', story_id)}"
        
        # Create breadcrumbs
        breadcrumbs = {
            "created_by": "developer_mentor",
            "story_id": story_id,
            "epic_id": epic_id,
            "story_artifact_path": story_artifact_path,
            "total_files": len(code_files),
            "file_types": list(set([
                cf.get("file_path", "").split(".")[-1] 
                for cf in code_files 
                if "." in cf.get("file_path", "")
            ])),
            **metadata
        }
        
        # Create artifact with all code files
        artifact = await self.artifact_service.create_artifact(
            artifact_path=implementation_path,
            artifact_type="code",
            title=title,
            content=parsed_json,  # Entire response with code_files array
            breadcrumbs=breadcrumbs
        )
        
        # Build list of created artifacts
        created_artifacts = [{
            "artifact_path": implementation_path,
            "artifact_id": str(artifact.id),
            "title": title,
            "file_path": cf.get("file_path")
        } for cf in code_files]
        
        return {
            "story_artifact_path": story_artifact_path,
            "code_artifacts_created": created_artifacts,
            "project_id": project_id,
            "epic_id": epic_id,
            "story_id": story_id,
            "total_files": len(code_files),
            "implementation_artifact_path": implementation_path,
            "implementation_artifact_id": str(artifact.id)
        }