"""
Story service for web UI
Maps story_id in Artifact model to Story concepts for UI
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
import zipfile
import io
import json

# Import existing models
from app.api.models import Artifact, Project


class StoryService:
    """Service for story-related operations (maps to story_id in Artifact)"""
    
    async def get_story_full(
        self,
        db: AsyncSession,
        story_id: str
    ) -> Dict[str, Any]:
        """Get complete story details for main content view"""
        # Get story artifact
        story_query = (
            select(Artifact)
            .where(Artifact.story_id == story_id)
            .where(Artifact.artifact_type == 'story')
        )
        story_result = await db.execute(story_query)
        story = story_result.scalar_one()
        
        # Get project
        proj_query = select(Project).where(Project.project_id == story.project_id)
        proj_result = await db.execute(proj_query)
        project = proj_result.scalar_one()
        
        # Try to parse acceptance criteria from content
        acceptance_criteria = []
        if story.content and isinstance(story.content, dict):
            acceptance_criteria = story.content.get("acceptance_criteria", [])
        
        return {
            "story_uuid": story.story_id,
            "epic_uuid": story.epic_id,
            "epic_name": f"Epic {story.epic_id}" if story.epic_id else "Unknown Epic",
            "project_uuid": story.project_id,
            "project_name": project.name or "Unknown Project",
            "title": story.title or f"Story {story.story_id}",
            "description": "",
            "acceptance_criteria": acceptance_criteria,
            "status": story.status or "pending",
            "has_code": bool(story.content and story.content != {}),
            "has_tests": False,
            "created_at": story.created_at.isoformat() if story.created_at else "",
            "updated_at": story.updated_at.isoformat() if story.updated_at else ""
        }
    
    async def get_code_deliverables(
        self,
        db: AsyncSession,
        story_id: str
    ) -> Dict[str, Any]:
        """Get code deliverables for a story"""
        # Get story artifact
        story_query = (
            select(Artifact)
            .where(Artifact.story_id == story_id)
            .where(Artifact.artifact_type == 'story')
        )
        story_result = await db.execute(story_query)
        story = story_result.scalar_one()
        
        # Get project
        proj_query = select(Project).where(Project.project_id == story.project_id)
        proj_result = await db.execute(proj_query)
        project = proj_result.scalar_one()
        
        files = []
        if story.content:
            # Try to parse as structured content with files
            if isinstance(story.content, dict):
                if "files" in story.content:
                    files = story.content["files"]
                elif "code" in story.content:
                    # Single code block
                    files = [{
                        "filepath": f"{story.artifact_path}.code",
                        "content": story.content["code"],
                        "language": story.content.get("language", "text"),
                        "description": ""
                    }]
                else:
                    # Treat entire content as single JSON file
                    files = [{
                        "filepath": f"{story.artifact_path}.json",
                        "content": json.dumps(story.content, indent=2),
                        "language": "json",
                        "description": ""
                    }]
            else:
                # String content - treat as single file
                files = [{
                    "filepath": f"{story.artifact_path}.txt",
                    "content": str(story.content),
                    "language": "text",
                    "description": ""
                }]
        
        return {
            "story_uuid": story.story_id,
            "story_title": story.title or f"Story {story.story_id}",
            "epic_uuid": story.epic_id,
            "epic_name": f"Epic {story.epic_id}" if story.epic_id else "Unknown Epic",
            "project_uuid": story.project_id,
            "project_name": project.name or "Unknown Project",
            "files": files,
            "has_code": len(files) > 0
        }
    
    async def get_code_file(
        self,
        db: AsyncSession,
        story_id: str,
        file_index: int
    ) -> Dict[str, Any]:
        """Get a specific code file by index"""
        code_data = await self.get_code_deliverables(db, story_id)
        
        if not code_data["files"] or file_index >= len(code_data["files"]):
            raise ValueError(f"File index {file_index} not found")
        
        file_info = code_data["files"][file_index]
        
        return {
            "story_uuid": code_data["story_uuid"],
            "story_title": code_data["story_title"],
            "file": file_info
        }
    
    async def create_code_zip(
        self,
        db: AsyncSession,
        story_id: str
    ) -> io.BytesIO:
        """Create a zip file with all code deliverables"""
        code_data = await self.get_code_deliverables(db, story_id)
        
        # Create zip in memory
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add README
            readme_content = f"""# {code_data['story_title']}

Project: {code_data['project_name']}
Epic: {code_data['epic_name']}
Story ID: {code_data['story_uuid']}

## Files Included

"""
            for file_info in code_data["files"]:
                readme_content += f"- {file_info['filepath']}\n"
            
            zip_file.writestr("README.md", readme_content)
            
            # Add all code files
            for file_info in code_data["files"]:
                filepath = file_info.get("filepath", "output.txt")
                content = file_info.get("content", "")
                zip_file.writestr(filepath, content)
        
        zip_buffer.seek(0)
        return zip_buffer


# Singleton instance
story_service = StoryService()