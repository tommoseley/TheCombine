"""
Epic service for web UI
Maps epic_id in Artifact model to Epic concepts for UI
"""

from sqlalchemy import select, func, distinct, and_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List

# Import existing models
from app.combine.models import Artifact, Project


class EpicService:
    """Service for epic-related operations (maps to epic_id in Artifact)"""
    
    async def get_epic_summary(
        self,
        db: AsyncSession,
        epic_id: str
    ) -> Dict[str, Any]:
        """Get basic epic info for collapsed tree node"""
        # Get epic artifact
        epic_query = (
            select(Artifact)
            .where(Artifact.epic_id == epic_id)
            .where(Artifact.artifact_type == 'epic')
            .order_by(Artifact.created_at.desc())
        )
        epic_result = await db.execute(epic_query)
        epic = epic_result.scalar_one()
        
        # Count stories in this epic
        story_count_query = (
            select(func.count(distinct(Artifact.story_id)))
            .where(Artifact.epic_id == epic_id)
            .where(Artifact.story_id.isnot(None))
        )
        story_count_result = await db.execute(story_count_query)
        story_count = story_count_result.scalar()
        
        return {
            "epic_uuid": epic.epic_id,
            "name": epic.title or f"Epic {epic.epic_id}",
            "description": "",
            "status": epic.status or "pending",
            "story_count": story_count or 0
        }
    
    async def get_epic_with_stories(
        self,
        db: AsyncSession,
        epic_id: str
    ) -> Dict[str, Any]:
        """Get epic with story list for expanded tree node"""
        # Get epic artifact
        epic_query = (
            select(Artifact)
            .where(Artifact.epic_id == epic_id)
            .where(Artifact.artifact_type == 'epic')
        )
        epic_result = await db.execute(epic_query)
        epic = epic_result.scalar_one()
        
        # Get all stories in this epic
        stories_query = (
            select(Artifact)
            .where(Artifact.epic_id == epic_id)
            .where(Artifact.artifact_type == 'story')
            .order_by(Artifact.story_id)
        )
        stories_result = await db.execute(stories_query)
        stories = stories_result.scalars().all()
        
        return {
            "epic_uuid": epic.epic_id,
            "name": epic.title or f"Epic {epic.epic_id}",
            "description": "",
            "status": epic.status or "pending",
            "story_count": len(stories),
            "stories": [
                {
                    "story_uuid": story.story_id,
                    "title": story.title or f"Story {story.story_id}",
                    "status": story.status or "pending",
                    "has_code": bool(story.content and story.content != {})
                }
                for story in stories
            ]
        }
    
    async def get_epic_full(
        self,
        db: AsyncSession,
        epic_id: str
    ) -> Dict[str, Any]:
        """Get complete epic details for main content view"""
        # Get epic artifact with project
        epic_query = (
            select(Artifact)
            .where(Artifact.epic_id == epic_id)
            .where(Artifact.artifact_type == 'epic')
        )
        epic_result = await db.execute(epic_query)
        epic = epic_result.scalar_one()
        
        # Get project
        proj_query = select(Project).where(Project.project_id == epic.project_id)
        proj_result = await db.execute(proj_query)
        project = proj_result.scalar_one()
        
        # Get story statistics
        stories_query = (
            select(Artifact)
            .where(Artifact.epic_id == epic_id)
            .where(Artifact.artifact_type == 'story')
        )
        stories_result = await db.execute(stories_query)
        stories = stories_result.scalars().all()
        
        total_stories = len(stories)
        completed_stories = sum(1 for s in stories if s.status == "complete")
        in_progress_stories = sum(1 for s in stories if s.status == "in_progress")
        
        return {
            "epic_uuid": epic.epic_id,
            "project_uuid": epic.project_id,
            "project_name": project.name or "Unknown Project",
            "name": epic.title or f"Epic {epic.epic_id}",
            "description": "",
            "status": epic.status or "pending",
            "created_at": epic.created_at.isoformat() if epic.created_at else "",
            "updated_at": epic.updated_at.isoformat() if epic.updated_at else "",
            "total_stories": total_stories,
            "completed_stories": completed_stories,
            "in_progress_stories": in_progress_stories,
            "pending_stories": total_stories - completed_stories - in_progress_stories
        }
    
    async def get_stories(
        self,
        db: AsyncSession,
        epic_id: str
    ) -> Dict[str, Any]:
        """Get all stories for an epic with details"""
        # Get epic
        epic_query = (
            select(Artifact)
            .where(Artifact.epic_id == epic_id)
            .where(Artifact.artifact_type == 'epic')
        )
        epic_result = await db.execute(epic_query)
        epic = epic_result.scalar_one()
        
        # Get project
        proj_query = select(Project).where(Project.project_id == epic.project_id)
        proj_result = await db.execute(proj_query)
        project = proj_result.scalar_one()
        
        # Get all stories
        stories_query = (
            select(Artifact)
            .where(Artifact.epic_id == epic_id)
            .where(Artifact.artifact_type == 'story')
            .order_by(Artifact.story_id)
        )
        stories_result = await db.execute(stories_query)
        stories_list = stories_result.scalars().all()
        
        return {
            "epic_uuid": epic.epic_id,
            "epic_name": epic.title or f"Epic {epic.epic_id}",
            "project_uuid": epic.project_id,
            "project_name": project.name or "Unknown Project",
            "stories": [
                {
                    "story_uuid": story.story_id,
                    "title": story.title or f"Story {story.story_id}",
                    "description": "",
                    "status": story.status or "pending",
                    "has_code": bool(story.content and story.content != {}),
                    "has_tests": False,
                    "acceptance_criteria_count": 0,
                    "created_at": story.created_at.isoformat() if story.created_at else ""
                }
                for story in stories_list
            ],
            "total_count": len(stories_list)
        }
    
    async def get_epic_code(
        self,
        db: AsyncSession,
        epic_id: str
    ) -> Dict[str, Any]:
        """Get all code deliverables across all stories in an epic"""
        # Get epic
        epic_query = (
            select(Artifact)
            .where(Artifact.epic_id == epic_id)
            .where(Artifact.artifact_type == 'epic')
        )
        epic_result = await db.execute(epic_query)
        epic = epic_result.scalar_one()
        
        # Get project
        proj_query = select(Project).where(Project.project_id == epic.project_id)
        proj_result = await db.execute(proj_query)
        project = proj_result.scalar_one()
        
        # Get all stories with code
        stories_query = (
            select(Artifact)
            .where(Artifact.epic_id == epic_id)
            .where(Artifact.artifact_type == 'story')
        )
        stories_result = await db.execute(stories_query)
        stories = stories_result.scalars().all()
        
        # Collect all code files
        all_files = []
        for story in stories:
            if story.content:
                # Check if content has files array
                if isinstance(story.content, dict) and "files" in story.content:
                    for file_info in story.content["files"]:
                        all_files.append({
                            "story_uuid": story.story_id,
                            "story_title": story.title or f"Story {story.story_id}",
                            "filepath": file_info.get("filepath", "unknown"),
                            "content": file_info.get("content", ""),
                            "language": file_info.get("language", "text")
                        })
                else:
                    # Treat entire content as single file
                    all_files.append({
                        "story_uuid": story.story_id,
                        "story_title": story.title or f"Story {story.story_id}",
                        "filepath": f"{story.artifact_path}.json",
                        "content": str(story.content),
                        "language": "json"
                    })
        
        return {
            "epic_uuid": epic.epic_id,
            "epic_name": epic.title or f"Epic {epic.epic_id}",
            "project_uuid": epic.project_id,
            "project_name": project.name or "Unknown Project",
            "files": all_files,
            "total_files": len(all_files)
        }


# Singleton instance
epic_service = EpicService()