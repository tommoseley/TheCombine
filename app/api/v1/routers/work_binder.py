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
