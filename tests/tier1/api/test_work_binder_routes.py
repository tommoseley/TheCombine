"""Tests for Work Binder API routes (WS-WB-003, WS-WB-006).

Tier-1 tests for work_binder router:
- Request/response model validation (WS-WB-003)
- Plane separation enforcement (WS-WB-006)
- Stabilization validation (WS-WB-006)
- WS CRUD operations (WS-WB-006)
- Duplicate WPC handling (promote resilience)

Pure business logic -- uses Pydantic model validation + mocked DB.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import MultipleResultsFound

from pydantic import ValidationError

from app.api.v1.routers.work_binder import (
    ImportCandidatesRequest,
    ImportCandidatesResponse,
    CandidateInfo,
    CreateWSRequest,
    ReorderWSRequest,
    WSResponse,
    WPCDetail,
    _load_wpc_document,
    router,
)


# ===========================================================================
# Request Model Tests (WS-WB-003)
# ===========================================================================

class TestImportCandidatesRequest:
    """Tests for ImportCandidatesRequest Pydantic model."""

    def test_valid_request(self):
        """Valid request with ip_document_id."""
        req = ImportCandidatesRequest(ip_document_id="abc-123")
        assert req.ip_document_id == "abc-123"

    def test_missing_ip_document_id_raises(self):
        """Missing ip_document_id raises validation error."""
        with pytest.raises(Exception):
            ImportCandidatesRequest()

    def test_empty_ip_document_id_raises(self):
        """Empty string ip_document_id raises validation error."""
        with pytest.raises(Exception):
            ImportCandidatesRequest(ip_document_id="")


# ===========================================================================
# Response Model Tests (WS-WB-003)
# ===========================================================================

class TestImportCandidatesResponse:
    """Tests for ImportCandidatesResponse Pydantic model."""

    def test_valid_response(self):
        """Valid response with candidates and count."""
        resp = ImportCandidatesResponse(
            candidates=[
                CandidateInfo(wpc_id="WPC-001", title="Registry Service"),
                CandidateInfo(wpc_id="WPC-002", title="Schema Validation"),
            ],
            count=2,
        )
        assert resp.count == 2
        assert len(resp.candidates) == 2
        assert resp.candidates[0].wpc_id == "WPC-001"

    def test_empty_candidates(self):
        """Valid response with zero candidates."""
        resp = ImportCandidatesResponse(candidates=[], count=0)
        assert resp.count == 0
        assert resp.candidates == []

    def test_serialization(self):
        """Response serializes to expected JSON shape."""
        resp = ImportCandidatesResponse(
            candidates=[
                CandidateInfo(wpc_id="WPC-001", title="Test"),
            ],
            count=1,
        )
        data = resp.model_dump()
        assert "candidates" in data
        assert "count" in data
        assert data["candidates"][0]["wpc_id"] == "WPC-001"
        assert data["candidates"][0]["title"] == "Test"


# ===========================================================================
# CandidateInfo Model Tests (WS-WB-003)
# ===========================================================================

class TestCandidateInfo:
    """Tests for CandidateInfo Pydantic model."""

    def test_valid_candidate_info(self):
        """Valid CandidateInfo with wpc_id and title."""
        info = CandidateInfo(wpc_id="WPC-001", title="Test Candidate")
        assert info.wpc_id == "WPC-001"
        assert info.title == "Test Candidate"

    def test_serialization(self):
        """CandidateInfo serializes correctly."""
        info = CandidateInfo(wpc_id="WPC-042", title="Answer Service")
        data = info.model_dump()
        assert data == {"wpc_id": "WPC-042", "title": "Answer Service"}


# ===========================================================================
# Test app setup (WS-WB-006)
# ===========================================================================

def _create_test_app() -> FastAPI:
    """Create a minimal FastAPI app with just the work_binder router."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return app


_app = _create_test_app()


# ===========================================================================
# Mock helpers (WS-WB-006)
# ===========================================================================

def _mock_wp_document(content: dict | None = None):
    """Create a mock WP document."""
    from datetime import datetime, timezone
    doc = MagicMock()
    doc.id = "ffddb4ff-f3fb-4481-ad7f-df59292c91ef"
    doc.space_type = "project"
    doc.space_id = "00000000-0000-0000-0000-000000000001"
    doc.created_at = datetime(2026, 3, 2, tzinfo=timezone.utc)
    doc.content = content or {
        "wp_id": "wp_wb_001",
        "title": "Test WP",
        "ws_index": [],
        "edition": 0,
    }
    return doc


