"""
FastAPI dependencies for archive enforcement.

Provides dependency injection for verifying projects are not archived
before allowing mutation operations.
"""

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
import logging

from app.core.database import get_db

logger = logging.getLogger(__name__)


def _get_project_id_condition(project_id: str):
    """Get the appropriate WHERE condition for project lookup.
    
    Handles both UUID (id column) and string (project_id column).
    """
    # Lazy import to avoid circular dependency
    from app.api.models.project import Project
    
    try:
        project_uuid = UUID(project_id)
        return Project.id == project_uuid
    except (ValueError, TypeError):
        return Project.project_id == project_id


async def verify_project_not_archived(
    project_id: str,
    db: AsyncSession = Depends(get_db)
) -> None:
    """
    Dependency that raises 403 if project is archived.
    
    Use this on any route that mutates a project or its artifacts.
    
    Server-side enforcement is critical - UI-only checks can be bypassed.
    
    Args:
        project_id: project_id string (e.g., 'LIR-001') or UUID string
        db: Database session
        
    Raises:
        HTTPException(404): Project not found
        HTTPException(403): Project is archived
    """
    # Lazy import to avoid circular dependency
    from app.api.models.project import Project
    
    result = await db.execute(
        select(Project.archived_at).where(_get_project_id_condition(project_id))
    )
    row = result.first()
    
    if not row:
        logger.warning(f"Archive check failed: project {project_id} not found")
        raise HTTPException(
            status_code=404, 
            detail="Project not found"
        )
    
    archived_at = row[0]
    if archived_at is not None:
        logger.warning(
            f"Archive check failed: project {project_id} is archived "
            f"(archived_at={archived_at})"
        )
        raise HTTPException(
            status_code=403,
            detail="Cannot modify archived project. Unarchive the project first to make changes."
        )
    
    logger.debug(f"Archive check passed: project {project_id} is active")