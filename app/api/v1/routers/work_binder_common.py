"""Work Binder shared models and helpers.

Pydantic request/response models and DB resolution helpers used across
the work_binder sub-routers.
"""

import logging
from typing import Any, List
from uuid import UUID

from fastapi import HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models.document import Document
from app.api.models.project import Project

logger = logging.getLogger(__name__)


# ===========================================================================
# Request / Response Models
# ===========================================================================


class ImportCandidatesRequest(BaseModel):
    """Request to import WP candidates from an Implementation Plan."""
    ip_document_id: str = Field(..., min_length=1)


class CandidateInfo(BaseModel):
    """Summary info for a single imported WPC."""
    wpc_id: str
    title: str


class ImportCandidatesResponse(BaseModel):
    """Response after importing candidates from an IP."""
    candidates: List[CandidateInfo]
    count: int


class PromoteCandidateRequest(BaseModel):
    """Request to promote a WPC to a governed Work Package."""
    wpc_id: str = Field(..., min_length=1)
    project_id: str = Field(..., min_length=1)
    transformation: str = Field(..., min_length=1)
    transformation_notes: str = ""
    title_override: str | None = None
    rationale_override: str | None = None


class PromoteCandidateResponse(BaseModel):
    """Response after promoting a WPC to a governed WP."""
    wp_id: str
    document_id: str


class CreateWSRequest(BaseModel):
    """Request body for creating a Work Statement."""
    title: str = Field(default="")
    objective: str = Field(default="")
    scope_in: list[str] = Field(default_factory=list)
    scope_out: list[str] = Field(default_factory=list)
    allowed_paths: list[str] = Field(default_factory=list)
    procedure: list[str] = Field(default_factory=list)
    verification_criteria: list[str] = Field(default_factory=list)
    prohibited_actions: list[str] = Field(default_factory=list)
    governance_pins: dict[str, Any] = Field(default_factory=dict)


class UpdateWSRequest(BaseModel):
    """Request body for updating WS content fields only."""
    model_config = ConfigDict(extra="allow")


class UpdateWPRequest(BaseModel):
    """Request body for updating WP fields only."""
    model_config = ConfigDict(extra="allow")


class ReorderWSRequest(BaseModel):
    """Request body for reordering WSs within a WP."""
    ws_index: list[dict[str, str]] = Field(
        ...,
        description="Ordered list of {ws_id, order_key} entries",
    )


class WSResponse(BaseModel):
    """Response for a single Work Statement."""
    ws_id: str
    parent_wp_id: str
    state: str
    order_key: str
    revision: dict[str, Any] = Field(default_factory=lambda: {"edition": 1})

    @field_validator("revision", mode="before")
    @classmethod
    def _normalize_revision(cls, v: Any) -> dict[str, Any]:
        """Normalize legacy scalar revision (int) to {edition: int}."""
        if isinstance(v, int):
            return {"edition": v}
        return v

    title: str = ""
    objective: str = ""
    scope_in: list[str] = Field(default_factory=list)
    scope_out: list[str] = Field(default_factory=list)
    allowed_paths: list[str] = Field(default_factory=list)
    procedure: list[str] = Field(default_factory=list)
    verification_criteria: list[str] = Field(default_factory=list)
    prohibited_actions: list[str] = Field(default_factory=list)
    governance_pins: dict[str, Any] = Field(default_factory=dict)


class WSListResponse(BaseModel):
    """Response for listing Work Statements."""
    work_statements: list[WSResponse]
    total: int


class ProposeWSRequest(BaseModel):
    """Request to propose WS drafts for a promoted WP via LLM."""
    project_id: str = Field(..., min_length=1)
    wp_id: str = Field(..., min_length=1)


class ProposeWSResponse(BaseModel):
    """Response after proposing WS drafts."""
    wp_id: str
    created: bool
    ws_ids: list[str]


class WPCDetail(BaseModel):
    """Detail for a single WPC in the candidate list."""
    wpc_id: str
    title: str
    rationale: str = ""
    scope_summary: list[str] = Field(default_factory=list)
    source_ip_id: str = ""
    source_ip_version: str = ""
    frozen_at: str = ""
    frozen_by: str = ""
    promoted: bool = False


