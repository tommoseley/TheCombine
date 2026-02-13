"""
Admin routes for The Combine UI via ORM

Provides administrative views for system configuration:
- Document types and their associated roles/tasks
- Role prompts and schemas
"""

from app.auth.dependencies import require_admin
from app.auth.models import User
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from ..shared import templates

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/document-types", response_class=HTMLResponse)
async def admin_document_types(request: Request, db: AsyncSession = Depends(get_db)):
    """List all document types with their role/task configuration via ORM."""
    from app.api.models.document_type import DocumentType
    from app.api.models.role_task import RoleTask
    from app.api.models.role import Role
    
    # Query document types with outer join to role_tasks and roles
    result = await db.execute(
        select(
            DocumentType,
            RoleTask,
            Role
        )
        .outerjoin(RoleTask, and_(
            RoleTask.task_name == DocumentType.doc_type_id,
            RoleTask.is_active == True
        ))
        .outerjoin(Role, Role.id == RoleTask.role_id)
        .where(DocumentType.is_active == True)
        .order_by(DocumentType.scope, DocumentType.display_order)
    )
    rows = result.all()
    
    doc_types = []
    for dt, rt, r in rows:
        doc_types.append({
            "doc_type_id": dt.doc_type_id,
            "doc_name": dt.name,
            "doc_description": dt.description,
            "icon": dt.icon,
            "scope": dt.scope,
            "display_order": dt.display_order,
            "handler_id": dt.handler_id,
            "required_inputs": dt.required_inputs or [],
            "optional_inputs": dt.optional_inputs or [],
            "acceptance_required": dt.acceptance_required,
            "role_name": r.name if r else None,
            "role_identity": r.identity_prompt if r else None,
            "task_name": rt.task_name if rt else None,
            "task_prompt": rt.task_prompt if rt else None,
            "expected_schema": rt.expected_schema if rt else None,
            "task_version": rt.version if rt else None,
            "task_active": rt.is_active if rt else None,
        })
    
    return templates.TemplateResponse(request, "admin/pages/document_types.html", {
            "doc_types": doc_types,
        }
    )


@router.get("/document-types/{doc_type_id}", response_class=HTMLResponse)
async def admin_document_type_detail(
    request: Request, 
    doc_type_id: str, 
    db: AsyncSession = Depends(get_db)
):
    """Detailed view of a single document type configuration via ORM."""
    from app.api.models.document_type import DocumentType
    from app.api.models.role_task import RoleTask
    from app.api.models.role import Role
    
    result = await db.execute(
        select(
            DocumentType,
            RoleTask,
            Role
        )
        .outerjoin(RoleTask, and_(
            RoleTask.task_name == DocumentType.doc_type_id,
            RoleTask.is_active == True
        ))
        .outerjoin(Role, Role.id == RoleTask.role_id)
        .where(DocumentType.doc_type_id == doc_type_id)
    )
    row = result.first()
    
    if not row:
        return templates.TemplateResponse(request, "admin/pages/not_found.html", {"item": "Document Type", "id": doc_type_id}, status_code=404)
    
    dt, rt, r = row
    
    doc_type = {
        "doc_type_id": dt.doc_type_id,
        "doc_name": dt.name,
        "doc_description": dt.description,
        "icon": dt.icon,
        "scope": dt.scope,
        "display_order": dt.display_order,
        "handler_id": dt.handler_id,
        "required_inputs": dt.required_inputs or [],
        "optional_inputs": dt.optional_inputs or [],
        "acceptance_required": dt.acceptance_required,
        "accepted_by_role": dt.accepted_by_role,
        "role_name": r.name if r else None,
        "role_identity": r.identity_prompt if r else None,
        "role_description": r.description if r else None,
        "task_id": rt.id if rt else None,
        "task_name": rt.task_name if rt else None,
        "task_prompt": rt.task_prompt if rt else None,
        "expected_schema": rt.expected_schema if rt else None,
        "progress_steps": rt.progress_steps if rt else None,
        "task_version": rt.version if rt else None,
        "task_active": rt.is_active if rt else None,
        "task_created": rt.created_at if rt else None,
        "task_updated": rt.updated_at if rt else None,
        "task_notes": rt.notes if rt else None,
    }
    
    return templates.TemplateResponse(request, "admin/pages/document_type_detail.html", {
            "doc_type": doc_type,
        }
    )