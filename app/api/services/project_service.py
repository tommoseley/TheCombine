"""
Project service for web UI - Document-centric version.
"""

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any

# Import existing models
from app.api.models import Project, Document
from app.api.repositories import ProjectRepository


class ProjectService:
    """Service for project-related operations using Document model."""
    
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
        Get projects with document counts for tree view.
        Supports pagination and search.
        """
        # Build query - count work_package documents per project
        wp_subquery = (
            select(
                Document.space_id,
                func.count(Document.id).label("work_package_count")
            )
            .where(Document.space_type == 'project')
            .where(Document.doc_type_id == 'work_package')
            .where(Document.is_latest == True)
            .group_by(Document.space_id)
            .subquery()
        )

        query = (
            select(
                Project.id,
                Project.project_id,
                Project.name,
                Project.description,
                Project.status,
                Project.created_at,
                func.coalesce(wp_subquery.c.work_package_count, 0).label("work_package_count")
            )
            .outerjoin(wp_subquery, Project.id == wp_subquery.c.space_id)
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
                "work_package_count": row.work_package_count or 0
            }
            for row in rows
        ]
    
    async def get_project_summary(
        self,
        db: AsyncSession,
        project_id: str
    ) -> Dict[str, Any]:
        """Get basic project info for collapsed tree node."""
        project = await self._get_project_or_raise(db, project_id)
        
        # Count work_package documents
        wp_count_query = (
            select(func.count(Document.id))
            .where(Document.space_type == 'project')
            .where(Document.space_id == project.id)
            .where(Document.doc_type_id == 'work_package')
            .where(Document.is_latest == True)
        )
        wp_count_result = await db.execute(wp_count_query)
        wp_count = wp_count_result.scalar()

        return {
            "id": str(project.id),
            "project_id": project.project_id,
            "name": project.name or "Untitled Project",
            "description": project.description or "",
            "status": project.status or "active",
            "work_package_count": wp_count or 0
        }

    async def get_project_with_work_packages(
        self,
        db: AsyncSession,
        project_id: str
    ) -> Dict[str, Any]:
        """Get project with all work packages for expanded tree node."""
        project = await self._get_project_or_raise(db, project_id)

        # Get all work_package documents for this project
        wp_query = (
            select(Document)
            .where(Document.space_type == 'project')
            .where(Document.space_id == project.id)
            .where(Document.doc_type_id == 'work_package')
            .where(Document.is_latest == True)
            .order_by(Document.created_at)
        )
        wp_result = await db.execute(wp_query)
        wp_docs = wp_result.scalars().all()

        work_packages = []
        for wp in wp_docs:
            work_packages.append({
                "work_package_uuid": str(wp.id),
                "name": wp.title,
                "description": wp.summary or "",
                "status": wp.status,
            })

        return {
            "id": str(project.id),
            "project_id": project.project_id,
            "name": project.name or "Untitled Project",
            "description": project.description or "",
            "status": project.status or "active",
            "work_packages": work_packages
        }
    
    async def get_project_full(
        self,
        db: AsyncSession,
        project_id: str
    ) -> Dict[str, Any]:
        """Get complete project details for main content view."""
        project = await self._get_project_or_raise(db, project_id)
        
        # Count work packages
        wp_count_query = (
            select(func.count(Document.id))
            .where(Document.space_type == 'project')
            .where(Document.space_id == project.id)
            .where(Document.doc_type_id == 'work_package')
            .where(Document.is_latest == True)
        )
        wp_count_result = await db.execute(wp_count_query)
        wp_count = wp_count_result.scalar() or 0
        
        # Count total documents
        doc_count_query = (
            select(func.count(Document.id))
            .where(Document.space_type == 'project')
            .where(Document.space_id == project.id)
            .where(Document.is_latest == True)
        )
        doc_count_result = await db.execute(doc_count_query)
        total_documents = doc_count_result.scalar() or 0
        
        # Check for architecture documents
        arch_query = (
            select(Document.id)
            .where(Document.space_type == 'project')
            .where(Document.space_id == project.id)
            .where(Document.doc_type_id.in_(['project_discovery', 'architecture_spec']))
            .where(Document.is_latest == True)
            .limit(1)
        )
        arch_result = await db.execute(arch_query)
        has_architecture = arch_result.scalar_one_or_none() is not None
        
        return {
            "id": str(project.id),
            "project_id": project.project_id,
            "name": project.name or "Untitled Project",
            "description": project.description or "",
            "parameters": project.metadata or {},
            "status": project.status or "active",
            "created_at": project.created_at.isoformat() if project.created_at else "",
            "updated_at": project.updated_at.isoformat() if project.updated_at else "",
            "work_package_count": wp_count,
            "document_count": total_documents,
            "has_architecture": has_architecture
        }
    
    async def get_architecture(
        self,
        db: AsyncSession,
        project_id: str
    ) -> Dict[str, Any]:
        """Get architecture details for a project."""
        project = await self._get_project_or_raise(db, project_id)
        
        # Look for architecture_spec document first, then project_discovery
        arch_query = (
            select(Document)
            .where(Document.space_type == 'project')
            .where(Document.space_id == project.id)
            .where(Document.doc_type_id == 'architecture_spec')
            .where(Document.is_latest == True)
        )
        arch_result = await db.execute(arch_query)
        architecture = arch_result.scalar_one_or_none()
        
        # Fall back to project_discovery if no architecture_spec
        if not architecture:
            discovery_query = (
                select(Document)
                .where(Document.space_type == 'project')
                .where(Document.space_id == project.id)
                .where(Document.doc_type_id == 'project_discovery')
                .where(Document.is_latest == True)
            )
            discovery_result = await db.execute(discovery_query)
            architecture = discovery_result.scalar_one_or_none()
        
        if architecture:
            return {
                "architecture_uuid": str(architecture.id),
                "id": str(project.id),
                "project_id": project.project_id,
                "project_name": project.name or "Untitled Project",
                "summary": architecture.title,
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
        """Get basic project info by UUID."""
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

    async def get_project_by_project_id(
        self,
        db: AsyncSession,
        project_id: str
    ) -> Optional[Project]:
        """Get project by short project_id."""
        repo = ProjectRepository(db)
        return await repo.get_by_project_id(project_id)

    async def create_project(
        self,
        db: AsyncSession,
        name: str,
        description: str = "",
        icon: str = "folder"
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
    
    async def get_project_documents(
        self,
        db: AsyncSession,
        project_id: str
    ) -> List[Dict[str, Any]]:
        """Get all documents for a project."""
        project = await self._get_project_or_raise(db, project_id)
        
        query = (
            select(Document)
            .where(Document.space_type == 'project')
            .where(Document.space_id == project.id)
            .where(Document.is_latest == True)
            .order_by(Document.created_at.desc())
        )
        result = await db.execute(query)
        docs = result.scalars().all()
        
        return [
            {
                "id": str(doc.id),
                "doc_type_id": doc.doc_type_id,
                "title": doc.title,
                "status": doc.status,
                "is_stale": doc.is_stale,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
                "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
            }
            for doc in docs
        ]


# Singleton instance
project_service = ProjectService()