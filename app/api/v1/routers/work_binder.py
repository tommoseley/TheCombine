"""Work Binder API router — WS-WB-003, WS-WB-004, WS-WB-006, WS-WB-008, WS-WB-009, WS-WB-025.

Provides endpoints for Work Binder operations:
- GET /candidates — List WPC documents for a project (WS-WB-009)
- POST /import-candidates — Extract WP candidates from IP (WS-WB-003)
- POST /promote — Promote WPC to governed WP (WS-WB-004)
- POST /propose-ws — Propose WS drafts via LLM (WS-WB-025)
- POST /wp/{wp_id}/work-statements — Create WS (WS-WB-006)
- PATCH /work-statements/{ws_id} — Update WS content only
- PUT /wp/{wp_id}/ws-index — Reorder WSs (WP edition bump)
- PATCH /wp/{wp_id} — Update WP fields only
- GET /wp/{wp_id}/work-statements — List WSs in order
- GET /work-statements/{ws_id} — Get single WS
- GET /wp/{wp_id}/history — WP edition history
- POST /work-statements/{ws_id}/stabilize — DRAFT -> READY
- POST /wp/{wp_id}/stabilize — Stabilize all DRAFT WSs atomically (WS-WB-040)

Business logic lives in pure service modules.
This router handles DB access, idempotency, HTTP concerns,
governance invariant enforcement, and audit trail logging (WS-WB-008).
"""

