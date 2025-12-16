"""
Architect Mentor - Creates architectural specifications from epics.
"""

from typing import Dict, Any

from app.domain.mentors.base_mentor import (
    StreamingMentor,
    validate_required_fields,
    validate_non_empty_array
)


class ArchitectMentor(StreamingMentor):
    """
    Architect Mentor - Creates final architectural specifications.
    
    Unique aspects:
    - Validates: architecture_summary, components array
    - Supports 2-part and 3-part paths
    """
    
    @property
    def role_name(self) -> str:
        return "architect"
    
    @property
    def task_name(self) -> str:
        return "final"
    
    @property
    def artifact_type(self) -> str:
        return "architecture"
    
    async def build_user_message(self, request_data: Dict[str, Any]) -> str:
        epic_content = request_data.get("epic_content", {})
        
        epic_title = epic_content.get("title", "Epic")
        epic_objectives = epic_content.get("objectives", [])
        epic_description = epic_content.get("description", "")
        user_stories = epic_content.get("user_stories", [])
        
        objectives_text = "\n".join([f"- {obj}" for obj in epic_objectives])
        
        stories_text = ""
        if user_stories:
            stories_text = "\n\nUser Stories:\n" + "\n".join([
                f"- {story.get('title', 'Story')}: {story.get('description', '')}" 
                for story in user_stories[:5]
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
        # Check for architecture_summary
        is_valid, error = validate_required_fields(parsed_json, ["architecture_summary"])
        if not is_valid:
            return is_valid, error
        
        # Check for non-empty components
        is_valid, error = validate_non_empty_array(parsed_json, "components")
        if not is_valid:
            return is_valid, error
        
        # Validate component structure
        for idx, component in enumerate(parsed_json["components"]):
            if not isinstance(component, dict):
                return False, f"Component {idx+1} must be an object"
            if "name" not in component:
                return False, f"Component {idx+1} missing 'name'"
            if "purpose" not in component:
                return False, f"Component {idx+1} missing 'purpose'"
        
        return True, ""
    
    async def extract_title(
        self, 
        parsed_json: Dict[str, Any], 
        request_data: Dict[str, Any]
    ) -> str:
        arch_summary = parsed_json.get("architecture_summary", {})
        return arch_summary.get("title", "Architecture")