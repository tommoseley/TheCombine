"""
PM Mentor - Creates epic definitions from user queries.
"""

from typing import Dict, Any

from app.domain.mentors.base_mentor import (
    StreamingMentor,
    validate_non_empty_array
)


class PMMentor(StreamingMentor):
    """
    Product Manager Mentor - Creates epic definitions from user queries.
    
    Unique aspects:
    - Uses id_generator to create epic IDs
    - Validates: title/epic_id, objectives array
    """
    
    @property
    def role_name(self) -> str:
        return "pm"
    
    @property
    def task_name(self) -> str:
        return "epic_creation"
    
    @property
    def artifact_type(self) -> str:
        return "epic"
    
    async def build_user_message(self, request_data: Dict[str, Any]) -> str:
        user_query = request_data.get("user_query", "")
        return f"""Create an Epic definition for the following user request:

{user_query}

Remember: Output ONLY valid JSON matching the schema. No markdown, no prose."""
    
    async def validate_response(
        self, 
        parsed_json: Dict[str, Any], 
        schema: Dict[str, Any]
    ) -> tuple[bool, str]:
        # Must have title or epic_id
        if "title" not in parsed_json and "epic_id" not in parsed_json:
            return False, "Missing required field: 'title' or 'epic_id'"
        
        # Must have non-empty objectives
        return validate_non_empty_array(parsed_json, "objectives")
    
    async def build_artifact_path(self, request_data: Dict[str, Any]) -> str:
        project_id = request_data.get("project_id")
        if not project_id:
            raise ValueError("project_id required for PM mentor")
        
        if self.id_generator:
            epic_id = await self.id_generator(project_id)
            return f"{project_id}/{epic_id}"
        
        raise ValueError("No ID generator provided for PM mentor")
    
    async def create_artifact(
        self,
        request_data: Dict[str, Any],
        parsed_json: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        # Generate epic_id if not in response
        project_id = request_data.get("project_id")
        epic_id = parsed_json.get("epic_id")
        
        if not epic_id:
            if self.id_generator is None:
                raise ValueError("No ID generator provided and epic_id not in response")
            epic_id = await self.id_generator(project_id)
            parsed_json["epic_id"] = epic_id
        
        epic_path = f"{project_id}/{epic_id}"
        title = parsed_json.get("title") or parsed_json.get("epic_title") or f"Epic {epic_id}"
        
        breadcrumbs = {
            "created_by": "pm_mentor",
            "task": self.task_name,
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