import copy
import logging
from typing import Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models.document import Document
from app.api.models.project import Project
from app.core.database import get_db
from app.domain.services.candidate_import_service import import_candidates
from app.domain.services.wp_promotion_service import (
    build_audit_event,
    build_promoted_wp,
    validate_promotion_request,
)
from app.domain.services.ws_crud_service import (
    add_ws_to_wp_index,
    build_new_ws,
    generate_order_key,
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
from app.domain.services.ws_proposal_service import (
    build_ws_documents,
    build_ws_index_entries,
    validate_proposal_gates,
)
from app.domain.services.task_execution_service import (
    TaskExecutionError,
    TaskOutputParseError,
    TaskOutputValidationError,
    TaskPromptNotFoundError,
    execute_task,
)

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
                wpc_id=content.get("wpc_id", doc.display_id or ""),
                title=content.get("title", doc.title or ""),
                rationale=content.get("rationale", ""),
                scope_summary=content.get("scope_summary", []),
                source_ip_id=content.get("source_ip_id", ""),
                source_ip_version=content.get("source_ip_version", ""),
                frozen_at=content.get("frozen_at", ""),
                frozen_by=content.get("frozen_by", ""),
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
            db, wpc_id, ip_doc.space_id,
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
            display_id=wpc_id,
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

    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        logger.warning(
            "IntegrityError during candidate import for IP %s — "
            "candidates likely already exist (concurrent or re-import)",
            request.ip_document_id,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Candidates already exist for this project. Refresh and retry.",
        )

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

    project = await _resolve_project(db, request.project_id)
    wpc_doc = await _load_wpc_document(db, request.wpc_id, project.id)

    # Check for existing WP promoted from this WPC (idempotency)
    existing_wp = await _find_wp_by_source_wpc(db, request.wpc_id, wpc_doc.space_id)
    if existing_wp:
        existing_wp_id = (existing_wp.content or {}).get("wp_id", existing_wp.display_id or "")
        logger.info(
            f"WP {existing_wp_id} already exists for WPC {request.wpc_id} "
            f"-- returning existing (idempotent)"
        )
        return PromoteCandidateResponse(
            wp_id=existing_wp_id,
            document_id=str(existing_wp.id),
        )

    # Mint a new display ID for the WP (replaces derive_wp_id)
    from app.domain.services.display_id_service import mint_display_id
    wp_id = await mint_display_id(db, wpc_doc.space_id, "work_package")

    wp_content = build_promoted_wp(
        candidate=wpc_doc.content,
        wp_id=wp_id,
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
        display_id=wp_id,
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
# WS-WB-025: Propose Work Statements (LLM Draft Station)
# ===========================================================================


@router.post("/propose-ws", response_model=ProposeWSResponse)
async def propose_work_statements(
    request: ProposeWSRequest,
    db: AsyncSession = Depends(get_db),
) -> ProposeWSResponse:
    """Propose WS drafts for a promoted WP via LLM.

    This is the first LLM boundary crossing in the Work Binder.
    Gates: TA must be ready, WP ws_index must be empty.
    Produces DRAFT-only WS artifacts, validated before persistence.
    """
    # --- Resolve project FIRST (scoping) ---
    project = await _resolve_project(db, request.project_id)

    # --- Resolve WP (scoped to project) ---
    wp_doc = await _load_wp_document(db, request.wp_id, space_id=str(project.id))
    wp_content = dict(wp_doc.content or {})

    # --- Resolve TA ---
    ta_doc = await _find_ta_for_project(db, project.id)

    # --- Gate checks (mechanical) ---
    gate_errors = validate_proposal_gates(wp_content, ta_doc)
    if gate_errors:
        # Determine status code: ws_index conflict -> 409, else 400
        status_code = (
            status.HTTP_409_CONFLICT
            if any("already has Work Statements" in e for e in gate_errors)
            else status.HTTP_400_BAD_REQUEST
        )

        # Audit: rejection
        audit_evt = build_wb_audit_event(
            event_type="ws_proposal_rejected",
            entity_id=request.wp_id,
            entity_type="work_package",
            mutation_data={
                "project_id": request.project_id,
                "reason": "; ".join(gate_errors),
            },
            actor="system",
        )
        logger.info("AUDIT: %s", audit_evt)

        raise HTTPException(
            status_code=status_code,
            detail="; ".join(gate_errors),
        )

    # --- Audit: proposal requested ---
    ta_version = str(ta_doc.version) if ta_doc else "unknown"
    audit_req = build_wb_audit_event(
        event_type="ws_proposal_requested",
        entity_id=request.wp_id,
        entity_type="work_package",
        mutation_data={
            "project_id": request.project_id,
            "ta_version": ta_version,
        },
        actor="system",
    )
    logger.info("AUDIT: %s", audit_req)

    # --- LLM call via task execution primitive (WS-WB-022) ---
    import json as _json
    import os as _os
    wp_json = _json.dumps(wp_content, indent=2, default=str)
    ta_json = _json.dumps(ta_doc.content or {}, indent=2, default=str)

    # Wire up LLM client
    from app.llm.providers.anthropic import AnthropicProvider
    from app.domain.workflow.nodes.llm_executors import LoggingLLMService

    api_key = _os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ANTHROPIC_API_KEY not configured",
        )
    llm_client = LoggingLLMService(
        provider=AnthropicProvider(api_key=api_key),
        default_max_tokens=16384,
    )

    try:
        result = await execute_task(
            task_id="propose_work_statements",
            version="1.0.0",
            inputs={"work_package": wp_json, "technical_architecture": ta_json},
            expected_schema_id="work_statement",
            llm_client=llm_client,
        )
    except TaskPromptNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Task prompt not found: {exc}",
        )
    except TaskOutputParseError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"LLM output parse failed: {exc}",
        )
    except TaskOutputValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"LLM output schema validation failed: {exc}",
        )
    except TaskExecutionError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Task execution failed: {exc}",
        )

    # --- Parse LLM output ---
    # Output may be a single WS dict or a list of WS dicts
    raw_output = result["output"]
    if isinstance(raw_output, dict):
        ws_items = [raw_output]
    elif isinstance(raw_output, list):
        ws_items = raw_output
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="LLM output is not a dict or list of WS objects",
        )

    if not ws_items:
        return ProposeWSResponse(
            wp_id=request.wp_id,
            created=False,
            ws_ids=[],
        )

    # --- Mint display IDs and build WS documents ---
    # Replace LLM-generated ws_ids with minted sequential IDs.
    # Mint the first ID via DB query, then increment locally for the batch
    # (unflushed rows aren't visible to subsequent MAX queries).
    from app.domain.services.display_id_service import mint_display_id, parse_display_id
    first_ws_id = await mint_display_id(db, wp_doc.space_id, "work_statement")
    prefix, num_str = parse_display_id(first_ws_id)
    first_num = int(num_str)
    for i, ws_item in enumerate(ws_items):
        ws_item["ws_id"] = f"{prefix}-{first_num + i:03d}"

    ws_docs_data = build_ws_documents(ws_items, request.wp_id)
    ws_index_entries = build_ws_index_entries(ws_items)

    # --- Persist WS documents ---
    ws_ids = []
    for ws_data in ws_docs_data:
        ws_id = ws_data["ws_id"]
        ws_doc = Document(
            space_type=wp_doc.space_type,
            space_id=wp_doc.space_id,
            doc_type_id="work_statement",
            title=ws_data.get("title", ws_id),
            content=ws_data,
            version=1,
            status="draft",
            lifecycle_state="complete",
            display_id=ws_id,
            created_by="system",
            created_by_type="llm_proposal",
        )
        ws_doc.update_revision_hash()
        db.add(ws_doc)
        ws_ids.append(ws_id)

        # Audit: per-WS
        audit_ws = build_wb_audit_event(
            event_type="ws_proposed",
            entity_id=ws_id,
            entity_type="work_statement",
            mutation_data={
                "wp_id": request.wp_id,
                "project_id": request.project_id,
            },
            actor="system",
        )
        logger.info("AUDIT: %s", audit_ws)

    # --- Update WP ws_index (new edition) ---
    old_content = copy.deepcopy(wp_content)
    wp_content["ws_index"] = ws_index_entries
    wp_content = apply_edition_bump(wp_content, old_content, "system")
    wp_doc.content = wp_content

    await db.flush()

    # Audit: ws_index updated
    audit_idx = build_wb_audit_event(
        event_type="wp_ws_index_updated",
        entity_id=request.wp_id,
        entity_type="work_package",
        mutation_data={
            "before_count": 0,
            "after_count": len(ws_ids),
            "ws_ids": ws_ids,
        },
        actor="system",
    )
    logger.info("AUDIT: %s", audit_idx)

    logger.info(
        "Proposed %d WS drafts for WP %s", len(ws_ids), request.wp_id,
    )

    return ProposeWSResponse(
        wp_id=request.wp_id,
        created=True,
        ws_ids=ws_ids,
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
    project_id: str | None = Query(None, description="Project scope"),
) -> WSResponse:
    """Create a new WS under the given WP."""
    # --- Governance: provenance check (WS-WB-008) ---
    prov_errors = validate_provenance("system")
    if prov_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="; ".join(prov_errors),
        )

    space_id = await _resolve_space_id(db, project_id)
    wp_doc = await _load_wp_document(db, wp_id, space_id=space_id)

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

    from app.domain.services.display_id_service import mint_display_id
    ws_id = await mint_display_id(db, wp_doc.space_id, "work_statement")
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
        display_id=ws_id,
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
    project_id: str | None = Query(None, description="Project scope"),
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

    space_id = await _resolve_space_id(db, project_id)
    ws_doc = await _load_ws_document(db, ws_id, space_id=space_id)
    ws_content = dict(ws_doc.content or {})

    for key, value in update_data.items():
        ws_content[key] = value

    rev = ws_content.get("revision", {})
    if isinstance(rev, int):
        rev = {"edition": rev}
    old_edition = rev.get("edition", 0)
    rev["edition"] = old_edition + 1
    ws_content["revision"] = rev
    ws_doc.content = ws_content
    await db.flush()

    # --- Audit trail (WS-WB-008) ---
    audit_evt = build_wb_audit_event(
        event_type="ws_updated",
        entity_id=ws_id,
        entity_type="work_statement",
        mutation_data={
            "fields_updated": list(update_data.keys()),
            "edition_before": old_edition,
            "edition_after": rev["edition"],
        },
        actor="system",
    )
    logger.info("AUDIT: %s", audit_evt)

    logger.info(
        "Updated WS %s (edition %d)", ws_id, rev["edition"]
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
    project_id: str | None = Query(None, description="Project scope"),
) -> dict[str, Any]:
    """Reorder WSs in a WP. Bumps WP edition."""
    # --- Governance: provenance check (WS-WB-008) ---
    prov_errors = validate_provenance("system")
    if prov_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="; ".join(prov_errors),
        )

    space_id = await _resolve_space_id(db, project_id)
    wp_doc = await _load_wp_document(db, wp_id, space_id=space_id)

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
    project_id: str | None = Query(None, description="Project scope"),
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

    space_id = await _resolve_space_id(db, project_id)
    wp_doc = await _load_wp_document(db, wp_id, space_id=space_id)
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
# WP Detail (full content for Work Binder UI)
# ===========================================================================


