"""Artifacts API router.

Provides endpoints for project artifact management (mockups, images, PDFs):
- POST   /projects/{project_id}/artifacts              - Upload artifact
- GET    /projects/{project_id}/artifacts              - List artifacts (metadata only)
- GET    /projects/{project_id}/artifacts/{artifact_id} - Download original file
- GET    /projects/{project_id}/artifacts/{artifact_id}/thumbnail - Download thumbnail
- PATCH  /projects/{project_id}/artifacts/{artifact_id} - Update label/stage_hints
- DELETE /projects/{project_id}/artifacts/{artifact_id} - Delete artifact
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models.project import Project
from app.api.services.mockup_storage_service import MockupStorageService
from app.core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["artifacts"])


# =============================================================================
# Request/Response Models
# =============================================================================


class ArtifactMetadataResponse(BaseModel):
    """Artifact metadata (no binary content)."""
    id: str
    project_id: str
    label: str
    artifact_type: str
    mime_type: str
    file_size_bytes: int
    created_at: Optional[str] = None
    uploaded_by: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ArtifactUpdateRequest(BaseModel):
    """Request body for updating an artifact."""
    label: Optional[str] = Field(None, min_length=1, max_length=200)
    stage_hints: Optional[List[str]] = None


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/{project_id}/artifacts", status_code=201)
async def upload_artifact(
    project_id: UUID,
    file: UploadFile = File(...),
    label: str = Form(...),
    artifact_type: str = Form(default="mockup"),
    db: AsyncSession = Depends(get_db),
) -> ArtifactMetadataResponse:
    """Upload a binary artifact (image/PDF) to a project."""
    # Validate project exists
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    if result.scalars().first() is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    content = await file.read()
    mime_type = file.content_type or "application/octet-stream"

    svc = MockupStorageService(db)
    try:
        artifact = await svc.save(
            project_id=project_id,
            file_content=content,
            mime_type=mime_type,
            label=label,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return ArtifactMetadataResponse(**artifact.to_dict())


@router.get("/{project_id}/artifacts")
async def list_artifacts(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> List[ArtifactMetadataResponse]:
    """List all artifacts for a project (metadata only, no binary content)."""
    svc = MockupStorageService(db)
    artifacts = await svc.list_for_project(project_id)
    return [ArtifactMetadataResponse(**a.to_dict()) for a in artifacts]


@router.get("/{project_id}/artifacts/{artifact_id}")
async def download_artifact(
    project_id: UUID,
    artifact_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Download the original artifact file."""
    svc = MockupStorageService(db)
    try:
        content, mime_type = await svc.load(project_id, artifact_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Artifact not found")

    return Response(content=content, media_type=mime_type)


@router.get("/{project_id}/artifacts/{artifact_id}/thumbnail")
async def download_thumbnail(
    project_id: UUID,
    artifact_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Download the artifact thumbnail."""
    svc = MockupStorageService(db)
    try:
        content, mime_type = await svc.load_thumbnail(project_id, artifact_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return Response(content=content, media_type=mime_type)


@router.patch("/{project_id}/artifacts/{artifact_id}")
async def update_artifact(
    project_id: UUID,
    artifact_id: UUID,
    body: ArtifactUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> ArtifactMetadataResponse:
    """Update artifact label and/or stage_hints."""
    svc = MockupStorageService(db)
    try:
        artifact = await svc.update(
            project_id=project_id,
            artifact_id=artifact_id,
            label=body.label,
            stage_hints=body.stage_hints,
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Artifact not found")

    return ArtifactMetadataResponse(**artifact.to_dict())


@router.delete("/{project_id}/artifacts/{artifact_id}", status_code=204)
async def delete_artifact(
    project_id: UUID,
    artifact_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an artifact."""
    svc = MockupStorageService(db)
    try:
        await svc.delete(project_id, artifact_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Artifact not found")
