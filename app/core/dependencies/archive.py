"""
FastAPI dependencies for archive enforcement.

Provides dependency injection for verifying projects are not archived
before allowing mutation operations.
"""

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from uuid import UUID
import logging

from app.core.database import get_db

logger = logging.getLogger(__name__)


async def verify_project_not_archived(
    project_id: str,
    db: AsyncSession = Depends(get_db)
) -> None:
    """
    Dependency that raises 403 if project is archived.
    
    Use this on any route that mutates a project or its artifacts.
    
    Server-side enforcement is critical - UI-only checks can be bypassed.
    
    Args:
        project_id: UUID string of the project
        db: Database session
        
    Raises:
        HTTPException(404): Project not found
        HTTPException(403): Project is archived
        
    Usage:
        @router.put("/projects/{project_id}")
        async def update_project(
            project_id: str,
            _: None = Depends(verify_project_not_archived),
            current_user: User = Depends(require_auth),
            db: AsyncSession = Depends(get_db)
        ):
            # This code only runs if project is NOT archived
            ...
    """
    result = await db.execute(
        text("""
            SELECT archived_at 
            FROM projects 
            WHERE id = :id
        """),
        {"id": project_id}
    )
    row = result.fetchone()
    
    if not row:
        logger.warning(f"Archive check failed: project {project_id} not found")
        raise HTTPException(
            status_code=404, 
            detail="Project not found"
        )
    
    if row.archived_at is not None:
        logger.warning(
            f"Archive check failed: project {project_id} is archived "
            f"(archived_at={row.archived_at})"
        )
        raise HTTPException(
            status_code=403,
            detail="Cannot modify archived project. Unarchive the project first to make changes."
        )
    
    logger.debug(f"Archive check passed: project {project_id} is active")