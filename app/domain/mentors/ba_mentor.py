"""
BA Mentor - Creates user stories from epic and architecture.
"""

from typing import Dict, Any

from app.domain.mentors.base_mentor import (
    StreamingMentor,
    validate_non_empty_array
)


class BAMentor(StreamingMentor):
    """
    Business Analyst Mentor - Creates user stories from epic and architecture.
    
    Unique aspects:
    - Creates MULTIPLE artifacts (one per story)
    - Uses id_generator for story IDs
    - Validates: stories array with required fields
    """
    
    @property
    def role_name(self) -> str:
        return "ba"
    
    @property
    def task_name(self) -> str:
        return "story_breakdown"
    
    @property
    def artifact_type(self) -> str:
        return "story"
    
    async def build_user_message(self, request_data: Dict[str, Any]) -> str:
        epic_content = request_data.get("epic_content", {})
        architecture_content = request_data.get("architecture_content", {})
        
        epic_title = epic_content.get("title", "Epic")
        epic_objectives = epic_content.get("objectives", [])
        epic_description = epic_content.get("description", "")
        
        arch_summary = architecture_content.get("architecture_summary", {})
        arch_style = arch_summary.get("style", "N/A")
        components = architecture_content.get("components", [])
        
        objectives_text = "\n".join([f"- {obj}" for obj in epic_objectives])
        components_text = "\n".join([
            f"- {comp.get('name', 'Component')}: {comp.get('purpose', '')}" 
            for comp in components[:10]
        ])
        
        return f"""Break down the following epic into detailed user stories:

Epic: {epic_title}

Description:
{epic_description}

Objectives:
{objectives_text}

Architecture Style: {arch_style}

Components:
{components_text if components_text else "- See architecture for details"}

Create comprehensive user stories with:
1. Clear user story in "As a [role], I want [feature], so that [benefit]" format
2. Detailed acceptance criteria (test-driven)
3. Technical considerations from the architecture
4. Dependencies on other stories or components
5. Estimated complexity (1-5 story points)

Remember: Output ONLY valid JSON matching the schema. No markdown, no prose."""
    
    async def validate_response(
        self, 
        parsed_json: Dict[str, Any], 
        schema: Dict[str, Any]
    ) -> tuple[bool, str]:
        # Check for non-empty stories array
        is_valid, error = validate_non_empty_array(parsed_json, "stories")
        if not is_valid:
            return is_valid, error
        
        # Validate each story
        for idx, story in enumerate(parsed_json["stories"]):
            story_num = idx + 1
            
            if not isinstance(story, dict):
                return False, f"Story {story_num} must be an object"
            
            if "title" not in story:
                return False, f"Story {story_num} missing 'title'"
            
            if "user_story" not in story:
                return False, f"Story {story_num} missing 'user_story'"
            
            if "acceptance_criteria" not in story:
                return False, f"Story {story_num} missing 'acceptance_criteria'"
            
            ac = story.get("acceptance_criteria")
            if not isinstance(ac, list) or len(ac) == 0:
                return False, f"Story {story_num} must have at least one acceptance criterion"
        
        return True, ""
    
    async def create_artifact(
        self,
        request_data: Dict[str, Any],
        parsed_json: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create multiple story artifacts - one per story in response."""
        epic_artifact_path = request_data.get("epic_artifact_path")
        architecture_artifact_path = request_data.get("architecture_artifact_path")
        
        path_parts = epic_artifact_path.split("/")
        if len(path_parts) != 2:
            raise ValueError(f"Invalid epic path: {epic_artifact_path}")
        
        project_id, epic_id = path_parts
        stories = parsed_json.get("stories", [])
        created_stories = []
        
        for idx, story_data in enumerate(stories):
            if self.id_generator is None:
                raise ValueError("No ID generator provided for story creation")
            
            story_id = await self.id_generator(epic_id)
            story_path = f"{project_id}/{epic_id}/{story_id}"
            title = story_data.get("title") or f"Story {idx+1}"
            
            breadcrumbs = {
                "created_by": "ba_mentor",
                "task": self.task_name,
                "epic_id": epic_id,
                "epic_artifact_path": epic_artifact_path,
                "architecture_artifact_path": architecture_artifact_path,
                "story_number": idx + 1,
                "total_stories": len(stories),
                **metadata
            }
            
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