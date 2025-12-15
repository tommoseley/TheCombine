"""
Artifact service for The Combine.

Handles artifact validation, storage, and retrieval using the new
RSP-1 canonical path architecture with PostgreSQL JSONB storage.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
import uuid

from pydantic import ValidationError, BaseModel

from app.api.repositories import ArtifactRepository
from app.combine.models import Artifact, Project

logger = logging.getLogger(__name__)


class ArtifactValidationError(Exception):
    """Artifact validation failed."""
    
    def __init__(self, message: str, details: Dict[str, Any]):
        self.message = message
        self.details = details
        super().__init__(message)


class ArtifactService:
    """
    Service for artifact validation and storage.
    
    Uses the new data-driven architecture:
    - RSP-1 canonical paths (HMP/E001/F003/S007)
    - PostgreSQL with JSONB storage
    - No hard-coded phases or workflows
    """
    
    def __init__(self, db_session):
        """
        Initialize artifact service.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        self.artifact_repo = ArtifactRepository(db_session)
    
    def create_artifact(
        self,
        artifact_path: str,
        artifact_type: str,
        title: str,
        content: Dict[str, Any],
        breadcrumbs: Optional[Dict[str, Any]] = None,
        status: str = "draft",
        created_by: Optional[str] = None
    ) -> Artifact:
        """
        Create a new artifact.
        
        Args:
            artifact_path: RSP-1 path (e.g., "HMP/E001/F003/S007")
            artifact_type: Type of artifact (epic, feature, story, code, etc.)
            title: Human-readable title
            content: JSONB content
            breadcrumbs: Optional context chain
            status: Artifact status (draft, active, completed)
            created_by: Optional creator identifier
            
        Returns:
            Created Artifact
            
        Raises:
            ArtifactValidationError: If validation fails
        """
        # Parse the path to extract components
        path_parts = artifact_path.split('/')
        
        if len(path_parts) < 1:
            raise ArtifactValidationError(
                "Invalid artifact path",
                {"artifact_path": artifact_path}
            )
        
        project_id = path_parts[0]
        epic_id = path_parts[1] if len(path_parts) > 1 else None
        feature_id = path_parts[2] if len(path_parts) > 2 else None
        story_id = path_parts[3] if len(path_parts) > 3 else None
        
        # Determine parent path
        parent_path = None
        if len(path_parts) > 1:
            parent_path = '/'.join(path_parts[:-1])
        
        # Create artifact
        try:
            artifact = Artifact(
                id=uuid.uuid4(),
                artifact_path=artifact_path,
                artifact_type=artifact_type,
                project_id=project_id,
                epic_id=epic_id,
                feature_id=feature_id,
                story_id=story_id,
                title=title,
                content=content,
                breadcrumbs=breadcrumbs or {},
                status=status,
                version=1,
                created_by=created_by,
                parent_path=parent_path
            )
            
            self.db.add(artifact)
            self.db.commit()
            self.db.refresh(artifact)
            
            logger.info(f"Created artifact: {artifact_path} ({artifact_type})")
            return artifact
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create artifact {artifact_path}: {e}")
            raise ArtifactValidationError(
                f"Failed to create artifact: {str(e)}",
                {"artifact_path": artifact_path, "error": str(e)}
            )
    
    def get_artifact(self, artifact_path: str) -> Optional[Artifact]:
        """
        Get artifact by path.
        
        Args:
            artifact_path: RSP-1 path (e.g., "HMP/E001/F003/S007")
            
        Returns:
            Artifact if found, None otherwise
        """
        return self.artifact_repo.get_by_path(artifact_path)
    
    def update_artifact(
        self,
        artifact_path: str,
        content: Optional[Dict[str, Any]] = None,
        title: Optional[str] = None,
        status: Optional[str] = None,
        breadcrumbs: Optional[Dict[str, Any]] = None
    ) -> Optional[Artifact]:
        """
        Update an existing artifact.
        
        Args:
            artifact_path: RSP-1 path
            content: New content (optional)
            title: New title (optional)
            status: New status (optional)
            breadcrumbs: New breadcrumbs (optional)
            
        Returns:
            Updated Artifact if found, None otherwise
        """
        artifact = self.get_artifact(artifact_path)
        if not artifact:
            return None
        
        try:
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
            
            logger.info(f"Updated artifact: {artifact_path} (v{artifact.version})")
            return artifact
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update artifact {artifact_path}: {e}")
            raise ArtifactValidationError(
                f"Failed to update artifact: {str(e)}",
                {"artifact_path": artifact_path, "error": str(e)}
            )
    
    def list_artifacts(
        self,
        project_id: Optional[str] = None,
        artifact_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Artifact]:
        """
        List artifacts with optional filters.
        
        Args:
            project_id: Filter by project
            artifact_type: Filter by type
            status: Filter by status
            limit: Maximum number to return
            
        Returns:
            List of Artifacts
        """
        query = self.db.query(Artifact)
        
        if project_id:
            query = query.filter(Artifact.project_id == project_id)
        if artifact_type:
            query = query.filter(Artifact.artifact_type == artifact_type)
        if status:
            query = query.filter(Artifact.status == status)
        
        query = query.order_by(Artifact.created_at.desc())
        query = query.limit(limit)
        
        return query.all()
    
    def get_children(self, artifact_path: str) -> List[Artifact]:
        """
        Get all child artifacts of a given artifact.
        
        Args:
            artifact_path: Parent artifact path
            
        Returns:
            List of child Artifacts
        """
        return self.db.query(Artifact).filter(
            Artifact.parent_path == artifact_path
        ).order_by(Artifact.created_at).all()
    
    def delete_artifact(self, artifact_path: str) -> bool:
        """
        Delete an artifact.
        
        Args:
            artifact_path: RSP-1 path
            
        Returns:
            True if deleted, False if not found
        """
        artifact = self.get_artifact(artifact_path)
        if not artifact:
            return False
        
        try:
            self.db.delete(artifact)
            self.db.commit()
            logger.info(f"Deleted artifact: {artifact_path}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete artifact {artifact_path}: {e}")
            raise ArtifactValidationError(
                f"Failed to delete artifact: {str(e)}",
                {"artifact_path": artifact_path, "error": str(e)}
            )
    
    def validate_path(self, artifact_path: str) -> bool:
        """
        Validate RSP-1 path format.
        
        Args:
            artifact_path: Path to validate
            
        Returns:
            True if valid, False otherwise
        """
        import re
        # Pattern: PROJECT/EPIC/FEATURE/STORY (e.g., HMP/E001/F003/S007)
        pattern = r'^[A-Z]{2,8}(/[A-Z0-9-]+)*$'
        return bool(re.match(pattern, artifact_path))