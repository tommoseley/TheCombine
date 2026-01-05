"""
Admin routes for The Combine UI

Provides administrative views for system configuration:
- Document types and their associated roles/tasks
- Role prompts and schemas
"""

from app.auth.dependencies import require_admin
from app.auth.models import User
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from .shared import templates

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])



@router.get("/document-types", response_class=HTMLResponse)
async def admin_document_types(request: Request, db: AsyncSession = Depends(get_db)):
    """List all document types with their role/task configuration."""
    
    # Query document types with their associated role_tasks
    query = text("""
        SELECT 
            dt.doc_type_id,
            dt.name as doc_name,
            dt.description as doc_description,
            dt.icon,
            dt.scope,
            dt.display_order,
            dt.handler_id,
            dt.required_inputs,
            dt.optional_inputs,
            dt.acceptance_required,
            r.name as role_name,
            r.identity_prompt as role_identity,
            rt.task_name,
            rt.task_prompt,
            rt.expected_schema,
            rt.version as task_version,
            rt.is_active as task_active
        FROM document_types dt
        LEFT JOIN role_tasks rt ON rt.task_name = dt.doc_type_id AND rt.is_active = true
        LEFT JOIN roles r ON r.id = rt.role_id
        WHERE dt.is_active = true
        ORDER BY dt.scope, dt.display_order
    """)
    
    result = await db.execute(query)
    rows = result.fetchall()
    
    # Convert to list of dicts
    doc_types = []
    for row in rows:
        doc_types.append({
            "doc_type_id": row.doc_type_id,
            "doc_name": row.doc_name,
            "doc_description": row.doc_description,
            "icon": row.icon,
            "scope": row.scope,
            "display_order": row.display_order,
            "handler_id": row.handler_id,
            "required_inputs": row.required_inputs or [],
            "optional_inputs": row.optional_inputs or [],
            "acceptance_required": row.acceptance_required,
            "role_name": row.role_name,
            "role_identity": row.role_identity,
            "task_name": row.task_name,
            "task_prompt": row.task_prompt,
            "expected_schema": row.expected_schema,
            "task_version": row.task_version,
            "task_active": row.task_active,
        })
    
    return templates.TemplateResponse(request, "pages/admin/document_types.html", {
            "doc_types": doc_types,
        }
    )


@router.get("/document-types/{doc_type_id}", response_class=HTMLResponse)
async def admin_document_type_detail(
    request: Request, 
    doc_type_id: str, 
    db: AsyncSession = Depends(get_db)
):
    """Detailed view of a single document type configuration."""
    
    query = text("""
        SELECT 
            dt.doc_type_id,
            dt.name as doc_name,
            dt.description as doc_description,
            dt.icon,
            dt.scope,
            dt.display_order,
            dt.handler_id,
            dt.required_inputs,
            dt.optional_inputs,
            dt.acceptance_required,
            dt.accepted_by_role,
            r.name as role_name,
            r.identity_prompt as role_identity,
            r.description as role_description,
            rt.id as task_id,
            rt.task_name,
            rt.task_prompt,
            rt.expected_schema,
            rt.progress_steps,
            rt.version as task_version,
            rt.is_active as task_active,
            rt.created_at as task_created,
            rt.updated_at as task_updated,
            rt.notes as task_notes
        FROM document_types dt
        LEFT JOIN role_tasks rt ON rt.task_name = dt.doc_type_id AND rt.is_active = true
        LEFT JOIN roles r ON r.id = rt.role_id
        WHERE dt.doc_type_id = :doc_type_id
    """)
    
    result = await db.execute(query, {"doc_type_id": doc_type_id})
    row = result.fetchone()
    
    if not row:
        return templates.TemplateResponse(request, "pages/admin/not_found.html", {"item": "Document Type", "id": doc_type_id}, status_code=404)
    
    doc_type = {
        "doc_type_id": row.doc_type_id,
        "doc_name": row.doc_name,
        "doc_description": row.doc_description,
        "icon": row.icon,
        "scope": row.scope,
        "display_order": row.display_order,
        "handler_id": row.handler_id,
        "required_inputs": row.required_inputs or [],
        "optional_inputs": row.optional_inputs or [],
        "acceptance_required": row.acceptance_required,
        "accepted_by_role": row.accepted_by_role,
        "role_name": row.role_name,
        "role_identity": row.role_identity,
        "role_description": row.role_description,
        "task_id": row.task_id,
        "task_name": row.task_name,
        "task_prompt": row.task_prompt,
        "expected_schema": row.expected_schema,
        "progress_steps": row.progress_steps,
        "task_version": row.task_version,
        "task_active": row.task_active,
        "task_created": row.task_created,
        "task_updated": row.task_updated,
        "task_notes": row.task_notes,
    }
    
    return templates.TemplateResponse(request, "pages/admin/document_type_detail.html", {
            "doc_type": doc_type,
        }
    )
