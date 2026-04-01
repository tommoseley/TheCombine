"""Tier-1 tests for ADR-067 timeline/restore/archive endpoints.

Tests router endpoints with mocked DB via FastAPI dependency overrides.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.routers.rewind import router
from app.core.database import get_db


def _make_test_app(db_mock):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db_mock
    return app


def _fake_project():
    p = MagicMock()
    p.id = uuid4()
    p.project_id = "PROJ-001"
    p.deleted_at = None
    return p


def _fake_document(doc_type="project_discovery", display_id="PD-001", version=1,
                    is_latest=True, is_stale=False, status="active"):
    d = MagicMock()
    d.id = uuid4()
    d.doc_type_id = doc_type
    d.display_id = display_id
    d.version = version
    d.title = f"{display_id} v{version}"
    d.is_latest = is_latest
    d.is_stale = is_stale
    d.status = status
    d.lifecycle_state = "complete"
    d.created_at = datetime.now(timezone.utc)
    d.parent_document_id = None
    return d


def _fake_event(event_type="rewind", stage="IP"):
    e = MagicMock()
    e.id = uuid4()
    e.event_type = event_type
    e.rewind_to_stage = stage
    e.reason = "test rewind"
    e.actor = "user"
    e.affected_document_ids = []
    e.created_at = datetime.now(timezone.utc)
    return e


class TestGetProjectTimeline:
    @pytest.mark.asyncio
    async def test_returns_timeline_with_docs_and_events(self):
        project = _fake_project()
        doc = _fake_document()
        event = _fake_event()

        mock_db = AsyncMock()
        doc_result = MagicMock()
        doc_result.scalars.return_value.all.return_value = [doc]
        event_result = MagicMock()
        event_result.scalars.return_value.all.return_value = [event]
        mock_db.execute = AsyncMock(side_effect=[doc_result, event_result])

        app = _make_test_app(mock_db)

        with patch(
            "app.api.v1.dependencies.resolve_project",
            new_callable=AsyncMock, return_value=project,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test",
            ) as client:
                resp = await client.get(f"/projects/{project.id}/timeline")

        assert resp.status_code == 200
        data = resp.json()
        assert data["entry_count"] == 2
        assert len(data["timeline"]) == 2
        assert "active_document_ids" in data
        types = {e["type"] for e in data["timeline"]}
        assert types == {"document", "event"}

    @pytest.mark.asyncio
    async def test_excludes_archived_docs(self):
        """Archived documents should not appear in timeline."""
        project = _fake_project()
        active_doc = _fake_document(status="active")
        archived_doc = _fake_document(status="archived", display_id="PD-002")

        mock_db = AsyncMock()
        # The query filters status != 'archived', so only active_doc should be returned
        doc_result = MagicMock()
        doc_result.scalars.return_value.all.return_value = [active_doc]
        event_result = MagicMock()
        event_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(side_effect=[doc_result, event_result])

        app = _make_test_app(mock_db)

        with patch(
            "app.api.v1.dependencies.resolve_project",
            new_callable=AsyncMock, return_value=project,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test",
            ) as client:
                resp = await client.get(f"/projects/{project.id}/timeline")

        assert resp.status_code == 200
        assert resp.json()["entry_count"] == 1


class TestRestoreCheckpoint:
    @pytest.mark.asyncio
    async def test_404_for_missing_checkpoint(self):
        project = _fake_project()
        mock_db = AsyncMock()
        app = _make_test_app(mock_db)

        with (
            patch("app.api.v1.dependencies.resolve_project",
                  new_callable=AsyncMock, return_value=project),
            patch("app.domain.services.lineage_path_service.compute_lineage_path_from_db",
                  new_callable=AsyncMock, return_value=None),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test",
            ) as client:
                resp = await client.post(
                    f"/projects/{project.id}/restore",
                    json={"checkpoint_id": str(uuid4()), "reason": "test"},
                )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_400_for_invalid_checkpoint_id(self):
        project = _fake_project()
        mock_db = AsyncMock()
        app = _make_test_app(mock_db)

        with patch(
            "app.api.v1.dependencies.resolve_project",
            new_callable=AsyncMock, return_value=project,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test",
            ) as client:
                resp = await client.post(
                    f"/projects/{project.id}/restore",
                    json={"checkpoint_id": "not-a-uuid", "reason": "test"},
                )
        assert resp.status_code == 400


    @pytest.mark.asyncio
    async def test_happy_path_demotes_current_promotes_path(self):
        """Restore demotes all current docs not in path and promotes path docs."""
        project = _fake_project()
        checkpoint_id = uuid4()
        current_doc = _fake_document(is_latest=True, display_id="PD-001", version=2)
        old_doc = _fake_document(is_latest=False, display_id="PD-001", version=1)
        old_doc.id = checkpoint_id

        from app.domain.services.lineage_path_service import LineagePath, PathDocument
        path = LineagePath(
            checkpoint_id=checkpoint_id,
            checkpoint_doc_type="project_discovery",
            checkpoint_version=1,
            documents=[PathDocument(
                id=checkpoint_id, doc_type_id="project_discovery",
                display_id="PD-001", version=1, title="PD-001 v1",
                is_latest=False, is_stale=False, lifecycle_state="complete",
                created_at=datetime.now(timezone.utc),
            )],
        )

        mock_db = AsyncMock()

        # First execute: current docs for preview (returns current_doc)
        preview_result = MagicMock()
        preview_result.scalars.return_value.all.return_value = [current_doc]

        # Second execute: re-query for demotion (returns current_doc again)
        demote_result = MagicMock()
        demote_result.scalars.return_value.all.return_value = [current_doc]

        # Third execute: promote path doc (returns old_doc)
        promote_result = MagicMock()
        promote_result.scalar_one_or_none.return_value = old_doc

        mock_db.execute = AsyncMock(side_effect=[
            preview_result, demote_result, promote_result,
        ])
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        app = _make_test_app(mock_db)

        with (
            patch("app.api.v1.dependencies.resolve_project",
                  new_callable=AsyncMock, return_value=project),
            patch("app.domain.services.lineage_path_service.compute_lineage_path_from_db",
                  new_callable=AsyncMock, return_value=path),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test",
            ) as client:
                resp = await client.post(
                    f"/projects/{project.id}/restore",
                    json={"checkpoint_id": str(checkpoint_id), "reason": "test restore"},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "restored"
        assert data["activated"] >= 1
        assert data["demoted"] >= 1
        # Verify demotion happened on current_doc
        assert current_doc.is_latest is False
        assert current_doc.is_stale is True
        # Verify promotion happened on old_doc
        assert old_doc.is_latest is True
        assert old_doc.is_stale is False
        # Verify lineage event was recorded
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()


class TestArchiveThread:
    @pytest.mark.asyncio
    async def test_404_for_missing_event(self):
        project = _fake_project()
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result)
        app = _make_test_app(mock_db)

        with patch(
            "app.api.v1.dependencies.resolve_project",
            new_callable=AsyncMock, return_value=project,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test",
            ) as client:
                resp = await client.post(
                    f"/projects/{project.id}/archive-thread",
                    json={"event_id": str(uuid4()), "reason": "cleanup"},
                )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_400_for_invalid_event_id(self):
        project = _fake_project()
        mock_db = AsyncMock()
        app = _make_test_app(mock_db)

        with patch(
            "app.api.v1.dependencies.resolve_project",
            new_callable=AsyncMock, return_value=project,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test",
            ) as client:
                resp = await client.post(
                    f"/projects/{project.id}/archive-thread",
                    json={"event_id": "not-a-uuid", "reason": "cleanup"},
                )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_happy_path_archives_thread_docs(self):
        """Archive marks thread documents as archived and records event."""
        project = _fake_project()
        root_event = _fake_event()
        affected_id = uuid4()
        root_event.affected_document_ids = [str(affected_id)]
        thread_doc = _fake_document(is_latest=False, is_stale=True)
        thread_doc.parent_document_id = affected_id
        thread_doc.created_at = datetime(2026, 3, 28, 12, 0, tzinfo=timezone.utc)
        root_event.created_at = datetime(2026, 3, 28, 11, 0, tzinfo=timezone.utc)

        mock_db = AsyncMock()
        event_result = MagicMock()
        event_result.scalar_one_or_none.return_value = root_event
        all_docs_result = MagicMock()
        all_docs_result.scalars.return_value.all.return_value = [thread_doc]
        mock_db.execute = AsyncMock(side_effect=[event_result, all_docs_result])
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        app = _make_test_app(mock_db)

        with patch(
            "app.api.v1.dependencies.resolve_project",
            new_callable=AsyncMock, return_value=project,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test",
            ) as client:
                resp = await client.post(
                    f"/projects/{project.id}/archive-thread",
                    json={"event_id": str(root_event.id), "reason": "cleanup"},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "archived"
        assert data["documents_archived"] == 1
        assert thread_doc.status == "archived"
        assert thread_doc.is_latest is False
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
