"""Tests for WP-level stabilize endpoint (WS-WB-040).

Tier-1 tests: mock DB, ASGI transport, pure business logic.

Test cases:
- Happy path: all DRAFT WSs stabilized atomically
- Mixed states: only DRAFT WSs are transitioned, READY ones untouched
- Validation failure: one bad WS blocks all (atomicity)
- No DRAFT WSs: returns 400
- No WSs at all: returns 400
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from datetime import datetime, timezone
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.routers.work_binder import router


# ===========================================================================
# Test app
# ===========================================================================

def _create_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return app


_app = _create_test_app()


# ===========================================================================
# Mock helpers
# ===========================================================================

def _make_wp_doc(wp_id="wp_test_001", ws_index=None, space_id="00000000-0000-0000-0000-000000000001"):
    doc = MagicMock()
    doc.id = "ffddb4ff-f3fb-4481-ad7f-df59292c91ef"
    doc.space_type = "project"
    doc.space_id = space_id
    doc.created_at = datetime(2026, 3, 8, tzinfo=timezone.utc)
    doc.content = {
        "wp_id": wp_id,
        "title": "Test WP",
        "ws_index": ws_index or [],
        "edition": 0,
    }
    return doc


def _make_ws_doc(ws_id, parent_wp_id="wp_test_001", state="DRAFT", title="Test WS", objective="Objective", procedure=None, verification=None):
    """Create a mock WS document with content as a mutable dict."""
    doc = MagicMock()
    doc.id = f"ws-uuid-{ws_id}"
    doc.content = {
        "ws_id": ws_id,
        "parent_wp_id": parent_wp_id,
        "state": state,
        "order_key": "a0",
        "revision": {"edition": 1},
        "title": title,
        "objective": objective,
        "procedure": procedure or ["Step 1"],
        "verification_criteria": verification or ["Check 1"],
        "scope_in": [],
        "scope_out": [],
        "allowed_paths": [],
        "prohibited_actions": [],
        "governance_pins": {},
    }
    return doc


def _mock_db(wp_doc, ws_docs):
    """Create a mock DB session that returns wp_doc on first query, ws_docs on second.

    The WP stabilize endpoint does:
      1. _resolve_space_id -> query Projects (returns None for no project_id)
      2. _load_wp_document -> query Documents (WP lookup, possibly 2 queries)
      3. query Documents (WS listing)

    We track call order to return the right results.
    """
    db = AsyncMock()
    call_count = {"n": 0}

    async def mock_execute(query):
        call_count["n"] += 1
        result = MagicMock()
        scalars = MagicMock()

        # First call: _resolve_space_id (Project query) — return None
        if call_count["n"] == 1:
            scalars.first.return_value = None
            scalars.all.return_value = []
        # Second call: _load_wp_document (WP by content wp_id)
        elif call_count["n"] == 2:
            scalars.first.return_value = wp_doc
            scalars.all.return_value = [wp_doc] if wp_doc else []
        # Third call: WS listing (all WSs under WP)
        elif call_count["n"] == 3:
            scalars.first.return_value = ws_docs[0] if ws_docs else None
            scalars.all.return_value = ws_docs
        # Fourth+ call: fallback _load_wp_document (display_id fallback)
        else:
            scalars.first.return_value = wp_doc
            scalars.all.return_value = ws_docs

        result.scalars.return_value = scalars
        return result

    db.execute = mock_execute
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.add = MagicMock()
    return db


# ===========================================================================
# Tests
# ===========================================================================

class TestStabilizeWorkPackage:

    @pytest.mark.asyncio
    async def test_happy_path_all_draft_stabilized(self):
        """3 DRAFT WSs -> all become READY, response lists all IDs."""
        wp = _make_wp_doc()
        ws1 = _make_ws_doc("WS-001")
        ws2 = _make_ws_doc("WS-002")
        ws3 = _make_ws_doc("WS-003")
        db = _mock_db(wp, [ws1, ws2, ws3])

        async def override_get_db():
            yield db

        from app.core.database import get_db
        _app.dependency_overrides[get_db] = override_get_db

        try:
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/api/v1/work-binder/wp/wp_test_001/stabilize")
                assert resp.status_code == 200
                body = resp.json()
                assert body["wp_id"] == "wp_test_001"
                assert body["count"] == 3
                assert set(body["stabilized"]) == {"WS-001", "WS-002", "WS-003"}
        finally:
            _app.dependency_overrides = {}

        # Verify doc content was mutated to READY
        assert ws1.content["state"] == "READY"
        assert ws2.content["state"] == "READY"
        assert ws3.content["state"] == "READY"

    @pytest.mark.asyncio
    async def test_mixed_states_only_draft_transitioned(self):
        """2 DRAFT + 1 READY -> only 2 transitioned."""
        wp = _make_wp_doc()
        ws1 = _make_ws_doc("WS-001", state="DRAFT")
        ws2 = _make_ws_doc("WS-002", state="READY")
        ws3 = _make_ws_doc("WS-003", state="DRAFT")
        db = _mock_db(wp, [ws1, ws2, ws3])

        async def override_get_db():
            yield db

        from app.core.database import get_db
        _app.dependency_overrides[get_db] = override_get_db

        try:
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/api/v1/work-binder/wp/wp_test_001/stabilize")
                assert resp.status_code == 200
                body = resp.json()
                assert body["count"] == 2
                assert set(body["stabilized"]) == {"WS-001", "WS-003"}
        finally:
            _app.dependency_overrides = {}

        # READY WS untouched
        assert ws2.content["state"] == "READY"

    @pytest.mark.asyncio
    async def test_validation_failure_blocks_all(self):
        """1 of 3 DRAFT WSs fails validation -> none transitioned (atomicity)."""
        wp = _make_wp_doc()
        ws1 = _make_ws_doc("WS-001")  # valid
        ws2 = _make_ws_doc("WS-002", title="")  # invalid: empty title
        ws3 = _make_ws_doc("WS-003")  # valid
        db = _mock_db(wp, [ws1, ws2, ws3])

        async def override_get_db():
            yield db

        from app.core.database import get_db
        _app.dependency_overrides[get_db] = override_get_db

        try:
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/api/v1/work-binder/wp/wp_test_001/stabilize")
                assert resp.status_code == 400
                body = resp.json()
                assert body["detail"]["error_code"] == "STABILIZATION_FAILED"
                assert "WS-002" in body["detail"]["errors"]
        finally:
            _app.dependency_overrides = {}

        # No docs should have been mutated
        assert ws1.content["state"] == "DRAFT"
        assert ws2.content["state"] == "DRAFT"
        assert ws3.content["state"] == "DRAFT"

    @pytest.mark.asyncio
    async def test_no_draft_ws_returns_400(self):
        """All WSs already READY -> 400."""
        wp = _make_wp_doc()
        ws1 = _make_ws_doc("WS-001", state="READY")
        ws2 = _make_ws_doc("WS-002", state="READY")
        db = _mock_db(wp, [ws1, ws2])

        async def override_get_db():
            yield db

        from app.core.database import get_db
        _app.dependency_overrides[get_db] = override_get_db

        try:
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/api/v1/work-binder/wp/wp_test_001/stabilize")
                assert resp.status_code == 400
                body = resp.json()
                assert body["detail"]["error_code"] == "NO_DRAFT_STATEMENTS"
        finally:
            _app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_empty_wp_no_ws_returns_400(self):
        """WP with zero WSs -> 400."""
        wp = _make_wp_doc()
        db = _mock_db(wp, [])

        async def override_get_db():
            yield db

        from app.core.database import get_db
        _app.dependency_overrides[get_db] = override_get_db

        try:
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/api/v1/work-binder/wp/wp_test_001/stabilize")
                assert resp.status_code == 400
                body = resp.json()
                assert body["detail"]["error_code"] == "NO_DRAFT_STATEMENTS"
        finally:
            _app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_revision_incremented(self):
        """Revision edition is incremented on each stabilized WS."""
        wp = _make_wp_doc()
        ws1 = _make_ws_doc("WS-001")
        ws1.content["revision"] = {"edition": 3}
        db = _mock_db(wp, [ws1])

        async def override_get_db():
            yield db

        from app.core.database import get_db
        _app.dependency_overrides[get_db] = override_get_db

        try:
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/api/v1/work-binder/wp/wp_test_001/stabilize")
                assert resp.status_code == 200
        finally:
            _app.dependency_overrides = {}

        assert ws1.content["revision"]["edition"] == 4
