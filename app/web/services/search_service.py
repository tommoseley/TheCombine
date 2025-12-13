"""
Search service for web UI
Handles full-text search across projects and artifacts
"""

from sqlalchemy import select, or_, distinct
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Set
from dataclasses import dataclass

# Import existing models
from app.combine.models import Project, Artifact


@dataclass
class SearchResults:
    """Container for search results across all entity types"""
    projects: List[Dict[str, Any]]
    epics: List[Dict[str, Any]]
    stories: List[Dict[str, Any]]
    
    def get_tree_paths(self) -> List[str]:
        """
        Generate tree paths for highlighting matched nodes
        Returns list of data-node-id values to highlight
        """
        paths: Set[str] = set()
        
        # Add project paths
        for project in self.projects:
            paths.add(f"project-{project['project_uuid']}")
        
        # Add epic paths (include parent project)
        for epic in self.epics:
            paths.add(f"project-{epic['project_uuid']}")
            paths.add(f"epic-{epic['epic_uuid']}")
        
        # Add story paths (include parent epic and project)
        for story in self.stories:
            paths.add(f"project-{story['project_uuid']}")
            if story.get('epic_uuid'):
                paths.add(f"epic-{story['epic_uuid']}")
            paths.add(f"story-{story['story_uuid']}")
        
        return list(paths)


class SearchService:
    """Service for search operations"""
    
    async def search_all(
        self,
        db: AsyncSession,
        query: str,
        limit: int = 10
    ) -> SearchResults:
        """
        Search across all entities (projects, epics, stories)
        Returns structured results with parent relationships
        """
        search_term = f"%{query}%"
        
        # Search projects
        projects = await self._search_projects(db, search_term, limit)
        
        # Search epics (artifacts with artifact_type='epic')
        epics = await self._search_epics(db, search_term, limit)
        
        # Search stories (artifacts with artifact_type='story')
        stories = await self._search_stories(db, search_term, limit)
        
        return SearchResults(
            projects=projects,
            epics=epics,
            stories=stories
        )
    
    async def _search_projects(
        self,
        db: AsyncSession,
        search_term: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Search projects by name or description"""
        query = (
            select(Project)
            .where(
                or_(
                    Project.name.ilike(search_term),
                    Project.description.ilike(search_term),
                    Project.project_id.ilike(search_term)
                )
            )
            .order_by(Project.updated_at.desc())
            .limit(limit)
        )
        
        result = await db.execute(query)
        projects = result.scalars().all()
        
        return [
            {
                "project_uuid": project.project_id,
                "name": project.name or "Untitled Project",
                "description": project.description or "",
                "status": project.status or "active"
            }
            for project in projects
        ]
    
    async def _search_epics(
        self,
        db: AsyncSession,
        search_term: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Search epics (artifacts with type='epic')"""
        query = (
            select(Artifact)
            .where(Artifact.artifact_type == 'epic')
            .where(
                or_(
                    Artifact.title.ilike(search_term),
                    Artifact.epic_id.ilike(search_term),
                    Artifact.artifact_path.ilike(search_term)
                )
            )
            .order_by(Artifact.updated_at.desc())
            .limit(limit)
        )
        
        result = await db.execute(query)
        epics = result.scalars().all()
        
        # Get project names
        epic_results = []
        for epic in epics:
            proj_query = select(Project).where(Project.project_id == epic.project_id)
            proj_result = await db.execute(proj_query)
            project = proj_result.scalar_one_or_none()
            
            epic_results.append({
                "epic_uuid": epic.epic_id,
                "name": epic.title or f"Epic {epic.epic_id}",
                "description": "",
                "status": epic.status or "pending",
                "project_uuid": epic.project_id,
                "project_name": project.name if project else "Unknown Project"
            })
        
        return epic_results
    
    async def _search_stories(
        self,
        db: AsyncSession,
        search_term: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Search stories (artifacts with type='story')"""
        query = (
            select(Artifact)
            .where(Artifact.artifact_type == 'story')
            .where(
                or_(
                    Artifact.title.ilike(search_term),
                    Artifact.story_id.ilike(search_term),
                    Artifact.artifact_path.ilike(search_term)
                )
            )
            .order_by(Artifact.updated_at.desc())
            .limit(limit)
        )
        
        result = await db.execute(query)
        stories = result.scalars().all()
        
        # Get project names
        story_results = []
        for story in stories:
            proj_query = select(Project).where(Project.project_id == story.project_id)
            proj_result = await db.execute(proj_query)
            project = proj_result.scalar_one_or_none()
            
            story_results.append({
                "story_uuid": story.story_id,
                "title": story.title or f"Story {story.story_id}",
                "description": "",
                "status": story.status or "pending",
                "epic_uuid": story.epic_id,
                "epic_name": f"Epic {story.epic_id}" if story.epic_id else "Unknown Epic",
                "project_uuid": story.project_id,
                "project_name": project.name if project else "Unknown Project"
            })
        
        return story_results


# Singleton instance
search_service = SearchService()