class WPCListResponse(BaseModel):
    """Response for listing WP candidates for a project."""
    candidates: list[WPCDetail]
    count: int
    import_available: bool = False
    source_ip_id: str | None = None


class WPStabilizeResponse(BaseModel):
    """Response from WP-level stabilize."""
    wp_id: str
    stabilized: list[str]
    count: int


# ===========================================================================
# DB Resolution Helpers (shared across sub-routers)
# ===========================================================================


async def _resolve_project(
    db: AsyncSession, project_id: str,
) -> "Project":
    """Resolve project by UUID or project_id string. 404 if not found."""
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


async def _resolve_space_id(
    db: AsyncSession, project_id: str | None,
) -> str | None:
    """Resolve optional project_id to space_id string. Returns None if unset."""
    if project_id is None:
        return None
    project = await _resolve_project(db, project_id)
    return str(project.id)


async def _load_ip_document(
    db: AsyncSession, ip_document_id: str,
) -> Document:
    """Load an IP document by ID. 404 if not found, 400 if not an IP."""
    try:
        doc_uuid = UUID(ip_document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid document ID format: {ip_document_id}",
        )

    result = await db.execute(
        select(Document).where(
            Document.id == doc_uuid,
            Document.is_latest == True,  # noqa: E712
        )
    )
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"IP document not found: {ip_document_id}",
        )

    ip_types = {"implementation_plan", "primary_implementation_plan"}
    if doc.doc_type_id not in ip_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Document {ip_document_id} is type "
                f"'{doc.doc_type_id}', not an implementation plan"
            ),
        )

    return doc


async def _load_wp_document(
    db: AsyncSession, wp_id: str, *, space_id: str | None = None,
) -> Document:
    """Load a WP document by wp_id content field or display_id. 404 if not found.

    When *space_id* is provided the query is scoped to that project,
    preventing cross-project collisions on display-ids like "WP-001".
    """
    # Try content.wp_id first (canonical for promoted WPs)
    filters = [
        Document.doc_type_id == "work_package",
        Document.content["wp_id"].astext == wp_id,
    ]
    if space_id is not None:
        filters.append(Document.space_id == space_id)
    result = await db.execute(select(Document).where(*filters))
    doc = result.scalars().first()
    if doc is not None:
        return doc

    # Fallback: try display_id (WPs created outside promotion flow)
    fallback_filters = [
        Document.doc_type_id == "work_package",
        Document.display_id == wp_id,
    ]
    if space_id is not None:
        fallback_filters.append(Document.space_id == space_id)
    result = await db.execute(select(Document).where(*fallback_filters))
    doc = result.scalars().first()
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Work Package '{wp_id}' not found",
        )
    return doc


async def _load_ws_document(
    db: AsyncSession, ws_id: str, *, space_id: str | None = None,
) -> Document:
    """Load a WS document by ws_id content field. 404 if not found.

    When *space_id* is provided the query is scoped to that project.
    """
    filters = [
        Document.doc_type_id == "work_statement",
        Document.content["ws_id"].astext == ws_id,
    ]
    if space_id is not None:
        filters.append(Document.space_id == space_id)
    result = await db.execute(select(Document).where(*filters))
    doc = result.scalars().first()
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Work Statement '{ws_id}' not found",
        )
    return doc


async def _find_ip_for_project(
    db: AsyncSession, space_id: UUID,
) -> Document | None:
    """Find the latest IP document for a project space."""
    ip_types = {"implementation_plan", "primary_implementation_plan"}
    result = await db.execute(
        select(Document)
        .where(Document.space_type == "project")
        .where(Document.space_id == space_id)
        .where(Document.doc_type_id.in_(ip_types))
        .where(Document.is_latest == True)  # noqa: E712
        .order_by(Document.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _find_ta_for_project(
    db: AsyncSession, space_id: UUID,
) -> Document | None:
    """Find the latest TA document for a project space."""
    result = await db.execute(
        select(Document)
        .where(Document.space_type == "project")
        .where(Document.space_id == space_id)
        .where(Document.doc_type_id == "technical_architecture")
        .where(Document.is_latest == True)  # noqa: E712
        .order_by(Document.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
