"""
Artifact Repository for The Combine - FastAPI Compatible

Repository pattern for artifact CRUD with dependency injection support.
"""

from typing import Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict
from psycopg2.extras import RealDictCursor, Json
import logging

logger = logging.getLogger(__name__)


@dataclass
class Artifact:
    """Artifact domain model."""
    id: str
    artifact_path: str
    artifact_type: str
    project_id: str
    epic_id: Optional[str]
    feature_id: Optional[str]
    story_id: Optional[str]
    title: Optional[str]
    content: dict
    breadcrumbs: Optional[dict]
    status: str
    version: int
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    parent_path: Optional[str]
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        # Convert datetime to ISO string
        data['created_at'] = self.created_at.isoformat() if self.created_at else None
        data['updated_at'] = self.updated_at.isoformat() if self.updated_at else None
        return data


class ArtifactRepository:
    """
    Repository for artifact CRUD operations.
    
    Works with database connections provided via dependency injection.
    """
    
    def __init__(self, connection):
        """
        Initialize repository with database connection.
        
        Args:
            connection: psycopg2 connection (from dependency injection)
        """
        self.connection = connection
    
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
        
        sql = """
        INSERT INTO artifacts (
            artifact_path, artifact_type, project_id, epic_id, feature_id, story_id,
            title, content, breadcrumbs, created_by, parent_path, status
        ) VALUES (
            %(artifact_path)s, %(artifact_type)s, %(project_id)s, %(epic_id)s,
            %(feature_id)s, %(story_id)s, %(title)s, %(content)s, %(breadcrumbs)s,
            %(created_by)s, %(parent_path)s, %(status)s
        )
        RETURNING *
        """
        
        with self.connection.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, {
                'artifact_path': artifact_path,
                'artifact_type': artifact_type,
                'project_id': project_id,
                'epic_id': epic_id,
                'feature_id': feature_id,
                'story_id': story_id,
                'title': title,
                'content': Json(content),
                'breadcrumbs': Json(breadcrumbs) if breadcrumbs else None,
                'created_by': created_by,
                'parent_path': parent_path,
                'status': status
            })
            
            row = cur.fetchone()
            self.connection.commit()
            
            logger.info(f"Created artifact: {artifact_path}")
            return self._row_to_artifact(row)
    
    def get_by_path(self, artifact_path: str) -> Optional[Artifact]:
        """Retrieve artifact by canonical path."""
        sql = "SELECT * FROM artifacts WHERE artifact_path = %(path)s"
        
        with self.connection.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, {'path': artifact_path})
            row = cur.fetchone()
            
            if row:
                return self._row_to_artifact(row)
            return None
    
    def get_by_project(self, project_id: str) -> List[Artifact]:
        """Get all artifacts for a project."""
        sql = """
        SELECT * FROM artifacts 
        WHERE project_id = %(project_id)s
        ORDER BY artifact_path
        """
        
        with self.connection.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, {'project_id': project_id})
            rows = cur.fetchall()
            
            return [self._row_to_artifact(row) for row in rows]
    
    def get_by_type(
        self, 
        artifact_type: str,
        project_id: Optional[str] = None
    ) -> List[Artifact]:
        """Get all artifacts of a specific type."""
        if project_id:
            sql = """
            SELECT * FROM artifacts 
            WHERE artifact_type = %(type)s AND project_id = %(project_id)s
            ORDER BY created_at DESC
            """
            params = {'type': artifact_type, 'project_id': project_id}
        else:
            sql = """
            SELECT * FROM artifacts 
            WHERE artifact_type = %(type)s
            ORDER BY created_at DESC
            """
            params = {'type': artifact_type}
        
        with self.connection.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            
            return [self._row_to_artifact(row) for row in rows]
    
    def get_children(self, artifact_path: str) -> List[Artifact]:
        """Get immediate children of an artifact."""
        sql = """
        SELECT * FROM artifacts 
        WHERE parent_path = %(path)s 
        ORDER BY artifact_path
        """
        
        with self.connection.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, {'path': artifact_path})
            rows = cur.fetchall()
            
            return [self._row_to_artifact(row) for row in rows]
    
    def update_status(
        self,
        artifact_path: str,
        status: str
    ) -> Optional[Artifact]:
        """Update artifact status."""
        sql = """
        UPDATE artifacts 
        SET status = %(status)s, version = version + 1
        WHERE artifact_path = %(path)s
        RETURNING *
        """
        
        with self.connection.cursor(cursor_factory=RealDictCursor) as cur:
            # Create version snapshot first
            cur.execute("""
                INSERT INTO artifact_versions (
                    artifact_id, artifact_path, version, title, content,
                    breadcrumbs, status
                )
                SELECT id, artifact_path, version, title, content,
                       breadcrumbs, status
                FROM artifacts
                WHERE artifact_path = %(path)s
            """, {'path': artifact_path})
            
            # Then update
            cur.execute(sql, {'path': artifact_path, 'status': status})
            row = cur.fetchone()
            self.connection.commit()
            
            if row:
                logger.info(f"Updated status for {artifact_path}: {status}")
                return self._row_to_artifact(row)
            
            return None
    
    def _row_to_artifact(self, row: dict) -> Artifact:
        """Convert database row to Artifact domain object."""
        return Artifact(
            id=str(row['id']),
            artifact_path=row['artifact_path'],
            artifact_type=row['artifact_type'],
            project_id=row['project_id'],
            epic_id=row.get('epic_id'),
            feature_id=row.get('feature_id'),
            story_id=row.get('story_id'),
            title=row.get('title'),
            content=row['content'],
            breadcrumbs=row.get('breadcrumbs'),
            status=row['status'],
            version=row['version'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            created_by=row.get('created_by'),
            parent_path=row.get('parent_path')
        )


def get_artifact_repository(connection) -> ArtifactRepository:
    """
    Factory function for dependency injection.
    
    Usage in FastAPI:
        @router.post("/artifacts")
        async def create_artifact(
            data: ArtifactCreate,
            conn = Depends(get_db_connection),
            repo: ArtifactRepository = Depends(get_artifact_repository)
        ):
            artifact = repo.create(...)
            return artifact.to_dict()
    """
    return ArtifactRepository(connection)