def _mock_ws_document(content: dict | None = None):
    """Create a mock WS document."""
    doc = MagicMock()
    doc.content = content or {
        "ws_id": "WS-WB-001",
        "parent_wp_id": "wp_wb_001",
        "state": "DRAFT",
        "order_key": "a0",
        "revision": {"edition": 1},
        "title": "Test WS",
        "objective": "Test objective",
        "scope_in": [],
        "scope_out": [],
        "allowed_paths": [],
        "procedure": ["Step 1"],
        "verification_criteria": ["Check A"],
        "prohibited_actions": [],
        "governance_pins": {},
    }
    return doc


def _mock_db_session(wp_doc=None, ws_doc=None):
    """Create a mock async DB session."""
    db = AsyncMock()

    async def mock_execute(query):
        result = MagicMock()
        scalars = MagicMock()

        if wp_doc is not None and ws_doc is not None:
            if not hasattr(mock_execute, '_call_count'):
                mock_execute._call_count = 0
            mock_execute._call_count += 1
            if mock_execute._call_count == 1:
                scalars.first.return_value = wp_doc
                scalars.all.return_value = [ws_doc] if ws_doc else []
            else:
                scalars.first.return_value = ws_doc
                scalars.all.return_value = [ws_doc] if ws_doc else []
        elif wp_doc is not None:
            scalars.first.return_value = wp_doc
            scalars.all.return_value = []
        elif ws_doc is not None:
            scalars.first.return_value = ws_doc
            scalars.all.return_value = [ws_doc]
        else:
            scalars.first.return_value = None
            scalars.all.return_value = []

        result.scalars.return_value = scalars
        return result

    db.execute = mock_execute
    db.commit = AsyncMock()
    db.add = MagicMock()
    return db


# ===========================================================================
# Plane separation: WS PATCH rejects WP-level fields (WS-WB-006)
# ===========================================================================

class TestWSUpdatePlaneSeparation:

    @pytest.mark.asyncio
    async def test_ws_update_rejects_ws_index(self):
        """WP field 'ws_index' in WS PATCH body -> 400."""
        ws_doc = _mock_ws_document()
        db = _mock_db_session(ws_doc=ws_doc)

        async def override_get_db():
            yield db

        from app.core.database import get_db
        _app.dependency_overrides[get_db] = override_get_db

        try:
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.patch(
                    "/api/v1/work-binder/work-statements/WS-WB-001",
                    json={"ws_index": [], "title": "OK"},
                )
                assert resp.status_code == 400
                body = resp.json()
                assert body["detail"]["error_code"] == "PLANE_VIOLATION"
                assert any("ws_index" in e for e in body["detail"]["errors"])
        finally:
            _app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_ws_update_rejects_dependencies(self):
        """WP field 'dependencies' in WS PATCH body -> 400."""
        ws_doc = _mock_ws_document()
        db = _mock_db_session(ws_doc=ws_doc)

        async def override_get_db():
            yield db

        from app.core.database import get_db
        _app.dependency_overrides[get_db] = override_get_db

        try:
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.patch(
                    "/api/v1/work-binder/work-statements/WS-WB-001",
                    json={"dependencies": ["WS-001"]},
                )
                assert resp.status_code == 400
                body = resp.json()
                assert body["detail"]["error_code"] == "PLANE_VIOLATION"
        finally:
            _app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_ws_update_accepts_valid_fields(self):
        """Valid WS fields in WS PATCH body -> 200."""
        ws_doc = _mock_ws_document()
        db = _mock_db_session(ws_doc=ws_doc)

        async def override_get_db():
            yield db

        from app.core.database import get_db
        _app.dependency_overrides[get_db] = override_get_db

        try:
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.patch(
                    "/api/v1/work-binder/work-statements/WS-WB-001",
                    json={"title": "Updated title", "objective": "Updated objective"},
                )
                assert resp.status_code == 200
                body = resp.json()
                assert body["title"] == "Updated title"
                assert body["objective"] == "Updated objective"
        finally:
            _app.dependency_overrides = {}


# ===========================================================================
# Plane separation: WP PATCH rejects WS content fields (WS-WB-006)
# ===========================================================================

