"""Work Binder API router — WS-WB-003, WS-WB-004, WS-WB-006, WS-WB-008, WS-WB-009.

Provides endpoints for Work Binder operations:
- GET /candidates — List WPC documents for a project (WS-WB-009)
- POST /import-candidates — Extract WP candidates from IP (WS-WB-003)
- POST /promote — Promote WPC to governed WP (WS-WB-004)
- POST /wp/{wp_id}/work-statements — Create WS (WS-WB-006)
- PATCH /work-statements/{ws_id} — Update WS content only
- PUT /wp/{wp_id}/ws-index — Reorder WSs (WP edition bump)
- PATCH /wp/{wp_id} — Update WP fields only
- GET /wp/{wp_id}/work-statements — List WSs in order
- GET /work-statements/{ws_id} — Get single WS
- GET /wp/{wp_id}/history — WP edition history
- POST /work-statements/{ws_id}/stabilize — DRAFT -> READY

Business logic lives in pure service modules.
This router handles DB access, idempotency, HTTP concerns,
governance invariant enforcement, and audit trail logging (WS-WB-008).
"""

import copy
import logging
from typing import Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models.document import Document
from app.api.models.project import Project
from app.core.database import get_db
from app.domain.services.candidate_import_service import import_candidates
from app.domain.services.wp_promotion_service import (
    build_audit_event,
    build_promoted_wp,
    derive_wp_id,
    validate_promotion_request,
)
from app.domain.services.ws_crud_service import (
    add_ws_to_wp_index,
    build_new_ws,
    generate_order_key,
    generate_ws_id,
    reorder_ws_index,
    validate_stabilization,
    validate_wp_update_fields,
    validate_ws_update_fields,
)
from app.domain.services.wp_edition_service import (
    apply_edition_bump,
)
from app.domain.services.wb_audit_service import (
    build_audit_event as build_wb_audit_event,
    validate_can_create_ws,
    validate_can_promote,
    validate_can_reorder,
    validate_provenance,
)
from app.domain.services.work_statement_state import validate_ws_transition

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/work-binder", tags=["work-binder"])


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
    revision: int
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


class WPCDetail(BaseModel):
    """Detail for a single WPC in the candidate list."""
    wpc_id: str
    title: str
    rationale: str = ""
    scope_summary: list[str] = Field(default_factory=list)
    source_ip_id: str = ""
    frozen_at: str = ""
    promoted: bool = False


class WPCListResponse(BaseModel):
    """Response for listing WP candidates for a project."""
    candidates: list[WPCDetail]
    count: int
    import_available: bool = False
    source_ip_id: str | None = None


# ===========================================================================
# WS-WB-009: List Candidates
# ===========================================================================


