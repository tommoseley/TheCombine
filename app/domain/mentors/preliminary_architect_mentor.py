"""
Preliminary Architect Mentor - Early discovery before PM decomposition.
"""

from typing import Dict, Any

from app.domain.mentors.base_mentor import (
    StreamingMentor,
    validate_required_fields
)


class PreliminaryArchitectMentor(StreamingMentor):
    """
    Preliminary Architect Mentor - Early discovery before PM decomposition.
    
    Performs architectural discovery BEFORE PM epic creation to:
    - Surface critical architectural questions
    - Identify constraints, risks, and dependencies
    - Propose candidate architectural directions (not final designs)
    - Establish guardrails that will shape PM epics and BA work
    
    Unique aspects:
    - Same role as ArchitectMentor, different task
    - Validates: preliminary_summary, project_name
    - Lighter output than full architect
    - Informs PM and BA work downstream
    """
    
    @property
    def role_name(self) -> str:
        return "architect"  # Same role as full architect
    
    @property
    def task_name(self) -> str:
        return "preliminary"  # Different task
    
    @property
    def artifact_type(self) -> str:
        return "architecture"
    
    async def build_user_message(self, request_data: Dict[str, Any]) -> str:
        project_content = request_data.get("project_content", {})
        
        project_name = project_content.get("name", "Project")
        description = project_content.get("description", "")
        
        return f"""Perform preliminary architectural discovery for the following project:

Project: {project_name}

Description:
{description}

Your goal is to:
1. Surface critical architectural questions that must be answered early
2. Identify constraints, risks, and dependencies
3. Propose candidate architectural directions (not final designs)
4. Establish guardrails that will shape PM epics and BA work

Focus on:
- What must be decided before detailed planning can begin
- Technical unknowns that could derail the project
- Integration points and external dependencies
- MVP guardrails and scope boundaries

Remember: Output ONLY valid JSON matching the schema. No markdown, no prose."""
    
    async def validate_response(
        self, 
        parsed_json: Dict[str, Any], 
        schema: Dict[str, Any]
    ) -> tuple[bool, str]:
        # Check for preliminary_summary
        is_valid, error = validate_required_fields(parsed_json, ["preliminary_summary"])
        if not is_valid:
            return is_valid, error
        
        # Should have project_name
        if "project_name" not in parsed_json:
            return False, "Missing required field: 'project_name'"
        
        return True, ""
    
    async def extract_title(
        self, 
        parsed_json: Dict[str, Any], 
        request_data: Dict[str, Any]
    ) -> str:
        project_name = parsed_json.get("project_name", "Project")
        return f"Preliminary Architecture: {project_name}"