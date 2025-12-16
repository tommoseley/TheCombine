"""
Project service for web UI
Uses path-based architecture (RSP-1)
"""

from sqlalchemy import select, func, or_, distinct
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any

# Import existing models
from app.api.models import Project, Artifact
from app.api.repositories import ProjectRepository


class ProjectService:
    """Service for project-related operations"""
    
    async def _get_project_or_raise(
        self,
        db: AsyncSession,
        project_uuid: str
    ) -> Project:
        """
        Get project by UUID or raise ValueError.
        
        Args:
            db: Database session
            project_uuid: Project UUID
            
        Returns:
            Project instance
            
        Raises:
            ValueError: If project not found
        """
        repo = ProjectRepository(db)
        project = await repo.get_by_uuid(project_uuid)
        if not project:
            raise ValueError(f"Project {project_uuid} not found")
        return project
    
    async def list_projects(
        self,
        db: AsyncSession,
        offset: int = 0,
        limit: int = 20,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get projects with epic counts for tree view
        Supports pagination and search
        """
        # Build query - count distinct epic_ids per project
        query = (
            select(
                Project.id,
                Project.project_id,
                Project.name,
                Project.description,
                Project.status,
                Project.created_at,
                func.count(distinct(Artifact.epic_id)).label("epic_count")
            )
            .outerjoin(Artifact, Project.project_id == Artifact.project_id)
            .group_by(Project.id, Project.project_id, Project.name, Project.description, Project.status, Project.created_at)
            .order_by(Project.created_at.desc())
        )
        
        # Add search filter if provided
        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    Project.name.ilike(search_term),
                    Project.description.ilike(search_term)
                )
            )
        
        # Add pagination
        query = query.offset(offset).limit(limit)
        
        # Execute query
        result = await db.execute(query)
        rows = result.all()
        
        return [
            {
                "id": str(row.id),
                "project_id": row.project_id,
                "name": row.name or "Untitled Project",
                "description": row.description or "",
                "status": row.status or "active",
                "created_at": row.created_at.isoformat() if row.created_at else "",
                "epic_count": row.epic_count or 0
            }
            for row in rows
        ]
    
    async def get_project_summary(
        self,
        db: AsyncSession,
        project_id: str
    ) -> Dict[str, Any]:
        """Get basic project info for collapsed tree node"""
        project = await self._get_project_or_raise(db, project_id)
        
        # Count epics using the project's short project_id
        epic_count_query = (
            select(func.count(distinct(Artifact.epic_id)))
            .where(Artifact.project_id == project.project_id)
            .where(Artifact.epic_id.isnot(None))
        )
        epic_count_result = await db.execute(epic_count_query)
        epic_count = epic_count_result.scalar()
        
        return {
            "id": str(project.id),
            "project_id": project.project_id,
            "name": project.name or "Untitled Project",
            "description": project.description or "",
            "status": project.status or "active",
            "epic_count": epic_count or 0
        }
    
    async def get_project_with_epics(
        self,
        db: AsyncSession,
        project_id: str
    ) -> Dict[str, Any]:
        """Get project with all epics for expanded tree node"""
        project = await self._get_project_or_raise(db, project_id)
        
        # Get all unique epics for this project using short project_id
        epics_query = (
            select(
                Artifact.epic_id,
                func.min(Artifact.title).label("title"),
                func.count(distinct(Artifact.story_id)).label("story_count"),
                func.min(Artifact.status).label("status")
            )
            .where(Artifact.project_id == project.project_id)
            .where(Artifact.epic_id.isnot(None))
            .where(Artifact.artifact_type == 'epic')
            .group_by(Artifact.epic_id)
            .order_by(Artifact.epic_id)
        )
        epics_result = await db.execute(epics_query)
        epics = epics_result.all()
        
        return {
            "id": str(project.id),
            "project_id": project.project_id,
            "name": project.name or "Untitled Project",
            "description": project.description or "",
            "status": project.status or "active",
            "epics": [
                {
                    "epic_uuid": epic.epic_id,
                    "name": epic.title or f"Epic {epic.epic_id}",
                    "description": "",
                    "status": epic.status or "pending",
                    "story_count": epic.story_count or 0
                }
                for epic in epics
            ]
        }
    
    async def get_project_full(
        self,
        db: AsyncSession,
        project_id: str
    ) -> Dict[str, Any]:
        """Get complete project details for main content view"""
        project = await self._get_project_or_raise(db, project_id)
        
        # Count epics using short project_id
        epic_count_query = (
            select(func.count(distinct(Artifact.epic_id)))
            .where(Artifact.project_id == project.project_id)
            .where(Artifact.epic_id.isnot(None))
        )
        epic_count_result = await db.execute(epic_count_query)
        epic_count = epic_count_result.scalar()
        
        # Count total artifacts
        artifact_count_query = (
            select(func.count(Artifact.id))
            .where(Artifact.project_id == project.project_id)
        )
        artifact_count_result = await db.execute(artifact_count_query)
        total_artifacts = artifact_count_result.scalar()
        
        return {
            "id": str(project.id),
            "project_id": project.project_id,
            "name": project.name or "Untitled Project",
            "description": project.description or "",
            "parameters": project.metadata or {},
            "status": project.status or "active",
            "created_at": project.created_at.isoformat() if project.created_at else "",
            "updated_at": project.updated_at.isoformat() if project.updated_at else "",
            "epic_count": epic_count or 0,
            "story_count": total_artifacts or 0,
            "has_architecture": False  # TODO: Check if architecture artifact exists
        }
    
    async def get_architecture(
        self,
        db: AsyncSession,
        project_id: str
    ) -> Dict[str, Any]:
        """Get architecture details for a project"""
        project = await self._get_project_or_raise(db, project_id)
        
        # Look for architecture artifact using short project_id
        arch_query = (
            select(Artifact)
            .where(Artifact.project_id == project.project_id)
            .where(Artifact.artifact_type == 'architecture')
            .order_by(Artifact.created_at.desc())
        )
        arch_result = await db.execute(arch_query)
        architecture = arch_result.scalar_one_or_none()
        
        if architecture:
            return {
                "architecture_uuid": str(architecture.id),
                "id": str(project.id),
                "project_id": project.project_id,
                "project_name": project.name or "Untitled Project",
                "summary": architecture.title or "Architecture",
                "detailed_view": architecture.content or {},
                "diagrams": []
            }
        
        return {
            "architecture_uuid": None,
            "id": str(project.id),
            "project_id": project.project_id,
            "project_name": project.name or "Untitled Project",
            "summary": "Architecture documentation coming soon",
            "detailed_view": {},
            "diagrams": []
        }

    async def get_project_by_uuid(
        self,
        db: AsyncSession,
        uuid: str
    ) -> Optional[Dict[str, Any]]:
        """Get basic project info by UUID"""
        repo = ProjectRepository(db)
        project = await repo.get_by_uuid(uuid)
        
        if not project:
            return None
        
        return {
            "id": str(project.id),
            "project_id": project.project_id,
            "name": project.name,
            "description": project.description,
            "status": project.status,
            "created_at": project.created_at.isoformat() if project.created_at else None
        }

    async def create_project(
        self,
        db: AsyncSession,
        name: str,
        description: str = ""
    ) -> Dict[str, Any]:
        """
        Create a new project with auto-generated project_id.
        
        Args:
            db: Database session
            name: Project name
            description: Project description
            
        Returns:
            Created project dict
            
        Raises:
            ValueError: If project creation fails
        """
        import re
        
        repo = ProjectRepository(db)
        
        # Generate a short project ID from the name (max 8 chars)
        base_id = re.sub(r'[^A-Z0-9]', '', name.upper())[:8]
        
        if len(base_id) < 3:
            base_id = base_id + 'PRJ'
        
        project_id = base_id
        counter = 1
        
        # Find unique project_id
        while counter < 100:
            existing = await repo.get_by_project_id(project_id)
            if not existing:
                break
            suffix = str(counter)
            project_id = base_id[:8-len(suffix)] + suffix
            counter += 1
        
        if counter >= 100:
            raise ValueError("Could not generate unique project ID")
        
        # Create project
        project = await repo.create(
            project_id=project_id,
            name=name,
            description=description
        )
        
        return {
            "id": str(project.id),
            "project_id": project.project_id,
            "name": project.name,
            "description": project.description,
            "status": project.status,
            "created_at": project.created_at.isoformat() if project.created_at else None
        }


# Singleton instance
project_service = ProjectService()