@router.get("/candidates", response_model=WPCListResponse)
async def list_candidates(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> WPCListResponse:
    """List WP candidate documents for a project (read-only).

    Returns existing WPC documents. If none exist but an IP document does,
    returns import_available=True with the IP document ID so the SPA can
    trigger an explicit import via POST /import-candidates.
    """
    project = await _resolve_project(db, project_id)

    # Query all WPC documents for this project
    wpc_result = await db.execute(
        select(Document)
        .where(Document.space_type == "project")
        .where(Document.space_id == project.id)
        .where(Document.doc_type_id == "work_package_candidate")
        .where(Document.is_latest == True)  # noqa: E712
        .order_by(Document.created_at)
    )
    wpc_docs = list(wpc_result.scalars().all())

    if wpc_docs:
        # Compute promoted flag via lineage (source_candidate_ids on WPs)
        promoted_ids = await _collect_promoted_wpc_ids(db, project.id)

        candidates = []
        for doc in wpc_docs:
            content = doc.content or {}
            candidates.append(WPCDetail(
                wpc_id=content.get("wpc_id", doc.instance_id or ""),
                title=content.get("title", doc.title or ""),
                rationale=content.get("rationale", ""),
                scope_summary=content.get("scope_summary", []),
                source_ip_id=content.get("source_ip_id", ""),
                frozen_at=content.get("frozen_at", ""),
                promoted=content.get("wpc_id", "") in promoted_ids,
            ))

        return WPCListResponse(
            candidates=candidates,
            count=len(candidates),
            import_available=False,
        )

    # No WPCs — check if an IP document exists for import
    ip_doc = await _find_ip_for_project(db, project.id)
    if ip_doc:
        return WPCListResponse(
            candidates=[],
            count=0,
            import_available=True,
            source_ip_id=str(ip_doc.id),
        )

    return WPCListResponse(candidates=[], count=0)


# ===========================================================================
# WS-WB-003: Import Candidates
# ===========================================================================


@router.post(
    "/import-candidates",
    response_model=ImportCandidatesResponse,
)
async def import_candidates_from_ip(
    request: ImportCandidatesRequest,
    db: AsyncSession = Depends(get_db),
) -> ImportCandidatesResponse:
    """Extract WP candidates from a committed Implementation Plan.

    Idempotent: re-import of the same IP version does not create duplicates.
    """
    # --- Governance: provenance check (WS-WB-008) ---
    prov_errors = validate_provenance("system")
    if prov_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="; ".join(prov_errors),
        )

    ip_doc = await _load_ip_document(db, request.ip_document_id)

    source_ip_version = str(ip_doc.version)
    wpc_documents = import_candidates(
        ip_content=ip_doc.content,
        source_ip_id=request.ip_document_id,
        source_ip_version=source_ip_version,
    )

    if not wpc_documents:
        return ImportCandidatesResponse(candidates=[], count=0)

    result_candidates: List[CandidateInfo] = []

    for wpc_content in wpc_documents:
        wpc_id = wpc_content["wpc_id"]

        existing = await _find_existing_wpc(
            db, wpc_id, request.ip_document_id, source_ip_version,
        )

        if existing:
            logger.info(
                f"WPC {wpc_id} already exists for IP "
                f"{request.ip_document_id} "
                f"v{source_ip_version} — skipping (idempotent)"
            )
            result_candidates.append(CandidateInfo(
                wpc_id=wpc_id,
                title=existing.title,
            ))
            continue

        doc = Document(
            space_type="project",
            space_id=ip_doc.space_id,
            doc_type_id="work_package_candidate",
            version=1,
            title=wpc_content["title"],
            content=wpc_content,
            status="active",
            lifecycle_state="complete",
            instance_id=wpc_id,
            parent_document_id=ip_doc.id,
            created_by="system",
            created_by_type="import",
        )
        doc.update_revision_hash()
        db.add(doc)

        result_candidates.append(CandidateInfo(
            wpc_id=wpc_id,
            title=wpc_content["title"],
        ))

        logger.info(
            f"Created WPC {wpc_id} from IP "
            f"{request.ip_document_id} v{source_ip_version}"
        )

    await db.flush()

    # --- Audit trail (WS-WB-008) ---
    for ci in result_candidates:
        audit_evt = build_wb_audit_event(
            event_type="candidate_import",
            entity_id=ci.wpc_id,
            entity_type="work_package_candidate",
            mutation_data={
                "source_ip_id": request.ip_document_id,
                "title": ci.title,
            },
            actor="system",
        )
        logger.info("AUDIT: %s", audit_evt)

    return ImportCandidatesResponse(
        candidates=result_candidates,
        count=len(result_candidates),
    )


# ===========================================================================
# WS-WB-004: Promote Candidate
# ===========================================================================


