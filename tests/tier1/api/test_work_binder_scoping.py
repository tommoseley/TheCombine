"""Tests for cross-project scoping in Work Binder endpoints.

Bug: _load_wp_document, _load_ws_document, and list_work_statements
query by content fields (wp_id, ws_id, parent_wp_id) without scoping
by space_id. This causes documents from other projects to leak when
display-ids like "WP-001" repeat across projects.

Fix: All helpers accept optional space_id kwarg. All endpoints accept
optional project_id query param which resolves to space_id.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID

from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient

from app.api.v1.routers.work_binder import (
    router,
    _load_wp_document,
    _load_ws_document,
    _resolve_space_id,
)


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

PROJECT_A_SPACE_ID = str(uuid4())
PROJECT_B_SPACE_ID = str(uuid4())


def _mock_wp_document(space_id, wp_id="WP-001"):
    """Create a mock WP document for a specific project."""
    from datetime import datetime, timezone
    doc = MagicMock()
    doc.id = str(uuid4())
    doc.space_type = "project"
    doc.space_id = space_id
    doc.created_at = datetime(2026, 3, 6, tzinfo=timezone.utc)
    doc.doc_type_id = "work_package"
    doc.content = {
        "wp_id": wp_id,
        "title": f"WP in {space_id[:8]}",
        "ws_index": [
            {"ws_id": "WS-001", "order_key": "a0"},
            {"ws_id": "WS-002", "order_key": "a1"},
        ],
        "edition": 1,
    }
    return doc


def _mock_ws_document(space_id, ws_id, parent_wp_id="WP-001"):
    """Create a mock WS document for a specific project."""
    doc = MagicMock()
    doc.id = str(uuid4())
    doc.space_type = "project"
    doc.space_id = space_id
    doc.doc_type_id = "work_statement"
    doc.content = {
        "ws_id": ws_id,
        "parent_wp_id": parent_wp_id,
        "title": f"{ws_id} in {space_id[:8]}",
        "state": "DRAFT",
        "order_key": "a0",
        "revision": {"edition": 1},
        "objective": "Test",
        "scope_in": [],
        "scope_out": [],
        "allowed_paths": [],
        "procedure": ["Step 1"],
        "verification_criteria": ["Check A"],
        "prohibited_actions": [],
        "governance_pins": {},
    }
    return doc


def _mock_project(space_id):
    """Create a mock Project with given space_id as its UUID."""
    project = MagicMock()
    project.id = UUID(space_id)
    project.project_id = f"PROJ-{space_id[:4]}"
    project.deleted_at = None
    return project


def _mock_db_for_cross_project_test():
    """Create a mock DB that returns WP from project A and WSs from project B.

    First execute call -> load WP (returns project A's WP-001)
    Second execute call -> load WSs (returns project B's WSs with matching parent_wp_id)

    After fix: second call should also filter by space_id, returning no WSs
    since project A has no WSs of its own.
    """
    db = AsyncMock()

    wp_doc = _mock_wp_document(PROJECT_A_SPACE_ID)

    # WSs belong to project B, but parent_wp_id="WP-001" matches
    ws_b1 = _mock_ws_document(PROJECT_B_SPACE_ID, "WS-001")
    ws_b2 = _mock_ws_document(PROJECT_B_SPACE_ID, "WS-002")

    call_count = 0

    async def mock_execute(query):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        scalars = MagicMock()

        if call_count == 1:
            # First query: _load_wp_document
            scalars.first.return_value = wp_doc
        else:
            # Second query: list WSs
            # Check if the query includes space_id filtering
            # by inspecting the uncompiled query string representation
            query_str = str(query)

            if "documents.space_id =" in query_str:
                # Query is scoped by project A's space_id
                # Project A has no WSs -> return empty
                scalars.all.return_value = []
            else:
                # Query is NOT scoped -> returns all matching WSs (cross-project leak)
                scalars.all.return_value = [ws_b1, ws_b2]

        result.scalars.return_value = scalars
        return result

    db.execute = mock_execute
    db.commit = AsyncMock()
    db.add = MagicMock()
    return db


def _mock_db_for_same_project_test():
    """Create a mock DB where WP and WSs are in the same project.

    First execute call -> load WP (returns project A's WP-001)
    Second execute call -> load WSs (returns project A's WSs)

    This should work both before and after the fix.
    """
    db = AsyncMock()

    wp_doc = _mock_wp_document(PROJECT_A_SPACE_ID)

    # WSs belong to project A (same project as WP)
    ws_a1 = _mock_ws_document(PROJECT_A_SPACE_ID, "WS-001")
    ws_a2 = _mock_ws_document(PROJECT_A_SPACE_ID, "WS-002")

    call_count = 0

    async def mock_execute(query):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        scalars = MagicMock()

        if call_count == 1:
            scalars.first.return_value = wp_doc
        else:
            # Same-project WSs always returned
            scalars.all.return_value = [ws_a1, ws_a2]

        result.scalars.return_value = scalars
        return result

    db.execute = mock_execute
    db.commit = AsyncMock()
    db.add = MagicMock()
    return db


# ===========================================================================
# Unit tests: _load_wp_document space_id scoping
# ===========================================================================


class TestLoadWPDocumentScoping:
    """_load_wp_document query must include space_id when provided."""

    @pytest.mark.asyncio
    async def test_query_includes_space_id_when_provided(self):
        """When space_id kwarg is set, the WHERE clause must filter by it."""
        wp_doc = _mock_wp_document(PROJECT_A_SPACE_ID)
        db = AsyncMock()
        captured_queries = []

        async def mock_execute(query):
            captured_queries.append(str(query))
            result = MagicMock()
            scalars = MagicMock()
            scalars.first.return_value = wp_doc
            result.scalars.return_value = scalars
            return result

        db.execute = mock_execute

        await _load_wp_document(db, "WP-001", space_id=PROJECT_A_SPACE_ID)

        assert len(captured_queries) == 1
        assert "documents.space_id =" in captured_queries[0], (
            "Query must include space_id filter when space_id kwarg is provided"
        )

    @pytest.mark.asyncio
    async def test_query_omits_space_id_when_none(self):
        """When space_id is None (default), no space_id filter in WHERE."""
        wp_doc = _mock_wp_document(PROJECT_A_SPACE_ID)
        db = AsyncMock()
        captured_queries = []

        async def mock_execute(query):
            captured_queries.append(str(query))
            result = MagicMock()
            scalars = MagicMock()
            scalars.first.return_value = wp_doc
            result.scalars.return_value = scalars
            return result

        db.execute = mock_execute

        await _load_wp_document(db, "WP-001")

        assert len(captured_queries) == 1
        # SELECT contains documents.space_id, but WHERE should NOT have "documents.space_id ="
        where_clause = captured_queries[0].split("WHERE")[1] if "WHERE" in captured_queries[0] else ""
        assert "documents.space_id =" not in where_clause, (
            "Query must NOT include space_id filter when space_id kwarg is None"
        )

    @pytest.mark.asyncio
    async def test_404_when_wp_not_found_with_space_id(self):
        """When scoped by space_id and WP doesn't exist in that project, 404."""
        db = AsyncMock()

        async def mock_execute(query):
            result = MagicMock()
            scalars = MagicMock()
            scalars.first.return_value = None  # Not found
            result.scalars.return_value = scalars
            return result

        db.execute = mock_execute

        with pytest.raises(HTTPException) as exc_info:
            await _load_wp_document(db, "WP-001", space_id=PROJECT_A_SPACE_ID)
        assert exc_info.value.status_code == 404


# ===========================================================================
# Unit tests: _load_ws_document space_id scoping
# ===========================================================================


class TestLoadWSDocumentScoping:
    """_load_ws_document query must include space_id when provided."""

    @pytest.mark.asyncio
    async def test_query_includes_space_id_when_provided(self):
        """When space_id kwarg is set, the WHERE clause must filter by it."""
        ws_doc = _mock_ws_document(PROJECT_A_SPACE_ID, "WS-001")
        db = AsyncMock()
        captured_queries = []

        async def mock_execute(query):
            captured_queries.append(str(query))
            result = MagicMock()
            scalars = MagicMock()
            scalars.first.return_value = ws_doc
            result.scalars.return_value = scalars
            return result

        db.execute = mock_execute

        await _load_ws_document(db, "WS-001", space_id=PROJECT_A_SPACE_ID)

        assert len(captured_queries) == 1
        assert "documents.space_id =" in captured_queries[0], (
            "Query must include space_id filter when space_id kwarg is provided"
        )

    @pytest.mark.asyncio
    async def test_query_omits_space_id_when_none(self):
        """When space_id is None (default), no space_id filter in WHERE."""
        ws_doc = _mock_ws_document(PROJECT_A_SPACE_ID, "WS-001")
        db = AsyncMock()
        captured_queries = []

        async def mock_execute(query):
            captured_queries.append(str(query))
            result = MagicMock()
            scalars = MagicMock()
            scalars.first.return_value = ws_doc
            result.scalars.return_value = scalars
            return result

        db.execute = mock_execute

        await _load_ws_document(db, "WS-001")

        assert len(captured_queries) == 1
        where_clause = captured_queries[0].split("WHERE")[1] if "WHERE" in captured_queries[0] else ""
        assert "documents.space_id =" not in where_clause, (
            "Query must NOT include space_id filter when space_id kwarg is None"
        )


# ===========================================================================
# Unit tests: _resolve_space_id
# ===========================================================================


class TestResolveSpaceId:
    """_resolve_space_id converts optional project_id to space_id string."""

    @pytest.mark.asyncio
    async def test_returns_none_when_project_id_is_none(self):
        db = AsyncMock()
        result = await _resolve_space_id(db, None)
        assert result is None
        # Should not query DB
        db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_space_id_for_valid_project(self):
        project = _mock_project(PROJECT_A_SPACE_ID)
        db = AsyncMock()

        async def mock_execute(query):
            result = MagicMock()
            result.scalar_one_or_none.return_value = project
            return result

        db.execute = mock_execute

        result = await _resolve_space_id(db, PROJECT_A_SPACE_ID)
        assert result == PROJECT_A_SPACE_ID


# ===========================================================================
# Integration tests: cross-project WS leakage via list endpoint
# ===========================================================================


class TestListWSCrossProjectScoping:
    """list_work_statements must only return WSs from the same project as the WP."""

    @pytest.mark.asyncio
    async def test_cross_project_ws_excluded(self):
        """WSs from project B must NOT appear under project A's WP-001.

        Bug: Without space_id scoping, WS-001 and WS-002 from project B
        leak into project A's Work Binder because they share parent_wp_id.
        """
        db = _mock_db_for_cross_project_test()

        async def override_get_db():
            yield db

        from app.core.database import get_db
        _app.dependency_overrides[get_db] = override_get_db

        try:
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/work-binder/wp/WP-001/work-statements")
                assert resp.status_code == 200
                body = resp.json()
                assert body["total"] == 0, (
                    f"Expected 0 WSs (project A has none), but got {body['total']}. "
                    f"Cross-project WS leakage detected."
                )
        finally:
            _app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_same_project_ws_included(self):
        """WSs from the same project as the WP should be returned normally."""
        db = _mock_db_for_same_project_test()

        async def override_get_db():
            yield db

        from app.core.database import get_db
        _app.dependency_overrides[get_db] = override_get_db

        try:
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/work-binder/wp/WP-001/work-statements")
                assert resp.status_code == 200
                body = resp.json()
                assert body["total"] == 2, (
                    f"Expected 2 WSs from same project, got {body['total']}"
                )
        finally:
            _app.dependency_overrides = {}


# ===========================================================================
# Integration tests: project_id query param scoping
# ===========================================================================


class TestProjectIdQueryParamScoping:
    """Endpoints accept project_id query param to scope document lookups."""

    @pytest.mark.asyncio
    async def test_get_wp_detail_with_project_id_scopes_query(self):
        """GET /wp/{wp_id}?project_id=X must scope the WP lookup."""
        project = _mock_project(PROJECT_A_SPACE_ID)
        wp_doc = _mock_wp_document(PROJECT_A_SPACE_ID)
        db = AsyncMock()
        captured_queries = []

        async def mock_execute(query):
            query_str = str(query)
            captured_queries.append(query_str)
            result = MagicMock()
            # Project table query vs document table query
            if "FROM projects" in query_str:
                result.scalar_one_or_none.return_value = project
            else:
                scalars = MagicMock()
                scalars.first.return_value = wp_doc
                result.scalars.return_value = scalars
            return result

        db.execute = mock_execute

        async def override_get_db():
            yield db

        from app.core.database import get_db
        _app.dependency_overrides[get_db] = override_get_db

        try:
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(
                    f"/api/v1/work-binder/wp/WP-001?project_id={PROJECT_A_SPACE_ID}"
                )
                assert resp.status_code == 200

                # Verify the document query included space_id in WHERE clause
                doc_queries = [q for q in captured_queries if "FROM documents" in q]
                assert len(doc_queries) >= 1
                assert "documents.space_id =" in doc_queries[0], (
                    "WP document query must include space_id filter when project_id is provided"
                )
        finally:
            _app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_get_wp_detail_without_project_id_no_scoping(self):
        """GET /wp/{wp_id} without project_id still works (backward compat)."""
        wp_doc = _mock_wp_document(PROJECT_A_SPACE_ID)
        db = AsyncMock()

        async def mock_execute(query):
            result = MagicMock()
            scalars = MagicMock()
            scalars.first.return_value = wp_doc
            result.scalars.return_value = scalars
            return result

        db.execute = mock_execute

        async def override_get_db():
            yield db

        from app.core.database import get_db
        _app.dependency_overrides[get_db] = override_get_db

        try:
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/work-binder/wp/WP-001")
                assert resp.status_code == 200
                body = resp.json()
                assert body["wp_id"] == "WP-001"
        finally:
            _app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_get_ws_with_project_id_scopes_query(self):
        """GET /work-statements/{ws_id}?project_id=X must scope the WS lookup."""
        project = _mock_project(PROJECT_A_SPACE_ID)
        ws_doc = _mock_ws_document(PROJECT_A_SPACE_ID, "WS-001")
        db = AsyncMock()
        captured_queries = []

        async def mock_execute(query):
            query_str = str(query)
            captured_queries.append(query_str)
            result = MagicMock()
            if "FROM projects" in query_str:
                result.scalar_one_or_none.return_value = project
            else:
                scalars = MagicMock()
                scalars.first.return_value = ws_doc
                result.scalars.return_value = scalars
            return result

        db.execute = mock_execute

        async def override_get_db():
            yield db

        from app.core.database import get_db
        _app.dependency_overrides[get_db] = override_get_db

        try:
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(
                    f"/api/v1/work-binder/work-statements/WS-001?project_id={PROJECT_A_SPACE_ID}"
                )
                assert resp.status_code == 200

                doc_queries = [q for q in captured_queries if "FROM documents" in q]
                assert len(doc_queries) >= 1
                assert "documents.space_id =" in doc_queries[0], (
                    "WS document query must include space_id filter when project_id is provided"
                )
        finally:
            _app.dependency_overrides = {}