@router.get("/wp/{wp_id}")
async def get_work_package_detail(
    wp_id: str,
    db: AsyncSession = Depends(get_db),
    project_id: str | None = Query(None, description="Project scope"),
) -> dict[str, Any]:
    """Return full WP content for the Work Binder detail view.

    The list endpoint (GET /projects/{id}/work-packages) returns a summary
    projection.  This endpoint returns the complete document content so
    sub-views (Governance, History, Work) can render all fields.
    """
    space_id = await _resolve_space_id(db, project_id)
    wp_doc = await _load_wp_document(db, wp_id, space_id=space_id)
    content = dict(wp_doc.content or {})
    # Merge DB-level metadata the SPA expects
    content["id"] = str(wp_doc.id)
    content["created_at"] = (
        wp_doc.created_at.isoformat() if wp_doc.created_at else ""
    )
    return content


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
    project_id: str | None = Query(None, description="Project scope"),
) -> WSListResponse:
    """List WSs under a WP in ws_index order."""
    space_id = await _resolve_space_id(db, project_id)
    wp_doc = await _load_wp_document(db, wp_id, space_id=space_id)
    wp_content = wp_doc.content or {}
    ws_index = wp_content.get("ws_index", [])

    ordered_ws_ids = [e.get("ws_id") for e in ws_index]

    # Use the WP's content wp_id for WS lookup (may differ from URL wp_id
    # for WPs created before the promotion flow standardized naming)
    content_wp_id = wp_content.get("wp_id", wp_id)

    # Match WSs by either the content wp_id or the URL wp_id
    from sqlalchemy import or_
    wp_id_filters = [Document.content["parent_wp_id"].astext == content_wp_id]
    if content_wp_id != wp_id:
        wp_id_filters.append(Document.content["parent_wp_id"].astext == wp_id)

    result = await db.execute(
        select(Document).where(
            Document.doc_type_id == "work_statement",
            or_(*wp_id_filters),
            Document.space_id == wp_doc.space_id,
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
    project_id: str | None = Query(None, description="Project scope"),
) -> WSResponse:
    """Get a single WS by ID."""
    space_id = await _resolve_space_id(db, project_id)
    ws_doc = await _load_ws_document(db, ws_id, space_id=space_id)
    return WSResponse(**(ws_doc.content or {}))


# ===========================================================================
# WS-WB-006: WP Edition History
# ===========================================================================


@router.get("/wp/{wp_id}/history")
async def get_wp_history(
    wp_id: str,
    db: AsyncSession = Depends(get_db),
    project_id: str | None = Query(None, description="Project scope"),
) -> dict[str, Any]:
    """Get WP edition history."""
    space_id = await _resolve_space_id(db, project_id)
    wp_doc = await _load_wp_document(db, wp_id, space_id=space_id)
    wp_content = wp_doc.content or {}

    revision = wp_content.get("revision", {})
    edition = revision.get("edition", 0) if isinstance(revision, dict) else 0
    change_summary = wp_content.get("change_summary", [])

    editions = []
    if edition > 0 or change_summary:
        editions.append({
            "edition": edition,
            "timestamp": revision.get("updated_at", "") if isinstance(revision, dict) else "",
            "updated_by": revision.get("updated_by", "") if isinstance(revision, dict) else "",
            "change_summary": change_summary,
        })

    return {
        "wp_id": wp_id,
        "editions": editions,
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
    project_id: str | None = Query(None, description="Project scope"),
) -> WSResponse:
    """Stabilize a WS: DRAFT -> READY with field validation."""
    # --- Governance: provenance check (WS-WB-008) ---
    prov_errors = validate_provenance("system")
    if prov_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="; ".join(prov_errors),
        )

    space_id = await _resolve_space_id(db, project_id)
    ws_doc = await _load_ws_document(db, ws_id, space_id=space_id)
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
    stab_rev = ws_content.get("revision", {})
    if isinstance(stab_rev, int):
        stab_rev = {"edition": stab_rev}
    stab_rev["edition"] = stab_rev.get("edition", 0) + 1
    ws_content["revision"] = stab_rev

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
# WS-WB-040: Stabilize Work Package (all DRAFT WSs -> READY atomically)
# ===========================================================================


