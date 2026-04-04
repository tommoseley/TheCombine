"""Work Binder statement routes — WS-WB-006, WS-WB-040.

Endpoints for creating, updating, listing, reordering, and stabilizing
Work Statements and Work Packages.
"""

import copy
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models.document import Document
from app.core.database import get_db
from app.domain.services.ws_crud_service import (
    add_ws_to_wp_index,
    build_new_ws,
    certify_wp_for_stabilization,
    check_blocking_unknowns,
    check_parent_wp_invariant,
    check_ws_referential_integrity,
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
    validate_can_reorder,
    validate_provenance,
)
from app.domain.services.work_statement_state import validate_ws_transition
from app.domain.services.document_builder_pure import apply_post_processing

from app.api.v1.routers.work_binder_common import (
    CreateWSRequest,
    ReorderWSRequest,
    UpdateWPRequest,
    UpdateWSRequest,
    WPStabilizeResponse,
    WSListResponse,
    WSResponse,
    _load_wp_document,
    _load_ws_document,
    _resolve_space_id,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["work-binder"])


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
    apply_post_processing(ws_data, "work_statement")

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
    await db.commit()

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

    # --- Certification gate: completeness + governance (WS-PI-2A) ---
    cert_findings = certify_wp_for_stabilization(
        wp_content, [doc.content for doc in ws_docs]
    )
    if cert_findings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "CERTIFICATION_FAILED",
                "findings": [f.to_dict() for f in cert_findings],
            },
        )

    # --- Referential integrity gate (WS-PI-2B) ---
    persisted_ws_ids = [
        (doc.content or {}).get("ws_id", str(doc.id)) for doc in ws_docs
    ]
    ref_findings = check_ws_referential_integrity(wp_content, persisted_ws_ids)
    if ref_findings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "REFERENTIAL_INTEGRITY_FAILED",
                "findings": [f.to_dict() for f in ref_findings],
            },
        )

    # --- Parent WP invariant (WS-PI-2C) ---
    content_wp_id = wp_content.get("wp_id", wp_id)
    parent_findings = check_parent_wp_invariant(
        content_wp_id, [doc.content for doc in ws_docs]
    )
    if parent_findings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "PARENT_WP_MISMATCH",
                "findings": [f.to_dict() for f in parent_findings],
            },
        )

    # --- Blocking unknowns gate (WS-PI-UNK) ---
    if project_id:
        pd_result = await db.execute(
            select(Document).where(
                Document.doc_type_id == "project_discovery",
                Document.space_type == "project",
                Document.space_id == space_id,
            ).order_by(Document.updated_at.desc()).limit(1)
        )
        pd_doc = pd_result.scalar_one_or_none()
        pd_content = pd_doc.content if pd_doc else None
        unk_findings = check_blocking_unknowns(pd_content)
        if unk_findings:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "BLOCKING_UNKNOWNS",
                    "findings": [f.to_dict() for f in unk_findings],
                },
            )

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
    await db.commit()

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