@router.post("/promote", response_model=PromoteCandidateResponse)
async def promote_candidate(
    request: PromoteCandidateRequest,
    db: AsyncSession = Depends(get_db),
) -> PromoteCandidateResponse:
    """Promote a WP candidate to a governed Work Package.

    Idempotent: if a WP already exists for this WPC, returns existing.
    """
    # --- Governance: provenance check (WS-WB-008) ---
    prov_errors = validate_provenance("system")
    if prov_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="; ".join(prov_errors),
        )

    # --- Governance: promotion requires transformation metadata (WS-WB-008) ---
    promote_errors = validate_can_promote(
        request.transformation, request.transformation_notes,
    )
    if promote_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="; ".join(promote_errors),
        )

    errors = validate_promotion_request(request.transformation)
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="; ".join(errors),
        )

    wpc_doc = await _load_wpc_document(db, request.wpc_id)

    wp_id = derive_wp_id(request.wpc_id)
    existing_wp = await _find_existing_wp(db, wp_id, wpc_doc.space_id)
    if existing_wp:
        logger.info(
            f"WP {wp_id} already exists for WPC {request.wpc_id} "
            f"-- returning existing (idempotent)"
        )
        return PromoteCandidateResponse(
            wp_id=wp_id,
            document_id=str(existing_wp.id),
        )

    wp_content = build_promoted_wp(
        candidate=wpc_doc.content,
        transformation=request.transformation,
        transformation_notes=request.transformation_notes,
        title_override=request.title_override,
        rationale_override=request.rationale_override,
    )

    wp_doc = Document(
        space_type="project",
        space_id=wpc_doc.space_id,
        doc_type_id="work_package",
        version=1,
        title=wp_content["title"],
        content=wp_content,
        status="active",
        lifecycle_state="complete",
        instance_id=wp_id,
        parent_document_id=wpc_doc.parent_document_id,
        created_by="system",
        created_by_type="promotion",
    )
    wp_doc.update_revision_hash()
    db.add(wp_doc)

    # Legacy audit event (wp_promotion_service) — retained for compatibility
    legacy_audit = build_audit_event(
        wpc_id=request.wpc_id,
        wp_id=wp_id,
        transformation=request.transformation,
        promoted_by="system",
    )
    logger.info(
        f"Promoted WPC {request.wpc_id} -> WP {wp_id} "
        f"(transformation={request.transformation}): "
        f"{legacy_audit}"
    )

    await db.flush()

    # --- Audit trail (WS-WB-008) ---
    audit_evt = build_wb_audit_event(
        event_type="candidate_promotion",
        entity_id=wp_id,
        entity_type="work_package",
        mutation_data={
            "wpc_id": request.wpc_id,
            "transformation": request.transformation,
            "transformation_notes": request.transformation_notes,
        },
        actor="system",
    )
    logger.info("AUDIT: %s", audit_evt)

    return PromoteCandidateResponse(
        wp_id=wp_id,
        document_id=str(wp_doc.id),
    )


# ===========================================================================
# WS-WB-006: Create Work Statement
# ===========================================================================


@router.post(
    "/wp/{wp_id}/work-statements",
    response_model=WSResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_work_statement(
    wp_id: str,
    body: CreateWSRequest,
    db: AsyncSession = Depends(get_db),
) -> WSResponse:
    """Create a new WS under the given WP."""
    # --- Governance: provenance check (WS-WB-008) ---
    prov_errors = validate_provenance("system")
    if prov_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="; ".join(prov_errors),
        )

    wp_doc = await _load_wp_document(db, wp_id)

    # --- Governance: cannot create WS when ta_version_id is pending (WS-WB-008) ---
    ws_create_errors = validate_can_create_ws(wp_doc.content or {})
    if ws_create_errors:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="; ".join(ws_create_errors),
        )

    old_content = copy.deepcopy(wp_doc.content or {})
    wp_content = dict(wp_doc.content or {})

    ws_index = wp_content.get("ws_index", [])
    sequence_num = len(ws_index) + 1

    ws_id = generate_ws_id(wp_id, sequence_num)
    existing_keys = [e.get("order_key", "") for e in ws_index]
    order_key = generate_order_key(existing_keys)

    ws_data = build_new_ws(wp_id, ws_id, order_key, body.model_dump())

    wp_content = add_ws_to_wp_index(wp_content, ws_id, order_key)
    wp_content = apply_edition_bump(wp_content, old_content, "system")

    ws_doc = Document(
        space_type=wp_doc.space_type,
        space_id=wp_doc.space_id,
        doc_type_id="work_statement",
        title=ws_data.get("title", ws_id),
        content=ws_data,
        version=1,
    )
    db.add(ws_doc)

    wp_doc.content = wp_content
    await db.flush()

    # --- Audit trail (WS-WB-008) ---
    audit_evt = build_wb_audit_event(
        event_type="ws_created",
        entity_id=ws_id,
        entity_type="work_statement",
        mutation_data={
            "parent_wp_id": wp_id,
            "title": ws_data.get("title", ""),
            "order_key": order_key,
        },
        actor="system",
    )
    logger.info("AUDIT: %s", audit_evt)

    logger.info("Created WS %s under WP %s", ws_id, wp_id)
    return WSResponse(**ws_data)


