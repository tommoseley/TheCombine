"""
Developer Mentor - Creates implementation code from user stories.
"""

from typing import Dict, Any

from app.domain.mentors.base_mentor import (
    StreamingMentor,
    validate_non_empty_array
)


class DeveloperMentor(StreamingMentor):
    """
    Developer Mentor - Creates implementation code from user stories.
    
    Unique aspects:
    - Validates: code_files array with file_path and content
    - Lower temperature for deterministic code
    """
    
    @property
    def role_name(self) -> str:
        return "developer"
    
    @property
    def task_name(self) -> str:
        return "implementation"
    
    @property
    def artifact_type(self) -> str:
        return "code"
    
    @property
    def preferred_model(self) -> str:
        return "claude-sonnet-4-20250514"
    
    async def build_user_message(self, request_data: Dict[str, Any]) -> str:
        story_content = request_data.get("story_content", {})
        architecture_content = request_data.get("architecture_content", {})
        
        story_title = story_content.get("title", "Story")
        user_story = story_content.get("user_story", "")
        acceptance_criteria = story_content.get("acceptance_criteria", [])
        technical_considerations = story_content.get("technical_considerations", [])
        
        criteria_text = "\n".join([f"{i+1}. {crit}" for i, crit in enumerate(acceptance_criteria)])
        tech_text = "\n".join([f"- {tc}" for tc in technical_considerations]) if technical_considerations else "None specified"
        
        # Extract architecture context
        arch_summary = architecture_content.get("architecture_summary", {})
        tech_stack = arch_summary.get("technology_stack", {})
        components = architecture_content.get("components", [])
        
        tech_stack_text = "\n".join([f"- {k}: {v}" for k, v in tech_stack.items()]) if tech_stack else "Use best practices"
        components_text = "\n".join([
            f"- {comp.get('name', 'Component')}: {comp.get('technologies', ['N/A'])[0] if comp.get('technologies') else 'N/A'}" 
            for comp in components[:5]
        ]) if components else "See architecture"
        
        return f"""Implement the following user story:

Story: {story_title}
{user_story}

Acceptance Criteria:
{criteria_text}

Technical Considerations:
{tech_text}

Technology Stack:
{tech_stack_text}

Relevant Components:
{components_text}

Provide a complete implementation including:
1. **Production Code**: Clean, well-structured, production-ready code
   - Follow SOLID principles
   - Include proper error handling
   - Add logging hooks

2. **Unit Tests**: Comprehensive test coverage
   - Test all acceptance criteria
   - Include edge cases
   - Mock external dependencies

3. **Documentation**:
   - Inline code comments for complex logic
   - Docstrings for public functions/classes

Code Quality Requirements:
- Type hints for all functions
- Proper exception handling
- Security best practices

Remember: Output ONLY valid JSON matching the schema with a "code_files" array."""
    
    async def validate_response(
        self, 
        parsed_json: Dict[str, Any], 
        schema: Dict[str, Any]
    ) -> tuple[bool, str]:
        # Check for non-empty code_files array
        is_valid, error = validate_non_empty_array(parsed_json, "code_files")
        if not is_valid:
            return is_valid, error
        
        # Validate each code file
        for idx, code_file in enumerate(parsed_json["code_files"]):
            file_num = idx + 1
            
            if not isinstance(code_file, dict):
                return False, f"File {file_num} must be an object"
            
            if "file_path" not in code_file or not code_file["file_path"].strip():
                return False, f"File {file_num} missing or empty 'file_path'"
            
            if "content" not in code_file or not code_file["content"].strip():
                return False, f"File {file_num} missing or empty 'content'"
        
        return True, ""
    
    async def create_artifact(
        self,
        request_data: Dict[str, Any],
        parsed_json: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        story_artifact_path = request_data.get("story_artifact_path")
        
        path_parts = story_artifact_path.split("/")
        if len(path_parts) != 3:
            raise ValueError(f"Invalid story path: {story_artifact_path}")
        
        project_id, epic_id, story_id = path_parts
        code_files = parsed_json.get("code_files", [])
        
        story_content = request_data.get("story_content", {})
        title = f"Implementation: {story_content.get('title', story_id)}"
        
        breadcrumbs = {
            "created_by": "developer_mentor",
            "task": self.task_name,
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
        
        artifact = await self.artifact_service.create_artifact(
            artifact_path=story_artifact_path,
            artifact_type="code",
            title=title,
            content=parsed_json,
            breadcrumbs=breadcrumbs
        )
        
        return {
            "story_artifact_path": story_artifact_path,
            "project_id": project_id,
            "epic_id": epic_id,
            "story_id": story_id,
            "total_files": len(code_files),
            "artifact_id": str(artifact.id),
            "title": title
        }