class TestWPUpdatePlaneSeparation:

    @pytest.mark.asyncio
    async def test_wp_update_rejects_objective(self):
        """WS field 'objective' in WP PATCH body -> 400."""
        wp_doc = _mock_wp_document()
        db = _mock_db_session(wp_doc=wp_doc)

        async def override_get_db():
            yield db

        from app.core.database import get_db
        _app.dependency_overrides[get_db] = override_get_db

        try:
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.patch(
                    "/api/v1/work-binder/wp/wp_wb_001",
                    json={"objective": "Should not be here"},
                )
                assert resp.status_code == 400
                body = resp.json()
                assert body["detail"]["error_code"] == "PLANE_VIOLATION"
                assert any("objective" in e for e in body["detail"]["errors"])
        finally:
            _app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_wp_update_rejects_procedure(self):
        """WS field 'procedure' in WP PATCH body -> 400."""
        wp_doc = _mock_wp_document()
        db = _mock_db_session(wp_doc=wp_doc)

        async def override_get_db():
            yield db

        from app.core.database import get_db
        _app.dependency_overrides[get_db] = override_get_db

        try:
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.patch(
                    "/api/v1/work-binder/wp/wp_wb_001",
                    json={"procedure": ["Step 1"]},
                )
                assert resp.status_code == 400
                body = resp.json()
                assert body["detail"]["error_code"] == "PLANE_VIOLATION"
        finally:
            _app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_wp_update_rejects_allowed_paths(self):
        """WS field 'allowed_paths' in WP PATCH body -> 400."""
        wp_doc = _mock_wp_document()
        db = _mock_db_session(wp_doc=wp_doc)

        async def override_get_db():
            yield db

        from app.core.database import get_db
        _app.dependency_overrides[get_db] = override_get_db

        try:
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.patch(
                    "/api/v1/work-binder/wp/wp_wb_001",
                    json={"allowed_paths": ["app/"]},
                )
                assert resp.status_code == 400
        finally:
            _app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_wp_update_accepts_valid_fields(self):
        """Valid WP fields in WP PATCH body -> 200."""
        wp_doc = _mock_wp_document()
        db = _mock_db_session(wp_doc=wp_doc)

        async def override_get_db():
            yield db

        from app.core.database import get_db
        _app.dependency_overrides[get_db] = override_get_db

        try:
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.patch(
                    "/api/v1/work-binder/wp/wp_wb_001",
                    json={"title": "Updated WP title", "rationale": "New rationale"},
                )
                assert resp.status_code == 200
                body = resp.json()
                assert body["status"] == "ok"
        finally:
            _app.dependency_overrides = {}


# ===========================================================================
# Stabilization validation (WS-WB-006)
# ===========================================================================

class TestStabilization:

    @pytest.mark.asyncio
    async def test_stabilize_succeeds_with_required_fields(self):
        """WS with all required fields -> READY."""
        ws_doc = _mock_ws_document({
            "ws_id": "WS-WB-001",
            "parent_wp_id": "wp_wb_001",
            "state": "DRAFT",
            "order_key": "a0",
            "revision": {"edition": 1},
            "title": "Complete WS",
            "objective": "Has objective",
            "procedure": ["Step 1"],
            "verification_criteria": ["Check 1"],
            "scope_in": [],
            "scope_out": [],
            "allowed_paths": [],
            "prohibited_actions": [],
            "governance_pins": {},
        })
        db = _mock_db_session(ws_doc=ws_doc)

        async def override_get_db():
            yield db

        from app.core.database import get_db
        _app.dependency_overrides[get_db] = override_get_db

        try:
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/work-binder/work-statements/WS-WB-001/stabilize",
                )
                assert resp.status_code == 200
                body = resp.json()
                assert body["state"] == "READY"
        finally:
            _app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_stabilize_fails_missing_title(self):
        """WS missing title -> 400 with stabilization errors."""
        ws_doc = _mock_ws_document({
            "ws_id": "WS-WB-001",
            "parent_wp_id": "wp_wb_001",
            "state": "DRAFT",
            "order_key": "a0",
            "revision": {"edition": 1},
            "title": "",
            "objective": "Has objective",
            "procedure": ["Step 1"],
            "verification_criteria": ["Check 1"],
            "scope_in": [],
            "scope_out": [],
            "allowed_paths": [],
            "prohibited_actions": [],
            "governance_pins": {},
        })
        db = _mock_db_session(ws_doc=ws_doc)

        async def override_get_db():
            yield db

        from app.core.database import get_db
        _app.dependency_overrides[get_db] = override_get_db

        try:
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/work-binder/work-statements/WS-WB-001/stabilize",
                )
                assert resp.status_code == 400
                body = resp.json()
                assert body["detail"]["error_code"] == "STABILIZATION_FAILED"
                assert any("title" in e for e in body["detail"]["errors"])
        finally:
            _app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_stabilize_fails_non_draft_state(self):
        """WS in READY state -> 400 invalid transition."""
        ws_doc = _mock_ws_document({
            "ws_id": "WS-WB-001",
            "parent_wp_id": "wp_wb_001",
            "state": "READY",
            "order_key": "a0",
            "revision": {"edition": 1},
            "title": "Complete WS",
            "objective": "Has objective",
            "procedure": ["Step 1"],
            "verification_criteria": ["Check 1"],
            "scope_in": [],
            "scope_out": [],
            "allowed_paths": [],
            "prohibited_actions": [],
            "governance_pins": {},
        })
        db = _mock_db_session(ws_doc=ws_doc)

        async def override_get_db():
            yield db

        from app.core.database import get_db
        _app.dependency_overrides[get_db] = override_get_db

        try:
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/work-binder/work-statements/WS-WB-001/stabilize",
                )
                assert resp.status_code == 400
                body = resp.json()
                assert body["detail"]["error_code"] == "INVALID_TRANSITION"
        finally:
            _app.dependency_overrides = {}


