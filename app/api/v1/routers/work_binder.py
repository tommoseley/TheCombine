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

Sub-routers:
- work_binder_candidates: candidate listing, import, promotion
- work_binder_statements: WS CRUD, reorder, stabilize
- work_binder_proposals: LLM-based WS proposal
- work_binder_common: shared models and helpers
"""

from fastapi import APIRouter

from app.api.v1.routers.work_binder_candidates import router as candidates_router
from app.api.v1.routers.work_binder_statements import router as statements_router
from app.api.v1.routers.work_binder_proposals import router as proposals_router

# Re-export models and helpers so existing tests that import from
# app.api.v1.routers.work_binder continue to work.
from app.api.v1.routers.work_binder_common import (  # noqa: F401
    CandidateInfo,
    CreateWSRequest,
    ImportCandidatesRequest,
    ImportCandidatesResponse,
    PromoteCandidateRequest,
    PromoteCandidateResponse,
    ProposeWSRequest,
    ProposeWSResponse,
    ReorderWSRequest,
    UpdateWPRequest,
    UpdateWSRequest,
    WPCDetail,
    WPCListResponse,
    WPStabilizeResponse,
    WSListResponse,
    WSResponse,
    _find_ip_for_project,
    _find_ta_for_project,
    _load_ip_document,
    _load_wp_document,
    _load_ws_document,
    _resolve_project,
    _resolve_space_id,
)

# Re-export candidate helpers used by tests
from app.api.v1.routers.work_binder_candidates import (  # noqa: F401
    _load_wpc_document,
)

router = APIRouter(prefix="/work-binder", tags=["work-binder"])
router.include_router(candidates_router)
router.include_router(statements_router)
router.include_router(proposals_router)


# ---------------------------------------------------------------------------
# Binder assembly (ADR-071)
# ---------------------------------------------------------------------------

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update
from uuid import uuid4
from datetime import datetime, timezone

from app.core.database import get_db
from app.api.models.document import Document


@router.post("/{project_id}/assemble")
async def assemble_work_binder(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Assemble a work binder from current project documents.

    Creates (or replaces) the work_binder document with version-pinned
    references to all project documents. Per ADR-071.
    """
    from app.domain.services.binder_assembly_service import assemble_binder
    from app.api.v1.routers.work_binder_common import _resolve_space_id

    space_id = await _resolve_space_id(db, project_id)

    binder_content = await assemble_binder(db, str(space_id))

    # Mark any prior work_binder as not latest
    await db.execute(
        update(Document)
        .where(
            and_(
                Document.space_id == space_id,
                Document.doc_type_id == "work_binder",
                Document.is_latest == True,  # noqa: E712
            )
        )
        .values(is_latest=False)
    )

    # Create new binder document
    binder_doc = Document(
        id=uuid4(),
        space_type="project",
        space_id=space_id,
        doc_type_id="work_binder",
        display_id=f"WB-{str(uuid4())[:6].upper()}",
        title="Work Binder",
        content=binder_content.to_dict(),
        version=1,
        is_latest=True,
        lifecycle_state="complete",
        status="active",
        builder_metadata={
            "generator": "binder_assembly_service",
            "adr": "ADR-071",
            "assembled_at": binder_content.assembled_at,
        },
    )

    db.add(binder_doc)
    await db.commit()

    return {
        "status": "assembled",
        "document_id": str(binder_doc.id),
        "document_count": binder_content.document_count,
        "groups": binder_content.groups,
    }


@router.get("/{project_id}/binder")
async def get_work_binder(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get the latest assembled work binder for a project."""
    from app.api.v1.routers.work_binder_common import _resolve_space_id

    space_id = await _resolve_space_id(db, project_id)

    stmt = (
        select(Document)
        .where(
            and_(
                Document.space_id == space_id,
                Document.doc_type_id == "work_binder",
                Document.is_latest == True,  # noqa: E712
            )
        )
        .limit(1)
    )
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="No work binder found")

    return {
        "document_id": str(doc.id),
        "project_id": project_id,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "content": doc.content,
    }


@router.post("/{project_id}/assemble-plan")
async def assemble_work_plan_endpoint(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Assemble the final Work Plan from project state.

    Creates (or replaces) the work_plan document with executive summary,
    decision log, dependency summary, and version-pinned document references.
    Per ADR-071 s3.8.
    """
    from app.domain.services.work_plan_assembly_service import assemble_work_plan
    from app.api.v1.routers.work_binder_common import _resolve_space_id

    space_id = await _resolve_space_id(db, project_id)

    plan_content = await assemble_work_plan(db, str(space_id))

    # Mark any prior work_plan as not latest
    await db.execute(
        update(Document)
        .where(
            and_(
                Document.space_id == space_id,
                Document.doc_type_id == "work_plan",
                Document.is_latest == True,  # noqa: E712
            )
        )
        .values(is_latest=False)
    )

    # Create new Work Plan document
    plan_doc = Document(
        id=uuid4(),
        space_type="project",
        space_id=space_id,
        doc_type_id="work_plan",
        display_id=f"PLAN-{str(uuid4())[:6].upper()}",
        title="Work Plan",
        content=plan_content.to_dict(),
        version=1,
        is_latest=True,
        lifecycle_state="complete",
        status="active",
        builder_metadata={
            "generator": "work_plan_assembly_service",
            "adr": "ADR-071",
            "assembled_at": plan_content.assembled_at,
        },
    )

    db.add(plan_doc)
    await db.commit()

    return {
        "status": "assembled",
        "document_id": str(plan_doc.id),
        "document_count": plan_content.document_count,
        "executive_summary": plan_content.executive_summary,
        "decision_count": len(plan_content.decision_log),
        "dependency_count": len(plan_content.dependency_summary),
    }
