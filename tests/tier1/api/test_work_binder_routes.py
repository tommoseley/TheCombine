"""Tests for Work Binder API routes (WS-WB-003, WS-WB-006).

Tier-1 tests for work_binder router:
- Request/response model validation (WS-WB-003)
- Plane separation enforcement (WS-WB-006)
- Stabilization validation (WS-WB-006)
- WS CRUD operations (WS-WB-006)

Pure business logic -- uses Pydantic model validation + mocked DB.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.routers.work_binder import (
    ImportCandidatesRequest,
    ImportCandidatesResponse,
    CandidateInfo,
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
    doc = MagicMock()
    doc.space_type = "project"
    doc.space_id = "00000000-0000-0000-0000-000000000001"
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
        "revision": 1,
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
            "revision": 1,
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
            "revision": 1,
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
            "revision": 1,
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
    async def test_create_ws_returns_201(self):
        """POST to create WS -> 201 with WS data."""
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
                assert body["ws_id"] == "WS-WB-001"
                assert body["parent_wp_id"] == "wp_wb_001"
                assert body["state"] == "DRAFT"
                assert body["revision"] == 1
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