# ===========================================================================
# WS creation (WS-WB-006)
# ===========================================================================

class TestWSCreation:

    @pytest.mark.asyncio
    @patch("app.domain.services.display_id_service.mint_display_id", new_callable=AsyncMock, return_value="WS-001")
    async def test_create_ws_returns_201(self, mock_mint):
        """POST to create WS -> 201 with WS data (new display ID format)."""
        wp_doc = _mock_wp_document()
        db = _mock_db_session(wp_doc=wp_doc)

        async def override_get_db():
            yield db

        from app.core.database import get_db
        _app.dependency_overrides[get_db] = override_get_db

        try:
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/work-binder/wp/wp_wb_001/work-statements",
                    json={"title": "New WS", "objective": "Do something"},
                )
                assert resp.status_code == 201
                body = resp.json()
                assert body["ws_id"] == "WS-001"
                assert body["parent_wp_id"] == "wp_wb_001"
                assert body["state"] == "DRAFT"
                assert body["revision"] == {"edition": 1}
                assert body["order_key"] == "a0"
        finally:
            _app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_create_ws_not_found_wp(self):
        """POST to create WS with non-existent WP -> 404."""
        db = _mock_db_session()

        async def override_get_db():
            yield db

        from app.core.database import get_db
        _app.dependency_overrides[get_db] = override_get_db

        try:
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/work-binder/wp/wp_nonexistent/work-statements",
                    json={"title": "New WS"},
                )
                assert resp.status_code == 404
        finally:
            _app.dependency_overrides = {}


# ===========================================================================
# WSResponse revision normalization
# ===========================================================================

class TestWSResponseRevisionNormalization:
    """WSResponse must accept both legacy scalar int and dict revision."""

    def test_scalar_revision_normalized_to_dict(self):
        """Legacy DB records have revision=1 (int). Must not crash."""
        ws = WSResponse(
            ws_id="WS-001", parent_wp_id="wp_001",
            state="DRAFT", order_key="a0", revision=1,
        )
        assert ws.revision == {"edition": 1}

    def test_dict_revision_passes_through(self):
        """New-format revision dicts must pass through unchanged."""
        ws = WSResponse(
            ws_id="WS-001", parent_wp_id="wp_001",
            state="DRAFT", order_key="a0",
            revision={"edition": 3, "updated_at": "2026-03-03"},
        )
        assert ws.revision == {"edition": 3, "updated_at": "2026-03-03"}

    def test_default_revision(self):
        """When revision is omitted, default to {edition: 1}."""
        ws = WSResponse(
            ws_id="WS-001", parent_wp_id="wp_001",
            state="DRAFT", order_key="a0",
        )
        assert ws.revision == {"edition": 1}


# ===========================================================================
# WS GET endpoints (WS-WB-006)
# ===========================================================================

