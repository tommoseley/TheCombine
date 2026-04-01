"""Shared helpers for projects sub-routers."""

import logging
import re
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models.project import Project

logger = logging.getLogger(__name__)

# ADR-055: Pattern to detect display_id format ({PREFIX}-{NNN}) vs doc_type_id (snake_case)
DISPLAY_ID_PATTERN = re.compile(r'^[A-Z]{2,4}-\d{3,}$')


async def resolve_project(project_id: str, db: AsyncSession) -> Project:
    """Resolve a project by UUID or project_id. Raises 404 if not found."""
    try:
        project_uuid = UUID(project_id)
        result = await db.execute(
            select(Project).where(
                Project.id == project_uuid,
                Project.deleted_at.is_(None),
            )
        )
    except ValueError:
        result = await db.execute(
            select(Project).where(
                Project.project_id == project_id,
                Project.deleted_at.is_(None),
            )
        )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )
    return project