# ===========================================================================
# WS-WB-006: Update WS Content Only
# ===========================================================================


@router.patch(
    "/work-statements/{ws_id}",
    response_model=WSResponse,
)
async def update_work_statement(
    ws_id: str,
    body: UpdateWSRequest,
    db: AsyncSession = Depends(get_db),
) -> WSResponse:
    """Update WS content fields. Rejects WP-level fields."""
    # --- Governance: provenance check (WS-WB-008) ---
    prov_errors = validate_provenance("system")
    if prov_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="; ".join(prov_errors),
        )

    update_data = body.model_dump(exclude_unset=True)

    errors = validate_ws_update_fields(update_data)
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "PLANE_VIOLATION", "errors": errors},
        )

    ws_doc = await _load_ws_document(db, ws_id)
    ws_content = dict(ws_doc.content or {})

    for key, value in update_data.items():
        ws_content[key] = value

    ws_content["revision"] = ws_content.get("revision", 0) + 1

    old_revision = ws_content.get("revision", 0) - 1  # before increment
    ws_doc.content = ws_content
    await db.flush()

    # --- Audit trail (WS-WB-008) ---
    audit_evt = build_wb_audit_event(
        event_type="ws_updated",
        entity_id=ws_id,
        entity_type="work_statement",
        mutation_data={
            "fields_updated": list(update_data.keys()),
            "revision_before": old_revision,
            "revision_after": ws_content["revision"],
        },
        actor="system",
    )
    logger.info("AUDIT: %s", audit_evt)

    logger.info(
        "Updated WS %s (revision %d)", ws_id, ws_content["revision"]
    )
    return WSResponse(**ws_content)


# ===========================================================================
# WS-WB-006: Reorder WSs
# ===========================================================================


@router.put("/wp/{wp_id}/ws-index")
async def reorder_work_statements(
    wp_id: str,
    body: ReorderWSRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Reorder WSs in a WP. Bumps WP edition."""
    # --- Governance: provenance check (WS-WB-008) ---
    prov_errors = validate_provenance("system")
    if prov_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="; ".join(prov_errors),
        )

    wp_doc = await _load_wp_document(db, wp_id)

    # --- Governance: cannot reorder on DONE WP (WS-WB-008) ---
    reorder_errors = validate_can_reorder(wp_doc.content or {})
    if reorder_errors:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="; ".join(reorder_errors),
        )

    old_content = copy.deepcopy(wp_doc.content or {})
    wp_content = dict(wp_doc.content or {})

    wp_content = reorder_ws_index(wp_content, body.ws_index)
    wp_content = apply_edition_bump(wp_content, old_content, "system")

    wp_doc.content = wp_content
    await db.flush()

    revision = wp_content.get("revision", {})
    edition = revision.get("edition", 0) if isinstance(revision, dict) else 0

    # --- Audit trail (WS-WB-008) ---
    audit_evt = build_wb_audit_event(
        event_type="ws_reordered",
        entity_id=wp_id,
        entity_type="work_package",
        mutation_data={
            "new_ws_index": [
                {"ws_id": e["ws_id"], "order_key": e["order_key"]}
                for e in body.ws_index
            ],
            "edition": edition,
        },
        actor="system",
    )
    logger.info("AUDIT: %s", audit_evt)

    logger.info("Reordered WSs in WP %s", wp_id)
    return {"status": "ok", "wp_id": wp_id, "edition": edition}


# ===========================================================================
# WS-WB-006: Update WP Fields Only
# ===========================================================================


@router.patch("/wp/{wp_id}")
async def update_work_package(
    wp_id: str,
    body: UpdateWPRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Update WP fields. Rejects WS content fields."""
    # --- Governance: provenance check (WS-WB-008) ---
    prov_errors = validate_provenance("system")
    if prov_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="; ".join(prov_errors),
        )

    update_data = body.model_dump(exclude_unset=True)

    errors = validate_wp_update_fields(update_data)
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "PLANE_VIOLATION", "errors": errors},
        )

    wp_doc = await _load_wp_document(db, wp_id)
    old_content = copy.deepcopy(wp_doc.content or {})
    wp_content = dict(wp_doc.content or {})

    for key, value in update_data.items():
        wp_content[key] = value

    wp_content = apply_edition_bump(wp_content, old_content, "system")

    wp_doc.content = wp_content
    await db.flush()

    revision = wp_content.get("revision", {})
    edition = revision.get("edition", 0) if isinstance(revision, dict) else 0

    # --- Audit trail (WS-WB-008) ---
    audit_evt = build_wb_audit_event(
        event_type="wp_updated",
        entity_id=wp_id,
        entity_type="work_package",
        mutation_data={
            "fields_updated": list(update_data.keys()),
            "edition": edition,
        },
        actor="system",
    )
    logger.info("AUDIT: %s", audit_evt)

    logger.info("Updated WP %s", wp_id)
    return {"status": "ok", "wp_id": wp_id, "edition": edition}


