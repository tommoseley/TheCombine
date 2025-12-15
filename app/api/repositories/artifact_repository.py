"""
Artifact Repository using SQLAlchemy ORM

Provides clean interface for artifact CRUD operations.
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from app.api.models import Artifact, Project, ArtifactVersion, RolePrompt

import logging

logger = logging.getLogger(__name__)


class ArtifactRepository:
    """
    Repository for artifact CRUD operations using SQLAlchemy.
    
    Uses RSP-1 canonical paths as primary identifiers.
    """
    
    def __init__(self, db: Session):
        """
        Initialize repository with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def create(
        self,
        artifact_path: str,
        artifact_type: str,
        content: dict,
        title: Optional[str] = None,
        breadcrumbs: Optional[dict] = None,
        created_by: Optional[str] = None,
        parent_path: Optional[str] = None,
        status: str = "draft"
    ) -> Artifact:
        """
        Create new artifact.
        
        Args:
            artifact_path: RSP-1 canonical path (e.g., "HMP/E001/F003/S007")
            artifact_type: Type of artifact (epic, story, architecture, etc.)
            content: Artifact content as dict
            title: Optional title
            breadcrumbs: Optional breadcrumb dict
            created_by: Optional creator identifier
            parent_path: Optional parent artifact path
            status: Initial status (default: draft)
            
        Returns:
            Created Artifact
        """
        # Parse path components
        parts = artifact_path.split('/')
        project_id = parts[0] if len(parts) >= 1 else None
        epic_id = parts[1] if len(parts) >= 2 else None
        feature_id = parts[2] if len(parts) >= 3 else None
        story_id = parts[3] if len(parts) >= 4 else None
        
        artifact = Artifact(
            artifact_path=artifact_path,
            artifact_type=artifact_type,
            project_id=project_id,
            epic_id=epic_id,
            feature_id=feature_id,
            story_id=story_id,
            title=title,
            content=content,
            breadcrumbs=breadcrumbs,
            created_by=created_by,
            parent_path=parent_path,
            status=status
        )
        
        self.db.add(artifact)
        self.db.commit()
        self.db.refresh(artifact)
        
        logger.info(f"Created artifact: {artifact_path}")
        return artifact
    
    def get_by_path(self, artifact_path: str) -> Optional[Artifact]:
        """
        Retrieve artifact by canonical path.
        
        Args:
            artifact_path: RSP-1 path
            
        Returns:
            Artifact if found, None otherwise
        """
        return self.db.query(Artifact).filter(
            Artifact.artifact_path == artifact_path
        ).first()
    
    def get_by_project(self, project_id: str) -> List[Artifact]:
        """
        Get all artifacts for a project.
        
        Args:
            project_id: Project identifier
            
        Returns:
            List of artifacts
        """
        return self.db.query(Artifact).filter(
            Artifact.project_id == project_id
        ).order_by(Artifact.artifact_path).all()
    
    def get_by_type(
        self,
        artifact_type: str,
        project_id: Optional[str] = None
    ) -> List[Artifact]:
        """
        Get all artifacts of a specific type.
        
        Args:
            artifact_type: Type of artifact
            project_id: Optional project filter
            
        Returns:
            List of artifacts
        """
        query = self.db.query(Artifact).filter(
            Artifact.artifact_type == artifact_type
        )
        
        if project_id:
            query = query.filter(Artifact.project_id == project_id)
        
        return query.order_by(Artifact.created_at.desc()).all()
    
    def get_children(self, artifact_path: str) -> List[Artifact]:
        """
        Get immediate children of an artifact.
        
        Args:
            artifact_path: Parent path
            
        Returns:
            List of child artifacts
        """
        return self.db.query(Artifact).filter(
            Artifact.parent_path == artifact_path
        ).order_by(Artifact.artifact_path).all()
    
    def get_siblings(self, artifact_path: str) -> List[Artifact]:
        """
        Get sibling artifacts (same parent).
        
        Args:
            artifact_path: Artifact path
            
        Returns:
            List of sibling artifacts (excluding self)
        """
        # Get parent path
        parts = artifact_path.split('/')
        if len(parts) <= 1:
            return []  # Project level has no siblings
        
        parent_path = '/'.join(parts[:-1])
        
        return self.db.query(Artifact).filter(
            Artifact.parent_path == parent_path,
            Artifact.artifact_path != artifact_path
        ).order_by(Artifact.artifact_path).all()
    
    def update(
        self,
        artifact_path: str,
        content: Optional[dict] = None,
        title: Optional[str] = None,
        status: Optional[str] = None,
        breadcrumbs: Optional[dict] = None
    ) -> Optional[Artifact]:
        """
        Update artifact fields.
        
        Creates version snapshot before updating.
        
        Args:
            artifact_path: Path of artifact to update
            content: New content dict
            title: New title
            status: New status
            breadcrumbs: New breadcrumbs
            
        Returns:
            Updated artifact or None if not found
        """
        artifact = self.get_by_path(artifact_path)
        if not artifact:
            return None
        
        # Create version snapshot
        version = ArtifactVersion(
            artifact_id=artifact.id,
            artifact_path=artifact.artifact_path,
            version=artifact.version,
            title=artifact.title,
            content=artifact.content,
            breadcrumbs=artifact.breadcrumbs,
            status=artifact.status
        )
        self.db.add(version)
        
        # Update artifact
        if content is not None:
            artifact.content = content
        if title is not None:
            artifact.title = title
        if status is not None:
            artifact.status = status
        if breadcrumbs is not None:
            artifact.breadcrumbs = breadcrumbs
        
        artifact.version += 1
        
        self.db.commit()
        self.db.refresh(artifact)
        
        logger.info(f"Updated artifact: {artifact_path} to v{artifact.version}")
        return artifact
    
    def update_status(
        self,
        artifact_path: str,
        status: str
    ) -> Optional[Artifact]:
        """
        Update artifact status.
        
        Args:
            artifact_path: Path of artifact
            status: New status
            
        Returns:
            Updated artifact or None if not found
        """
        return self.update(artifact_path, status=status)
    
    def delete(self, artifact_path: str) -> bool:
        """
        Delete artifact (soft delete by setting status).
        
        Args:
            artifact_path: Path of artifact to delete
            
        Returns:
            True if deleted, False if not found
        """
        artifact = self.get_by_path(artifact_path)
        if not artifact:
            return False
        
        artifact.status = 'deleted'
        self.db.commit()
        
        logger.info(f"Deleted artifact: {artifact_path}")
        return True
    
    def search(
        self,
        query: str,
        artifact_type: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> List[Artifact]:
        """
        Search artifacts by title or content.
        
        Args:
            query: Search query
            artifact_type: Optional filter by type
            project_id: Optional filter by project
            
        Returns:
            List of matching artifacts
        """
        # Simple search using ILIKE (case-insensitive)
        # For production, use PostgreSQL full-text search
        search_pattern = f"%{query}%"
        
        query_builder = self.db.query(Artifact).filter(
            (Artifact.title.ilike(search_pattern)) |
            (Artifact.content.astext.ilike(search_pattern))
        )
        
        if artifact_type:
            query_builder = query_builder.filter(
                Artifact.artifact_type == artifact_type
            )
        
        if project_id:
            query_builder = query_builder.filter(
                Artifact.project_id == project_id
            )
        
        return query_builder.order_by(Artifact.created_at.desc()).all()


# ============================================================================
# PROJECT REPOSITORY
# ============================================================================

class ProjectRepository:
    """Repository for project CRUD operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(
        self,
        project_id: str,
        name: str,
        description: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> Project:
        """Create new project."""
        project = Project(
            project_id=project_id,
            name=name,
            description=description,
            created_by=created_by
        )
        
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        
        logger.info(f"Created project: {project_id}")
        return project
    
    def get_by_id(self, project_id: str) -> Optional[Project]:
        """Get project by ID."""
        return self.db.query(Project).filter(
            Project.project_id == project_id
        ).first()
    
    def get_all(self, status: Optional[str] = None) -> List[Project]:
        """Get all projects, optionally filtered by status."""
        query = self.db.query(Project)
        
        if status:
            query = query.filter(Project.status == status)
        
        return query.order_by(Project.created_at.desc()).all()
    
    def update_status(self, project_id: str, status: str) -> Optional[Project]:
        """Update project status."""
        project = self.get_by_id(project_id)
        if not project:
            return None
        
        project.status = status
        self.db.commit()
        self.db.refresh(project)
        
        return project


# ============================================================================
# ROLE PROMPT REPOSITORY
# ============================================================================

class RolePromptRepository:
    """Repository for role prompt CRUD operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_active_by_role(self, role_name: str) -> Optional['RolePrompt']:
        """
        Get active prompt for a specific role.
        
        Args:
            role_name: Role identifier (pm, architect, ba, developer, qa)
            
        Returns:
            RolePrompt if found, None otherwise
        """
        from models import RolePrompt
        
        return self.db.query(RolePrompt).filter(
            RolePrompt.role_name == role_name,
            RolePrompt.is_active == True
        ).order_by(RolePrompt.version.desc()).first()
    
    def get_by_id(self, prompt_id: str) -> Optional['RolePrompt']:
        """Get prompt by ID."""
        from models import RolePrompt
        
        return self.db.query(RolePrompt).filter(
            RolePrompt.id == prompt_id
        ).first()
    
    def get_all_versions(self, role_name: str) -> List['RolePrompt']:
        """Get all versions for a role."""
        from models import RolePrompt
        
        return self.db.query(RolePrompt).filter(
            RolePrompt.role_name == role_name
        ).order_by(RolePrompt.version.desc()).all()
    
    def get_all_active(self) -> List['RolePrompt']:
        """Get all active prompts."""
        from models import RolePrompt
        
        return self.db.query(RolePrompt).filter(
            RolePrompt.is_active == True
        ).order_by(RolePrompt.role_name).all()
    
    def create(
        self,
        prompt_id: str,
        role_name: str,
        version: str,
        instructions: str,
        expected_schema: dict,
        is_active: bool = True,
        created_by: Optional[str] = None,
        notes: Optional[str] = None
    ) -> 'RolePrompt':
        """
        Create a new role prompt.
        
        Args:
            prompt_id: Unique identifier (e.g., "pm-v1")
            role_name: Role identifier (pm, architect, ba, developer, qa)
            version: Version string (e.g., "1", "2.1")
            instructions: Prompt template
            expected_schema: JSON schema for validation
            is_active: Whether this is the active version
            created_by: Optional creator identifier
            notes: Optional notes
            
        Returns:
            Created RolePrompt
        """
        from models import RolePrompt
        from datetime import datetime
        
        prompt = RolePrompt(
            id=prompt_id,
            role_name=role_name,
            version=version,
            instructions=instructions,
            expected_schema=expected_schema,
            is_active=is_active,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            created_by=created_by,
            notes=notes
        )
        
        self.db.add(prompt)
        self.db.commit()
        self.db.refresh(prompt)
        
        logger.info(f"Created role prompt: {prompt_id} ({role_name} v{version})")
        return prompt
    
    def update(
        self,
        prompt_id: str,
        instructions: Optional[str] = None,
        expected_schema: Optional[dict] = None,
        is_active: Optional[bool] = None,
        notes: Optional[str] = None
    ) -> Optional['RolePrompt']:
        """
        Update an existing prompt.
        
        Args:
            prompt_id: Prompt identifier
            instructions: New instructions (optional)
            expected_schema: New schema (optional)
            is_active: New active status (optional)
            notes: New notes (optional)
            
        Returns:
            Updated prompt or None if not found
        """
        prompt = self.get_by_id(prompt_id)
        if not prompt:
            return None
        
        if instructions is not None:
            prompt.instructions = instructions
        if expected_schema is not None:
            prompt.expected_schema = expected_schema
        if is_active is not None:
            prompt.is_active = is_active
        if notes is not None:
            prompt.notes = notes
        
        self.db.commit()
        self.db.refresh(prompt)
        
        logger.info(f"Updated role prompt: {prompt_id}")
        return prompt
    
    def set_active_version(self, role_name: str, version: str) -> bool:
        """
        Set a specific version as active (deactivates all others for that role).
        
        Args:
            role_name: Role identifier
            version: Version to activate
            
        Returns:
            True if successful, False if version not found
        """
        from models import RolePrompt
        
        # Deactivate all versions for this role
        self.db.query(RolePrompt).filter(
            RolePrompt.role_name == role_name
        ).update({RolePrompt.is_active: False})
        
        # Activate the specified version
        result = self.db.query(RolePrompt).filter(
            RolePrompt.role_name == role_name,
            RolePrompt.version == version
        ).update({RolePrompt.is_active: True})
        
        self.db.commit()
        
        if result > 0:
            logger.info(f"Set active version for {role_name}: v{version}")
            return True
        return False
    
    def delete(self, prompt_id: str) -> bool:
        """
        Delete a role prompt.
        
        Args:
            prompt_id: Prompt identifier
            
        Returns:
            True if deleted, False if not found
        """
        from models import RolePrompt
        
        prompt = self.get_by_id(prompt_id)
        if not prompt:
            return False
        
        self.db.delete(prompt)
        self.db.commit()
        
        logger.info(f"Deleted role prompt: {prompt_id}")
        return True