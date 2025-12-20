"""
Story service for web UI - Document-centric version.

Stories are documents with doc_type_id = 'story'.
Related to epics via document_relations (derived_from).
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
from uuid import UUID
import zipfile
import io
import json

from app.api.models import Document, DocumentRelation, Project


class StoryService:
    """Service for story-related operations using Document model."""
    
    async def get_story_full(
        self,
        db: AsyncSession,
        story_id: UUID
    ) -> Dict[str, Any]:
        """Get complete story details for main content view."""
        # Get story document
        story = await db.get(Document, story_id)
        if not story or story.doc_type_id != 'story':
            raise ValueError(f"Story not found: {story_id}")
        
        # Get project
        project = await db.get(Project, story.space_id)
        project_name = project.name if project else "Unknown Project"
        
        # Get parent epic (if any) via derived_from relation
        epic_query = (
            select(Document)
            .join(DocumentRelation, DocumentRelation.to_document_id == Document.id)
            .where(DocumentRelation.from_document_id == story_id)
            .where(DocumentRelation.relation_type == 'derived_from')
            .where(Document.doc_type_id == 'epic')
        )
        result = await db.execute(epic_query)
        epic = result.scalar_one_or_none()
        
        # Parse acceptance criteria from content
        acceptance_criteria = []
        if story.content and isinstance(story.content, dict):
            acceptance_criteria = story.content.get("acceptance_criteria", [])
        
        return {
            "story_uuid": str(story.id),
            "epic_uuid": str(epic.id) if epic else None,
            "epic_name": epic.title if epic else "No Epic",
            "project_uuid": str(story.space_id),
            "project_name": project_name,
            "title": story.title,
            "description": story.summary or "",
            "acceptance_criteria": acceptance_criteria,
            "status": story.status,
            "is_stale": story.is_stale,
            "has_code": bool(story.content and story.content.get("files")),
            "has_tests": bool(story.content and story.content.get("tests")),
            "created_at": story.created_at.isoformat() if story.created_at else "",
            "updated_at": story.updated_at.isoformat() if story.updated_at else ""
        }
    
    async def get_code_deliverables(
        self,
        db: AsyncSession,
        story_id: UUID
    ) -> Dict[str, Any]:
        """Get code deliverables for a story."""
        # Get story document
        story = await db.get(Document, story_id)
        if not story or story.doc_type_id != 'story':
            raise ValueError(f"Story not found: {story_id}")
        
        # Get project
        project = await db.get(Project, story.space_id)
        project_name = project.name if project else "Unknown Project"
        
        # Get parent epic
        epic_query = (
            select(Document)
            .join(DocumentRelation, DocumentRelation.to_document_id == Document.id)
            .where(DocumentRelation.from_document_id == story_id)
            .where(DocumentRelation.relation_type == 'derived_from')
            .where(Document.doc_type_id == 'epic')
        )
        result = await db.execute(epic_query)
        epic = result.scalar_one_or_none()
        
        # Extract files from content
        files = []
        if story.content and isinstance(story.content, dict):
            if "files" in story.content:
                files = story.content["files"]
            elif "code" in story.content:
                # Single code block
                files = [{
                    "filepath": f"story_{story.id}.code",
                    "content": story.content["code"],
                    "language": story.content.get("language", "text"),
                    "description": ""
                }]
            elif story.content:
                # Treat entire content as single JSON file
                files = [{
                    "filepath": f"story_{story.id}.json",
                    "content": json.dumps(story.content, indent=2),
                    "language": "json",
                    "description": ""
                }]
        
        return {
            "story_uuid": str(story.id),
            "story_title": story.title,
            "epic_uuid": str(epic.id) if epic else None,
            "epic_name": epic.title if epic else "No Epic",
            "project_uuid": str(story.space_id),
            "project_name": project_name,
            "files": files,
            "has_code": len(files) > 0
        }
    
    async def get_code_file(
        self,
        db: AsyncSession,
        story_id: UUID,
        file_index: int
    ) -> Dict[str, Any]:
        """Get a specific code file by index."""
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
        story_id: UUID
    ) -> io.BytesIO:
        """Create a zip file with all code deliverables."""
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
    
    async def list_stories_for_project(
        self,
        db: AsyncSession,
        project_id: UUID
    ) -> list[Dict[str, Any]]:
        """List all stories for a project."""
        query = (
            select(Document)
            .where(Document.space_type == 'project')
            .where(Document.space_id == project_id)
            .where(Document.doc_type_id == 'story')
            .where(Document.is_latest == True)
            .order_by(Document.created_at)
        )
        result = await db.execute(query)
        stories = result.scalars().all()
        
        return [
            {
                "story_uuid": str(story.id),
                "title": story.title,
                "status": story.status,
                "is_stale": story.is_stale,
                "has_code": bool(story.content and story.content.get("files")),
                "created_at": story.created_at.isoformat() if story.created_at else ""
            }
            for story in stories
        ]


# Singleton instance
story_service = StoryService()