# ===========================================================================
# WS-WB-006: List WSs in Order
# ===========================================================================


@router.get(
    "/wp/{wp_id}/work-statements",
    response_model=WSListResponse,
)
async def list_work_statements(
    wp_id: str,
    db: AsyncSession = Depends(get_db),
) -> WSListResponse:
    """List WSs under a WP in ws_index order."""
    wp_doc = await _load_wp_document(db, wp_id)
    wp_content = wp_doc.content or {}
    ws_index = wp_content.get("ws_index", [])

    ordered_ws_ids = [e.get("ws_id") for e in ws_index]

    result = await db.execute(
        select(Document).where(
            Document.doc_type_id == "work_statement",
            Document.content["parent_wp_id"].astext == wp_id,
        )
    )
    ws_docs = {
        doc.content.get("ws_id"): doc.content
        for doc in result.scalars().all()
        if doc.content
    }

    ordered = []
    for ws_id_val in ordered_ws_ids:
        if ws_id_val in ws_docs:
            ordered.append(WSResponse(**ws_docs[ws_id_val]))

    indexed_ids = set(ordered_ws_ids)
    for ws_id_val, content in ws_docs.items():
        if ws_id_val not in indexed_ids:
            ordered.append(WSResponse(**content))

    return WSListResponse(work_statements=ordered, total=len(ordered))


# ===========================================================================
# WS-WB-006: Get Single WS
# ===========================================================================


@router.get(
    "/work-statements/{ws_id}",
    response_model=WSResponse,
)
async def get_work_statement(
    ws_id: str,
    db: AsyncSession = Depends(get_db),
) -> WSResponse:
    """Get a single WS by ID."""
    ws_doc = await _load_ws_document(db, ws_id)
    return WSResponse(**(ws_doc.content or {}))


# ===========================================================================
# WS-WB-006: WP Edition History
# ===========================================================================