class WPStabilizeResponse(BaseModel):
    """Response from WP-level stabilize."""
    wp_id: str
    stabilized: list[str]
    count: int


@router.post(
    "/wp/{wp_id}/stabilize",
    response_model=WPStabilizeResponse,
    summary="Stabilize all DRAFT work statements in a Work Package",
)
async def stabilize_work_package(
    wp_id: str,
    db: AsyncSession = Depends(get_db),
    project_id: str | None = Query(None, description="Project scope"),
) -> WPStabilizeResponse:
    """Atomically stabilize all DRAFT WSs under a WP.

    Validates all DRAFT WSs first. If any fail validation, none are transitioned.
    """
    # --- Governance: provenance check ---
    prov_errors = validate_provenance("system")
    if prov_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="; ".join(prov_errors),
        )

    space_id = await _resolve_space_id(db, project_id)
    wp_doc = await _load_wp_document(db, wp_id, space_id=space_id)
    wp_content = wp_doc.content or {}

    # Load all WSs under this WP (same query as list_work_statements)
    content_wp_id = wp_content.get("wp_id", wp_id)
    from sqlalchemy import or_
    wp_id_filters = [Document.content["parent_wp_id"].astext == content_wp_id]
    if content_wp_id != wp_id:
        wp_id_filters.append(Document.content["parent_wp_id"].astext == wp_id)

    result = await db.execute(
        select(Document).where(
            Document.doc_type_id == "work_statement",
            or_(*wp_id_filters),
            Document.space_id == wp_doc.space_id,
        )
    )
    ws_docs = [doc for doc in result.scalars().all() if doc.content]

    # Filter to DRAFT WSs only
    draft_docs = [doc for doc in ws_docs if (doc.content or {}).get("state", "DRAFT") == "DRAFT"]

    if not draft_docs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "NO_DRAFT_STATEMENTS",
                "message": "No DRAFT work statements to stabilize",
            },
        )

    # Validate ALL drafts before transitioning any (all-or-nothing)
    all_errors: dict[str, list[str]] = {}
    for doc in draft_docs:
        ws_content = doc.content or {}
        ws_id_val = ws_content.get("ws_id", str(doc.id))
        errors = validate_stabilization(ws_content)
        if errors:
            all_errors[ws_id_val] = errors

    if all_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "STABILIZATION_FAILED",
                "errors": all_errors,
            },
        )

    # Transition all DRAFT WSs to READY
    stabilized_ids: list[str] = []
    for doc in draft_docs:
        ws_content = dict(doc.content)
        ws_content["state"] = "READY"
        rev = ws_content.get("revision", {})
        if isinstance(rev, int):
            rev = {"edition": rev}
        rev["edition"] = rev.get("edition", 0) + 1
        ws_content["revision"] = rev
        doc.content = ws_content
        stabilized_ids.append(ws_content.get("ws_id", str(doc.id)))

    await db.flush()

    # --- Audit trail ---
    audit_evt = build_wb_audit_event(
        event_type="wp_stabilized",
        entity_id=wp_id,
        entity_type="work_package",
        mutation_data={
            "stabilized_ws_ids": stabilized_ids,
            "count": len(stabilized_ids),
        },
        actor="system",
    )
    logger.info("AUDIT: %s", audit_evt)
    logger.info("Stabilized WP %s: %d WSs DRAFT -> READY", wp_id, len(stabilized_ids))

    return WPStabilizeResponse(
        wp_id=wp_id,
        stabilized=stabilized_ids,
        count=len(stabilized_ids),
    )


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
    space_id: UUID,
) -> Document | None:
    """Find existing WPC by wpc_id within the same space.

    Checks display_id + space_id only (not IP provenance). This prevents
    duplicate WPCs when import-candidates runs against different IP document
    versions that contain the same candidate IDs.
    """
    result = await db.execute(
        select(Document).where(
            Document.doc_type_id == "work_package_candidate",
            Document.display_id == wpc_id,
            Document.space_id == space_id,
            Document.is_latest == True,  # noqa: E712
        )
    )
    return result.scalars().first()


