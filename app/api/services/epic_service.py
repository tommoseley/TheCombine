"""
Epic service for web UI - Document-centric version.

Epics are documents with doc_type_id = 'epic'.
Stories are related via document_relations (derived_from).
"""

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import Dict, Any, List
from uuid import UUID

from app.api.models import Document, DocumentRelation, Project


class EpicService:
    """Service for epic-related operations using Document model."""
    
    async def get_epic_summary(
        self,
        db: AsyncSession,
        epic_id: UUID
    ) -> Dict[str, Any]:
        """Get basic epic info for collapsed tree node."""
        # Get epic document
        epic = await db.get(Document, epic_id)
        if not epic or epic.doc_type_id != 'epic':
            raise ValueError(f"Epic not found: {epic_id}")
        
        # Count stories derived from this epic
        story_count_query = (
            select(func.count(Document.id))
            .join(DocumentRelation, DocumentRelation.from_document_id == Document.id)
            .where(DocumentRelation.to_document_id == epic_id)
            .where(DocumentRelation.relation_type == 'derived_from')
            .where(Document.doc_type_id == 'story')
            .where(Document.is_latest == True)
        )
        result = await db.execute(story_count_query)
        story_count = result.scalar() or 0
        
        return {
            "epic_uuid": str(epic.id),
            "name": epic.title,
            "description": epic.summary or "",
            "status": epic.status,
            "story_count": story_count
        }
    
    async def get_epic_with_stories(
        self,
        db: AsyncSession,
        epic_id: UUID
    ) -> Dict[str, Any]:
        """Get epic with story list for expanded tree node."""
        # Get epic document
        epic = await db.get(Document, epic_id)
        if not epic or epic.doc_type_id != 'epic':
            raise ValueError(f"Epic not found: {epic_id}")
        
        # Get all stories derived from this epic
        stories_query = (
            select(Document)
            .join(DocumentRelation, DocumentRelation.from_document_id == Document.id)
            .where(DocumentRelation.to_document_id == epic_id)
            .where(DocumentRelation.relation_type == 'derived_from')
            .where(Document.doc_type_id == 'story')
            .where(Document.is_latest == True)
            .order_by(Document.created_at)
        )
        result = await db.execute(stories_query)
        stories = result.scalars().all()
        
        return {
            "epic_uuid": str(epic.id),
            "name": epic.title,
            "description": epic.summary or "",
            "status": epic.status,
            "story_count": len(stories),
            "stories": [
                {
                    "story_uuid": str(story.id),
                    "title": story.title,
                    "status": story.status,
                    "has_code": bool(story.content and story.content.get("files"))
                }
                for story in stories
            ]
        }
    
    async def get_epic_full(
        self,
        db: AsyncSession,
        epic_id: UUID
    ) -> Dict[str, Any]:
        """Get complete epic details for main content view."""
        # Get epic document
        epic = await db.get(Document, epic_id)
        if not epic or epic.doc_type_id != 'epic':
            raise ValueError(f"Epic not found: {epic_id}")
        
        # Get project
        project = await db.get(Project, epic.space_id)
        project_name = project.name if project else "Unknown Project"
        
        # Get story statistics
        stories_query = (
            select(Document)
            .join(DocumentRelation, DocumentRelation.from_document_id == Document.id)
            .where(DocumentRelation.to_document_id == epic_id)
            .where(DocumentRelation.relation_type == 'derived_from')
            .where(Document.doc_type_id == 'story')
            .where(Document.is_latest == True)
        )
        result = await db.execute(stories_query)
        stories = result.scalars().all()
        
        total_stories = len(stories)
        completed_stories = sum(1 for s in stories if s.status == "complete")
        in_progress_stories = sum(1 for s in stories if s.status == "in_progress")
        
        return {
            "epic_uuid": str(epic.id),
            "project_uuid": str(epic.space_id),
            "project_name": project_name,
            "name": epic.title,
            "description": epic.summary or "",
            "status": epic.status,
            "is_stale": epic.is_stale,
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
        epic_id: UUID
    ) -> Dict[str, Any]:
        """Get all stories for an epic with details."""
        # Get epic
        epic = await db.get(Document, epic_id)
        if not epic or epic.doc_type_id != 'epic':
            raise ValueError(f"Epic not found: {epic_id}")
        
        # Get project
        project = await db.get(Project, epic.space_id)
        project_name = project.name if project else "Unknown Project"
        
        # Get all stories
        stories_query = (
            select(Document)
            .join(DocumentRelation, DocumentRelation.from_document_id == Document.id)
            .where(DocumentRelation.to_document_id == epic_id)
            .where(DocumentRelation.relation_type == 'derived_from')
            .where(Document.doc_type_id == 'story')
            .where(Document.is_latest == True)
            .order_by(Document.created_at)
        )
        result = await db.execute(stories_query)
        stories = result.scalars().all()
        
        return {
            "epic_uuid": str(epic.id),
            "epic_name": epic.title,
            "project_uuid": str(epic.space_id),
            "project_name": project_name,
            "stories": [
                {
                    "story_uuid": str(story.id),
                    "title": story.title,
                    "description": story.summary or "",
                    "status": story.status,
                    "is_stale": story.is_stale,
                    "has_code": bool(story.content and story.content.get("files")),
                    "has_tests": bool(story.content and story.content.get("tests")),
                    "acceptance_criteria_count": len(story.content.get("acceptance_criteria", [])) if story.content else 0,
                    "created_at": story.created_at.isoformat() if story.created_at else ""
                }
                for story in stories
            ],
            "total_count": len(stories)
        }
    
    async def get_epic_code(
        self,
        db: AsyncSession,
        epic_id: UUID
    ) -> Dict[str, Any]:
        """Get all code deliverables across all stories in an epic."""
        # Get epic
        epic = await db.get(Document, epic_id)
        if not epic or epic.doc_type_id != 'epic':
            raise ValueError(f"Epic not found: {epic_id}")
        
        # Get project
        project = await db.get(Project, epic.space_id)
        project_name = project.name if project else "Unknown Project"
        
        # Get all stories
        stories_query = (
            select(Document)
            .join(DocumentRelation, DocumentRelation.from_document_id == Document.id)
            .where(DocumentRelation.to_document_id == epic_id)
            .where(DocumentRelation.relation_type == 'derived_from')
            .where(Document.doc_type_id == 'story')
            .where(Document.is_latest == True)
        )
        result = await db.execute(stories_query)
        stories = result.scalars().all()
        
        # Collect all code files
        all_files = []
        for story in stories:
            if story.content and isinstance(story.content, dict):
                files = story.content.get("files", [])
                for file_info in files:
                    all_files.append({
                        "story_uuid": str(story.id),
                        "story_title": story.title,
                        "filepath": file_info.get("filepath", "unknown"),
                        "content": file_info.get("content", ""),
                        "language": file_info.get("language", "text")
                    })
        
        return {
            "epic_uuid": str(epic.id),
            "epic_name": epic.title,
            "project_uuid": str(epic.space_id),
            "project_name": project_name,
            "files": all_files,
            "total_files": len(all_files)
        }
    
    async def list_epics_for_project(
        self,
        db: AsyncSession,
        project_id: UUID
    ) -> List[Dict[str, Any]]:
        """List all epics for a project."""
        query = (
            select(Document)
            .where(Document.space_type == 'project')
            .where(Document.space_id == project_id)
            .where(Document.doc_type_id == 'epic')
            .where(Document.is_latest == True)
            .order_by(Document.created_at)
        )
        result = await db.execute(query)
        epics = result.scalars().all()
        
        return [
            {
                "epic_uuid": str(epic.id),
                "name": epic.title,
                "status": epic.status,
                "is_stale": epic.is_stale,
                "created_at": epic.created_at.isoformat() if epic.created_at else ""
            }
            for epic in epics
        ]


# Singleton instance
epic_service = EpicService()