class TestWSGetEndpoints:

    @pytest.mark.asyncio
    async def test_get_ws_returns_content(self):
        """GET single WS -> 200 with content."""
        ws_doc = _mock_ws_document()
        db = _mock_db_session(ws_doc=ws_doc)

        async def override_get_db():
            yield db

        from app.core.database import get_db
        _app.dependency_overrides[get_db] = override_get_db

        try:
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(
                    "/api/v1/work-binder/work-statements/WS-WB-001",
                )
                assert resp.status_code == 200
                body = resp.json()
                assert body["ws_id"] == "WS-WB-001"
                assert body["state"] == "DRAFT"
        finally:
            _app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_get_ws_not_found(self):
        """GET non-existent WS -> 404."""
        db = _mock_db_session()

        async def override_get_db():
            yield db

        from app.core.database import get_db
        _app.dependency_overrides[get_db] = override_get_db

        try:
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(
                    "/api/v1/work-binder/work-statements/WS-NONEXISTENT",
                )
                assert resp.status_code == 404
        finally:
            _app.dependency_overrides = {}


# ===========================================================================
# WP Detail endpoint — full content for Work Binder UI
# ===========================================================================

# Promoted WP content matching build_promoted_wp output
_PROMOTED_WP_CONTENT = {
    "wp_id": "wp_wb_007",
    "title": "Order Execution Workflow",
    "rationale": "Implements the order execution workflow for paper trading.",
    "scope_in": ["Order execution workflow orchestration", "Alpaca API integration"],
    "scope_out": [],
    "dependencies": [],
    "definition_of_done": ["All work statements executed and verified"],
    "governance_pins": {"ta_version_id": "pending"},
    "state": "PLANNED",
    "ws_index": [],
    "revision": {
        "edition": 1,
        "updated_at": "2026-03-02T00:00:00+00:00",
        "updated_by": "system",
    },
    "source_candidate_ids": ["WPC-007"],
    "transformation": "kept",
    "transformation_notes": "Promoted as-is from IP candidate.",
    "_lineage": {
        "parent_document_type": "work_package_candidate",
        "parent_execution_id": None,
        "source_candidate_ids": ["WPC-007"],
        "transformation": "kept",
        "transformation_notes": "Promoted as-is from IP candidate.",
    },
}


class TestWPDetailEndpoint:
    """Tests for GET /work-binder/wp/{wp_id} detail endpoint.

    Reproduces the bug: promoted WP content (governance_pins, rationale,
    scope_in, transformation, source_candidate_ids) was not visible in
    the Work Binder UI because the list endpoint returns a summary projection.
    The detail endpoint must return the full document content.
    """

    @pytest.mark.asyncio
    async def test_detail_returns_full_content(self):
        """GET /wp/{wp_id} returns all content fields from promoted WP."""
        wp_doc = _mock_wp_document(_PROMOTED_WP_CONTENT)
        db = _mock_db_session(wp_doc=wp_doc)

        async def override_get_db():
            yield db

        from app.core.database import get_db
        _app.dependency_overrides[get_db] = override_get_db

        try:
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/work-binder/wp/wp_wb_007")
                assert resp.status_code == 200
                body = resp.json()

                # Core fields the summary endpoint strips
                assert body["rationale"] == "Implements the order execution workflow for paper trading."
                assert body["scope_in"] == ["Order execution workflow orchestration", "Alpaca API integration"]
                assert body["governance_pins"] == {"ta_version_id": "pending"}
                assert body["transformation"] == "kept"
                assert body["source_candidate_ids"] == ["WPC-007"]

                # DB-level metadata merged in
                assert body["id"] == "ffddb4ff-f3fb-4481-ad7f-df59292c91ef"
                assert "created_at" in body
        finally:
            _app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_detail_returns_lineage(self):
        """GET /wp/{wp_id} returns _lineage provenance chain."""
        wp_doc = _mock_wp_document(_PROMOTED_WP_CONTENT)
        db = _mock_db_session(wp_doc=wp_doc)

        async def override_get_db():
            yield db

        from app.core.database import get_db
        _app.dependency_overrides[get_db] = override_get_db

        try:
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/work-binder/wp/wp_wb_007")
                assert resp.status_code == 200
                body = resp.json()

                lineage = body["_lineage"]
                assert lineage["parent_document_type"] == "work_package_candidate"
                assert lineage["source_candidate_ids"] == ["WPC-007"]
                assert lineage["transformation"] == "kept"
        finally:
            _app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_detail_not_found(self):
        """GET /wp/{wp_id} with non-existent wp_id -> 404."""
        db = _mock_db_session()

        async def override_get_db():
            yield db

        from app.core.database import get_db
        _app.dependency_overrides[get_db] = override_get_db

        try:
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/work-binder/wp/wp_nonexistent")
                assert resp.status_code == 404
        finally:
            _app.dependency_overrides = {}


