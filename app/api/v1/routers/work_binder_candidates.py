"""Work Binder candidate routes — WS-WB-003, WS-WB-004, WS-WB-009.

Endpoints for listing, importing, and promoting WP candidates.
"""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models.document import Document
from app.core.database import get_db
from app.domain.services.candidate_import_service import import_candidates
from app.api.v1.services.render_pure import unwrap_raw_envelope
from app.domain.services.wp_promotion_service import (
    build_audit_event,
    build_promoted_wp,
    validate_promotion_request,
    validate_ta_for_promotion,
)
from app.domain.services.document_builder_pure import apply_post_processing
from app.domain.services.wb_audit_service import (
    build_audit_event as build_wb_audit_event,
    validate_can_promote,
    validate_provenance,
)

from app.api.v1.routers.work_binder_common import (
    CandidateInfo,
    ImportCandidatesRequest,
    ImportCandidatesResponse,
    PromoteCandidateRequest,
    PromoteCandidateResponse,
    WPCDetail,
    WPCListResponse,
    _load_ip_document,
    _resolve_project,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["work-binder"])


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

    # No WPCs -- check if an IP document exists for import
    from app.api.v1.routers.work_binder_common import _find_ip_for_project
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
    ip_content = unwrap_raw_envelope(ip_doc.content)
    wpc_documents = import_candidates(
        ip_content=ip_content,
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

    # --- TA version gate: resolve ta_version_id from TA document ---
    ta_result = await db.execute(
        select(Document).where(
            Document.doc_type_id == "technical_architecture",
            Document.space_id == wpc_doc.space_id,
            Document.space_type == "project",
        ).order_by(Document.created_at.desc()).limit(1)
    )
    ta_doc_row = ta_result.scalars().first()
    ta_version_id = validate_ta_for_promotion(
        {"display_id": ta_doc_row.display_id, "content": ta_doc_row.content} if ta_doc_row else None
    )
    if ta_version_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "TA_VERSION_REQUIRED",
                "message": "Cannot promote WPC to WP: no Technical Architecture document found for this project. "
                           "A TA must exist before WP promotion to establish governance lineage.",
            },
        )

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
        ta_version_id=ta_version_id,
    )

    apply_post_processing(wp_content, "work_package")
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

    # Legacy audit event (wp_promotion_service) -- retained for compatibility
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
# Internal Helpers (candidate-specific)
# ===========================================================================


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