async def _load_wpc_document(
    db: AsyncSession, wpc_id: str, space_id: UUID | None = None,
) -> Document:
    """Load a WPC document by display_id, scoped to space_id. 404 if not found.

    Uses scalars().first() instead of scalar_one_or_none() to tolerate
    duplicate WPC rows (created when import-candidates runs against
    different IP document versions with the same candidate IDs).
    """
    query = select(Document).where(
        Document.doc_type_id == "work_package_candidate",
        Document.display_id == wpc_id,
        Document.is_latest == True,  # noqa: E712
    )
    if space_id is not None:
        query = query.where(Document.space_id == space_id)
    result = await db.execute(query.order_by(Document.created_at.desc()))
    doc = result.scalars().first()

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
    """Find existing WP by display_id within the same space."""
    result = await db.execute(
        select(Document).where(
            Document.doc_type_id == "work_package",
            Document.display_id == wp_id,
            Document.space_id == space_id,
            Document.is_latest == True,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def _find_wp_by_source_wpc(
    db: AsyncSession,
    wpc_id: str,
    space_id: UUID,
) -> Document | None:
    """Find existing WP promoted from a given WPC (idempotency check).

    Searches WP documents in the space whose content.source_candidate_ids
    contains the given wpc_id.
    """
    result = await db.execute(
        select(Document).where(
            Document.doc_type_id == "work_package",
            Document.space_id == space_id,
            Document.is_latest == True,  # noqa: E712
            Document.content["source_candidate_ids"].astext.contains(wpc_id),
        )
    )
    return result.scalars().first()


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
