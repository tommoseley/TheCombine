"""
Project Repository for The Combine

Handles project-level operations using the class-based repository pattern.
"""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.models import Project
from datetime import datetime
import uuid as uuid_lib
import logging

logger = logging.getLogger(__name__)


class ProjectRepository:
    """
    Repository for project CRUD operations using SQLAlchemy.
    
    Follows the same pattern as ArtifactRepository and RolePromptRepository.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize repository with database session.
        
        Args:
            db: SQLAlchemy async database session
        """
        self.db = db
    
    async def create(
        self,
        project_id: str,
        name: str,
        description: str = "",
        uuid_id: Optional[str] = None
    ) -> Project:
        """
        Create a new project.
        
        Args:
            project_id: Short project identifier (max 8 chars, e.g., "AUTH", "BILLING")
            name: Human-readable project name (e.g., "Authentication System")
            description: Optional project description
            uuid_id: Optional UUID for database primary key (auto-generated if not provided)
            
        Returns:
            Created Project
            
        Raises:
            ValueError: If project_id already exists
        """
        # Check if exists by project_id
        existing = await self.get_by_project_id(project_id)
        if existing:
            raise ValueError(f"Project {project_id} already exists")
        
        # Generate UUID if not provided
        if not uuid_id:
            uuid_id = str(uuid_lib.uuid4())
        
        project = Project(
            id=uuid_id,
            project_id=project_id,
            name=name,
            description=description,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)
        
        logger.info(f"Created project: {project_id} ({uuid_id}) - {name}")
        return project
    
    async def get_by_uuid(self, uuid_id: str) -> Optional[Project]:
        """
        Get a project by UUID (id field).
        
        Args:
            uuid_id: Project UUID
            
        Returns:
            Project if found, None otherwise
        """
        try:
            # Validate UUID format
            uuid_obj = uuid_lib.UUID(uuid_id)
            uuid_str = str(uuid_obj)
        except ValueError:
            return None
        
        query = select(Project).where(Project.id == uuid_str)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_project_id(self, project_id: str) -> Optional[Project]:
        """
        Get a project by project_id (short identifier).
        
        Args:
            project_id: Project identifier (short, max 8 chars)
            
        Returns:
            Project if found, None otherwise
        """
        query = select(Project).where(Project.project_id == project_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        status: Optional[str] = None
    ) -> List[Project]:
        """
        Get all projects with optional filtering.
        
        Args:
            limit: Maximum number of projects to return
            offset: Number of projects to skip
            status: Optional status filter
            
        Returns:
            List of projects
        """
        query = select(Project).order_by(Project.created_at.desc())
        
        if status:
            query = query.where(Project.status == status)
        
        query = query.limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def update(
        self,
        uuid_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None
    ) -> Optional[Project]:
        """
        Update an existing project.
        
        Args:
            uuid_id: Project UUID
            name: New name (optional)
            description: New description (optional)
            status: New status (optional)
            
        Returns:
            Updated Project or None if not found
        """
        project = await self.get_by_uuid(uuid_id)
        if not project:
            return None
        
        if name is not None:
            project.name = name
        if description is not None:
            project.description = description
        if status is not None:
            project.status = status
        
        project.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(project)
        
        logger.info(f"Updated project: {project.project_id}")
        return project
    
    async def delete(self, uuid_id: str) -> bool:
        """
        Delete a project.
        
        Note: This will cascade delete all artifacts in the project if
        the database is configured with CASCADE on the foreign key.
        
        Args:
            uuid_id: Project UUID
            
        Returns:
            True if deleted, False if not found
        """
        project = await self.get_by_uuid(uuid_id)
        if not project:
            return False
        
        await self.db.delete(project)
        await self.db.commit()
        
        logger.info(f"Deleted project: {project.project_id}")
        return True
    
    async def ensure_exists(self, project_id: str) -> Project:
        """
        Ensure a project exists, creating it if necessary.
        
        This is used by mentors to ensure the project exists before
        creating artifacts within it.
        
        Args:
            project_id: Short project identifier (max 8 chars)
            
        Returns:
            Project (existing or newly created)
        """
        project = await self.get_by_project_id(project_id)
        if project:
            logger.debug(f"Project {project_id} already exists")
            return project
        
        # Create with default name
        return await self.create(
            project_id=project_id,
            name=project_id,
            description=f"Project {project_id}"
        )
    
    async def count(self, status: Optional[str] = None) -> int:
        """
        Count total projects.
        
        Args:
            status: Optional status filter
            
        Returns:
            Number of projects
        """
        from sqlalchemy import func
        
        query = select(func.count(Project.id))
        
        if status:
            query = query.where(Project.status == status)
        
        result = await self.db.execute(query)
        return result.scalar() or 0