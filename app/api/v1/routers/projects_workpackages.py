"""Project work packages sub-router.

Handles work package listing, generation, and work statement operations.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models.document import Document
from app.core.database import get_db
from app.auth.dependencies import require_auth
from app.auth.models import User
from app.api.v1.routers.projects_common import resolve_project

logger = logging.getLogger(__name__)

router = APIRouter(tags=["project-workpackages"])


# =============================================================================
# Response Models
# =============================================================================

class WorkPackageResponse(BaseModel):
    """Response model for a governed work package."""
    id: str
    wp_id: Optional[str] = None
    title: Optional[str] = None
    name: Optional[str] = None
    state: Optional[str] = None
    ws_count: int = 0
    provenance: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/{project_id}/work-packages")
async def list_work_packages(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> List[WorkPackageResponse]:
    """List governed work packages for a project."""
    project = await resolve_project(project_id, db)

    result = await db.execute(
        select(Document)
        .where(Document.space_type == 'project')
        .where(Document.space_id == project.id)
        .where(Document.doc_type_id == 'work_package')
        .where(Document.is_latest == True)
        .order_by(Document.created_at)
    )
    docs = result.scalars().all()

    # Count work statements per WP
    ws_counts: Dict[str, int] = {}
    if docs:
        ws_result = await db.execute(
            select(Document)
            .where(Document.space_type == 'project')
            .where(Document.space_id == project.id)
            .where(Document.doc_type_id == 'work_statement')
            .where(Document.is_latest == True)
        )
        for ws in ws_result.scalars().all():
            parent = (ws.content or {}).get('parent_wp_id', '')
            if parent:
                ws_counts[parent] = ws_counts.get(parent, 0) + 1

    return [
        WorkPackageResponse(
            id=str(doc.id),
            wp_id=doc.display_id or str(doc.id)[:8],
            title=(doc.content or {}).get('title'),
            name=(doc.content or {}).get('name', doc.display_id),
            state=(doc.content or {}).get('state', 'ready'),
            ws_count=ws_counts.get(str(doc.id), 0),
            provenance=(doc.content or {}).get('provenance'),
            created_at=doc.created_at.isoformat() if doc.created_at else None,
        )
        for doc in docs
    ]


@router.post("/{project_id}/work-packages/generate")
async def generate_work_packages(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> Dict[str, Any]:
    """Trigger LLM generation of governed work packages from IP candidates + TA."""
    project = await resolve_project(project_id, db)

    # Placeholder: In a future WS, this will invoke the work_package_handler
    # to decompose IP candidates into governed WPs with TA bindings.
    logger.info(
        "Work package generation requested for project %s by %s",
        project.id, current_user.email,
    )

    return {
        "status": "accepted",
        "message": "Work package generation is not yet implemented. "
                   "This endpoint will invoke the WP handler in a future release.",
    }


@router.get("/{project_id}/work-packages/{wp_id}/work-statements")
async def list_work_statements(
    project_id: str,
    wp_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> List[Dict[str, Any]]:
    """List work statements for a governed work package."""
    project = await resolve_project(project_id, db)

    result = await db.execute(
        select(Document)
        .where(Document.space_type == 'project')
        .where(Document.space_id == project.id)
        .where(Document.doc_type_id == 'work_statement')
        .where(Document.is_latest == True)
    )
    ws_docs = result.scalars().all()

    # Filter to WSs belonging to this WP
    statements = []
    for doc in ws_docs:
        content = doc.content or {}
        parent = content.get('parent_wp_id', '')
        if parent == wp_id or str(doc.id).startswith(wp_id):
            statements.append({
                "id": str(doc.id),
                "ws_id": doc.display_id or str(doc.id)[:8],
                "title": content.get('title'),
                "state": content.get('state', 'ready'),
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
            })

    return statements


@router.post("/{project_id}/work-packages/{wp_id}/work-statements/generate")
async def generate_work_statements(
    project_id: str,
    wp_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> Dict[str, Any]:
    """Trigger LLM decomposition of a work package into work statements."""
    project = await resolve_project(project_id, db)

    logger.info(
        "Work statement generation requested for WP %s in project %s by %s",
        wp_id, project.id, current_user.email,
    )

    return {
        "status": "accepted",
        "message": "Work statement generation is not yet implemented. "
                   "This endpoint will invoke the WS handler in a future release.",
    }