@router.get("/wp/{wp_id}/history")
async def get_wp_history(
    wp_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get WP edition history."""
    wp_doc = await _load_wp_document(db, wp_id)
    wp_content = wp_doc.content or {}

    revision = wp_content.get("revision", {})
    edition = revision.get("edition", 0) if isinstance(revision, dict) else 0
    change_summary = wp_content.get("change_summary", [])

    return {
        "wp_id": wp_id,
        "edition": edition,
        "change_summary": change_summary,
    }


# ===========================================================================
# WS-WB-006: Stabilize WS (DRAFT -> READY)
# ===========================================================================


@router.post(
    "/work-statements/{ws_id}/stabilize",
    response_model=WSResponse,
)
async def stabilize_work_statement(
    ws_id: str,
    db: AsyncSession = Depends(get_db),
) -> WSResponse:
    """Stabilize a WS: DRAFT -> READY with field validation."""
    # --- Governance: provenance check (WS-WB-008) ---
    prov_errors = validate_provenance("system")
    if prov_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="; ".join(prov_errors),
        )

    ws_doc = await _load_ws_document(db, ws_id)
    ws_content = dict(ws_doc.content or {})

    current_state = ws_content.get("state", "DRAFT")
    try:
        validate_ws_transition(current_state, "READY")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_TRANSITION",
                "message": str(e),
            },
        )

    errors = validate_stabilization(ws_content)
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "STABILIZATION_FAILED",
                "errors": errors,
            },
        )

    ws_content["state"] = "READY"
    ws_content["revision"] = ws_content.get("revision", 0) + 1

    ws_doc.content = ws_content
    await db.flush()

    # --- Audit trail (WS-WB-008) ---
    audit_evt = build_wb_audit_event(
        event_type="ws_stabilized",
        entity_id=ws_id,
        entity_type="work_statement",
        mutation_data={
            "state_before": "DRAFT",
            "state_after": "READY",
        },
        actor="system",
    )
    logger.info("AUDIT: %s", audit_evt)

    logger.info("Stabilized WS %s: DRAFT -> READY", ws_id)
    return WSResponse(**ws_content)


# ===========================================================================
# Internal Helpers
# ===========================================================================


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


async def _find_existing_wpc(
    db: AsyncSession,
    wpc_id: str,
    source_ip_id: str,
    source_ip_version: str,
) -> Document | None:
    """Find existing WPC by wpc_id + source IP provenance."""
    result = await db.execute(
        select(Document).where(
            Document.doc_type_id == "work_package_candidate",
            Document.instance_id == wpc_id,
            Document.is_latest == True,  # noqa: E712
            Document.content["source_ip_id"].astext == source_ip_id,
            Document.content[
                "source_ip_version"
            ].astext == source_ip_version,
        )
    )
    return result.scalar_one_or_none()


async def _load_wpc_document(
    db: AsyncSession, wpc_id: str,
) -> Document:
    """Load a WPC document by instance_id. 404 if not found."""
    result = await db.execute(
        select(Document).where(
            Document.doc_type_id == "work_package_candidate",
            Document.instance_id == wpc_id,
            Document.is_latest == True,  # noqa: E712
        )
    )
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"WPC document not found: {wpc_id}",
        )

    return doc


async def _find_existing_wp(
    db: AsyncSession,
    wp_id: str,
    space_id: UUID,
) -> Document | None:
    """Find existing WP by instance_id within the same space."""
    result = await db.execute(
        select(Document).where(
            Document.doc_type_id == "work_package",
            Document.instance_id == wp_id,
            Document.space_id == space_id,
            Document.is_latest == True,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def _load_wp_document(
    db: AsyncSession, wp_id: str,
) -> Document:
    """Load a WP document by wp_id content field. 404 if not found."""
    result = await db.execute(
        select(Document).where(
            Document.doc_type_id == "work_package",
            Document.content["wp_id"].astext == wp_id,
        )
    )
    doc = result.scalars().first()
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Work Package '{wp_id}' not found",
        )
    return doc


async def _load_ws_document(
    db: AsyncSession, ws_id: str,
) -> Document:
    """Load a WS document by ws_id content field. 404 if not found."""
    result = await db.execute(
        select(Document).where(
            Document.doc_type_id == "work_statement",
            Document.content["ws_id"].astext == ws_id,
        )
    )
    doc = result.scalars().first()
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Work Statement '{ws_id}' not found",
        )
    return doc


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


async def _collect_promoted_wpc_ids(
    db: AsyncSession, space_id: UUID,
) -> set[str]:
    """Collect all WPC IDs that have been promoted to governed WPs.

    Uses lineage (source_candidate_ids on WP content), not naming conventions.
    """
    result = await db.execute(
        select(Document)
        .where(Document.space_type == "project")
        .where(Document.space_id == space_id)
        .where(Document.doc_type_id == "work_package")
        .where(Document.is_latest == True)  # noqa: E712
    )
    promoted_ids: set[str] = set()
    for wp_doc in result.scalars().all():
        src_ids = (wp_doc.content or {}).get("source_candidate_ids", [])
        promoted_ids.update(src_ids)
    return promoted_ids