# ===========================================================================
# WS-WB-025: IA Contract Alignment Tests
# ===========================================================================


class TestReorderWSRequestValidation:
    """ReorderWSRequest must require ws_index with {ws_id, order_key} dicts."""

    def test_valid_ws_index_accepted(self):
        """ws_index with [{ws_id, order_key}] dicts is accepted."""
        req = ReorderWSRequest(ws_index=[
            {"ws_id": "WS-001", "order_key": "a0"},
            {"ws_id": "WS-002", "order_key": "a1"},
        ])
        assert len(req.ws_index) == 2
        assert req.ws_index[0]["ws_id"] == "WS-001"

    def test_ws_ids_array_rejected(self):
        """A payload with ws_ids (string array) must be rejected —
        the field name is ws_index, not ws_ids."""
        with pytest.raises(ValidationError):
            ReorderWSRequest(**{"ws_ids": ["WS-001", "WS-002"]})


class TestCreateWSIntentRegression:
    """CreateWSRequest must use title, not intent."""

    def test_title_field_accepted(self):
        """CreateWSRequest with title= populates the title field."""
        req = CreateWSRequest(title="Build logger")
        assert req.title == "Build logger"

    def test_intent_field_silently_dropped(self):
        """An 'intent' field is not part of CreateWSRequest — it gets
        silently ignored by Pydantic, leaving title empty."""
        req = CreateWSRequest(**{"intent": "Build logger"})
        assert req.title == ""


class TestWPCDetailSchemaFields:
    """WPCDetail must include source_ip_version and frozen_by (WS-WB-025 #5)."""

    def test_source_ip_version_field(self):
        """WPCDetail must accept and expose source_ip_version."""
        detail = WPCDetail(
            wpc_id="WPC-001",
            title="Test",
            source_ip_version="2.0.0",
        )
        assert detail.source_ip_version == "2.0.0"

    def test_frozen_by_field(self):
        """WPCDetail must accept and expose frozen_by."""
        detail = WPCDetail(
            wpc_id="WPC-001",
            title="Test",
            frozen_by="system",
        )
        assert detail.frozen_by == "system"

    def test_both_fields_default_empty(self):
        """When omitted, both fields default to empty string."""
        detail = WPCDetail(wpc_id="WPC-001", title="Test")
        assert detail.source_ip_version == ""
        assert detail.frozen_by == ""


# ===========================================================================
# Duplicate WPC handling: _load_wpc_document resilience
# ===========================================================================

class TestLoadWpcDocumentDuplicateResilience:
    """_load_wpc_document must not crash when duplicate WPCs exist.

    Bug: If import-candidates runs twice with different IP document IDs
    (e.g., IP re-created), duplicate WPC rows with the same display_id
    and is_latest=True are created. scalar_one_or_none() then raises
    MultipleResultsFound, causing a 500 on promote.

    Fix: Use scalars().first() to tolerate duplicates gracefully.
    """

    @pytest.mark.asyncio
    async def test_returns_doc_when_duplicates_exist(self):
        """_load_wpc_document returns first doc when duplicates exist."""
        mock_doc = MagicMock()
        mock_doc.display_id = "WPC-001"

        db = AsyncMock()
        result = MagicMock()
        # scalar_one_or_none would raise on duplicates (current bug)
        result.scalar_one_or_none.side_effect = MultipleResultsFound(
            "Multiple rows returned for one_or_none()"
        )
        # scalars().first() returns the first doc (desired behavior)
        scalars_mock = MagicMock()
        scalars_mock.first.return_value = mock_doc
        result.scalars.return_value = scalars_mock

        db.execute = AsyncMock(return_value=result)

        doc = await _load_wpc_document(db, "WPC-001")
        assert doc.display_id == "WPC-001"

    @pytest.mark.asyncio
    async def test_returns_404_when_no_docs(self):
        """_load_wpc_document raises 404 when no WPC found."""
        from fastapi import HTTPException

        db = AsyncMock()
        result = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.first.return_value = None
        result.scalars.return_value = scalars_mock

        db.execute = AsyncMock(return_value=result)

        with pytest.raises(HTTPException) as exc_info:
            await _load_wpc_document(db, "WPC-NONEXISTENT")
        assert exc_info.value.status_code == 404
