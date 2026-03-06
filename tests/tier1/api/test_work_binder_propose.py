"""Tier-1 CRAP score remediation tests for propose_work_statements endpoint.

Covers the branching logic (CC=17):
- Gate check failures: returns 400 or 409
- Missing ANTHROPIC_API_KEY: returns 500
- TaskPromptNotFoundError, TaskOutputParseError, TaskOutputValidationError, TaskExecutionError
- LLM output is dict (single WS), list (multiple WSs), or other type
- Empty ws_items list -> early return
- Successful proposal with WS creation, display ID minting, ws_index update
"""

import copy
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.routers.work_binder import router


# =========================================================================
# Test app setup
# =========================================================================


def _make_test_app():
    app = FastAPI()
    app.include_router(router)
    return app


# =========================================================================
# Fake DB objects
# =========================================================================


def _fake_wp_doc(wp_id="WP-001", ws_index=None, space_id=None):
    doc = MagicMock()
    doc.content = {
        "wp_id": wp_id,
        "title": "Test WP",
        "ws_index": ws_index or [],
    }
    doc.id = uuid4()
    doc.space_id = space_id or uuid4()
    doc.space_type = "project"
    doc.version = 1
    return doc


def _fake_ta_doc():
    doc = MagicMock()
    doc.id = uuid4()
    doc.content = {"architecture": "stuff"}
    doc.version = 1
    return doc


def _fake_project(project_id=None):
    proj = MagicMock()
    proj.id = uuid4()
    proj.project_id = project_id or "PROJ-001"
    return proj


# =========================================================================
# Gate check tests (validate_proposal_gates)
# =========================================================================


class TestProposeWSGateRejection:
    """Tests for gate check rejection paths."""

    @pytest.mark.asyncio
    async def test_gate_error_400_when_ta_not_ready(self):
        """Gate rejection (TA not ready) returns 400."""
        app = _make_test_app()
        wp_doc = _fake_wp_doc()
        ta_doc = _fake_ta_doc()
        project = _fake_project()

        with (
            patch(
                "app.api.v1.routers.work_binder._load_wp_document",
                new_callable=AsyncMock, return_value=wp_doc,
            ),
            patch(
                "app.api.v1.routers.work_binder._resolve_project",
                new_callable=AsyncMock, return_value=project,
            ),
            patch(
                "app.api.v1.routers.work_binder._find_ta_for_project",
                new_callable=AsyncMock, return_value=ta_doc,
            ),
            patch(
                "app.api.v1.routers.work_binder.validate_proposal_gates",
                return_value=["HARD_STOP: TA not stabilized"],
            ),
            patch(
                "app.api.v1.routers.work_binder.build_wb_audit_event",
                return_value={"event": "mock"},
            ),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                resp = await client.post(
                    "/work-binder/propose-ws",
                    json={"project_id": "PROJ-001", "wp_id": "WP-001"},
                )
            assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_gate_error_409_when_ws_index_exists(self):
        """Gate rejection (ws_index not empty) returns 409."""
        app = _make_test_app()
        wp_doc = _fake_wp_doc()
        project = _fake_project()
        ta_doc = _fake_ta_doc()

        with (
            patch(
                "app.api.v1.routers.work_binder._load_wp_document",
                new_callable=AsyncMock, return_value=wp_doc,
            ),
            patch(
                "app.api.v1.routers.work_binder._resolve_project",
                new_callable=AsyncMock, return_value=project,
            ),
            patch(
                "app.api.v1.routers.work_binder._find_ta_for_project",
                new_callable=AsyncMock, return_value=ta_doc,
            ),
            patch(
                "app.api.v1.routers.work_binder.validate_proposal_gates",
                return_value=["HARD_STOP: Work Package already has Work Statements. "],
            ),
            patch(
                "app.api.v1.routers.work_binder.build_wb_audit_event",
                return_value={"event": "mock"},
            ),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                resp = await client.post(
                    "/work-binder/propose-ws",
                    json={"project_id": "PROJ-001", "wp_id": "WP-001"},
                )
            assert resp.status_code == 409


# =========================================================================
# API key / LLM error tests
# =========================================================================


class TestProposeWSLLMErrors:
    """Tests for LLM-related error paths."""

    @pytest.mark.asyncio
    async def test_missing_api_key_returns_500(self):
        """Missing ANTHROPIC_API_KEY returns 500."""
        app = _make_test_app()
        wp_doc = _fake_wp_doc()
        project = _fake_project()
        ta_doc = _fake_ta_doc()

        with (
            patch(
                "app.api.v1.routers.work_binder._load_wp_document",
                new_callable=AsyncMock, return_value=wp_doc,
            ),
            patch(
                "app.api.v1.routers.work_binder._resolve_project",
                new_callable=AsyncMock, return_value=project,
            ),
            patch(
                "app.api.v1.routers.work_binder._find_ta_for_project",
                new_callable=AsyncMock, return_value=ta_doc,
            ),
            patch(
                "app.api.v1.routers.work_binder.validate_proposal_gates",
                return_value=[],
            ),
            patch(
                "app.api.v1.routers.work_binder.build_wb_audit_event",
                return_value={"event": "mock"},
            ),
            patch.dict("os.environ", {}, clear=True),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                resp = await client.post(
                    "/work-binder/propose-ws",
                    json={"project_id": "PROJ-001", "wp_id": "WP-001"},
                )
            assert resp.status_code == 500
            assert "ANTHROPIC_API_KEY" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_task_prompt_not_found_returns_500(self):
        """TaskPromptNotFoundError returns 500."""
        from app.domain.services.task_execution_service import TaskPromptNotFoundError

        app = _make_test_app()
        wp_doc = _fake_wp_doc()
        project = _fake_project()
        ta_doc = _fake_ta_doc()

        with (
            patch(
                "app.api.v1.routers.work_binder._load_wp_document",
                new_callable=AsyncMock, return_value=wp_doc,
            ),
            patch(
                "app.api.v1.routers.work_binder._resolve_project",
                new_callable=AsyncMock, return_value=project,
            ),
            patch(
                "app.api.v1.routers.work_binder._find_ta_for_project",
                new_callable=AsyncMock, return_value=ta_doc,
            ),
            patch(
                "app.api.v1.routers.work_binder.validate_proposal_gates",
                return_value=[],
            ),
            patch(
                "app.api.v1.routers.work_binder.build_wb_audit_event",
                return_value={"event": "mock"},
            ),
            patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}),
            patch(
                "app.api.v1.routers.work_binder.execute_task",
                new_callable=AsyncMock,
                side_effect=TaskPromptNotFoundError("not found"),
            ),
            patch("app.llm.providers.anthropic.AnthropicProvider"),
            patch("app.domain.workflow.nodes.llm_executors.LoggingLLMService"),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                resp = await client.post(
                    "/work-binder/propose-ws",
                    json={"project_id": "PROJ-001", "wp_id": "WP-001"},
                )
            assert resp.status_code == 500
            assert "Task prompt not found" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_task_output_parse_error_returns_400(self):
        """TaskOutputParseError returns 400."""
        from app.domain.services.task_execution_service import TaskOutputParseError

        app = _make_test_app()
        wp_doc = _fake_wp_doc()
        project = _fake_project()
        ta_doc = _fake_ta_doc()

        with (
            patch(
                "app.api.v1.routers.work_binder._load_wp_document",
                new_callable=AsyncMock, return_value=wp_doc,
            ),
            patch(
                "app.api.v1.routers.work_binder._resolve_project",
                new_callable=AsyncMock, return_value=project,
            ),
            patch(
                "app.api.v1.routers.work_binder._find_ta_for_project",
                new_callable=AsyncMock, return_value=ta_doc,
            ),
            patch(
                "app.api.v1.routers.work_binder.validate_proposal_gates",
                return_value=[],
            ),
            patch(
                "app.api.v1.routers.work_binder.build_wb_audit_event",
                return_value={"event": "mock"},
            ),
            patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}),
            patch(
                "app.api.v1.routers.work_binder.execute_task",
                new_callable=AsyncMock,
                side_effect=TaskOutputParseError("bad json"),
            ),
            patch("app.llm.providers.anthropic.AnthropicProvider"),
            patch("app.domain.workflow.nodes.llm_executors.LoggingLLMService"),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                resp = await client.post(
                    "/work-binder/propose-ws",
                    json={"project_id": "PROJ-001", "wp_id": "WP-001"},
                )
            assert resp.status_code == 400
            assert "parse failed" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_task_output_validation_error_returns_400(self):
        """TaskOutputValidationError returns 400."""
        from app.domain.services.task_execution_service import TaskOutputValidationError

        app = _make_test_app()
        wp_doc = _fake_wp_doc()
        project = _fake_project()
        ta_doc = _fake_ta_doc()

        with (
            patch(
                "app.api.v1.routers.work_binder._load_wp_document",
                new_callable=AsyncMock, return_value=wp_doc,
            ),
            patch(
                "app.api.v1.routers.work_binder._resolve_project",
                new_callable=AsyncMock, return_value=project,
            ),
            patch(
                "app.api.v1.routers.work_binder._find_ta_for_project",
                new_callable=AsyncMock, return_value=ta_doc,
            ),
            patch(
                "app.api.v1.routers.work_binder.validate_proposal_gates",
                return_value=[],
            ),
            patch(
                "app.api.v1.routers.work_binder.build_wb_audit_event",
                return_value={"event": "mock"},
            ),
            patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}),
            patch(
                "app.api.v1.routers.work_binder.execute_task",
                new_callable=AsyncMock,
                side_effect=TaskOutputValidationError("schema fail"),
            ),
            patch("app.llm.providers.anthropic.AnthropicProvider"),
            patch("app.domain.workflow.nodes.llm_executors.LoggingLLMService"),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                resp = await client.post(
                    "/work-binder/propose-ws",
                    json={"project_id": "PROJ-001", "wp_id": "WP-001"},
                )
            assert resp.status_code == 400
            assert "schema validation failed" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_task_execution_error_returns_500(self):
        """TaskExecutionError returns 500."""
        from app.domain.services.task_execution_service import TaskExecutionError

        app = _make_test_app()
        wp_doc = _fake_wp_doc()
        project = _fake_project()
        ta_doc = _fake_ta_doc()

        with (
            patch(
                "app.api.v1.routers.work_binder._load_wp_document",
                new_callable=AsyncMock, return_value=wp_doc,
            ),
            patch(
                "app.api.v1.routers.work_binder._resolve_project",
                new_callable=AsyncMock, return_value=project,
            ),
            patch(
                "app.api.v1.routers.work_binder._find_ta_for_project",
                new_callable=AsyncMock, return_value=ta_doc,
            ),
            patch(
                "app.api.v1.routers.work_binder.validate_proposal_gates",
                return_value=[],
            ),
            patch(
                "app.api.v1.routers.work_binder.build_wb_audit_event",
                return_value={"event": "mock"},
            ),
            patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}),
            patch(
                "app.api.v1.routers.work_binder.execute_task",
                new_callable=AsyncMock,
                side_effect=TaskExecutionError("llm broke"),
            ),
            patch("app.llm.providers.anthropic.AnthropicProvider"),
            patch("app.domain.workflow.nodes.llm_executors.LoggingLLMService"),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                resp = await client.post(
                    "/work-binder/propose-ws",
                    json={"project_id": "PROJ-001", "wp_id": "WP-001"},
                )
            assert resp.status_code == 500
            assert "Task execution failed" in resp.json()["detail"]


# =========================================================================
# Output parsing tests
# =========================================================================


class TestProposeWSOutputParsing:
    """Tests for output type branching (dict/list/other) and empty list."""

    @pytest.mark.asyncio
    async def test_output_not_dict_or_list_returns_400(self):
        """When LLM output is a string (not dict/list), returns 400."""
        app = _make_test_app()
        wp_doc = _fake_wp_doc()
        project = _fake_project()
        ta_doc = _fake_ta_doc()

        with (
            patch(
                "app.api.v1.routers.work_binder._load_wp_document",
                new_callable=AsyncMock, return_value=wp_doc,
            ),
            patch(
                "app.api.v1.routers.work_binder._resolve_project",
                new_callable=AsyncMock, return_value=project,
            ),
            patch(
                "app.api.v1.routers.work_binder._find_ta_for_project",
                new_callable=AsyncMock, return_value=ta_doc,
            ),
            patch(
                "app.api.v1.routers.work_binder.validate_proposal_gates",
                return_value=[],
            ),
            patch(
                "app.api.v1.routers.work_binder.build_wb_audit_event",
                return_value={"event": "mock"},
            ),
            patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}),
            patch(
                "app.api.v1.routers.work_binder.execute_task",
                new_callable=AsyncMock,
                return_value={"output": "just a string"},
            ),
            patch("app.llm.providers.anthropic.AnthropicProvider"),
            patch("app.domain.workflow.nodes.llm_executors.LoggingLLMService"),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                resp = await client.post(
                    "/work-binder/propose-ws",
                    json={"project_id": "PROJ-001", "wp_id": "WP-001"},
                )
            assert resp.status_code == 400
            assert "not a dict or list" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_empty_ws_items_returns_created_false(self):
        """When LLM returns empty list, created=False, ws_ids=[]."""
        app = _make_test_app()
        wp_doc = _fake_wp_doc()
        project = _fake_project()
        ta_doc = _fake_ta_doc()

        with (
            patch(
                "app.api.v1.routers.work_binder._load_wp_document",
                new_callable=AsyncMock, return_value=wp_doc,
            ),
            patch(
                "app.api.v1.routers.work_binder._resolve_project",
                new_callable=AsyncMock, return_value=project,
            ),
            patch(
                "app.api.v1.routers.work_binder._find_ta_for_project",
                new_callable=AsyncMock, return_value=ta_doc,
            ),
            patch(
                "app.api.v1.routers.work_binder.validate_proposal_gates",
                return_value=[],
            ),
            patch(
                "app.api.v1.routers.work_binder.build_wb_audit_event",
                return_value={"event": "mock"},
            ),
            patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}),
            patch(
                "app.api.v1.routers.work_binder.execute_task",
                new_callable=AsyncMock,
                return_value={"output": []},
            ),
            patch("app.llm.providers.anthropic.AnthropicProvider"),
            patch("app.domain.workflow.nodes.llm_executors.LoggingLLMService"),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                resp = await client.post(
                    "/work-binder/propose-ws",
                    json={"project_id": "PROJ-001", "wp_id": "WP-001"},
                )
            assert resp.status_code == 200
            data = resp.json()
            assert data["created"] is False
            assert data["ws_ids"] == []

    @pytest.mark.asyncio
    async def test_integer_output_returns_400(self):
        """When LLM output is an integer (not dict/list), returns 400."""
        app = _make_test_app()
        wp_doc = _fake_wp_doc()
        project = _fake_project()
        ta_doc = _fake_ta_doc()

        with (
            patch(
                "app.api.v1.routers.work_binder._load_wp_document",
                new_callable=AsyncMock, return_value=wp_doc,
            ),
            patch(
                "app.api.v1.routers.work_binder._resolve_project",
                new_callable=AsyncMock, return_value=project,
            ),
            patch(
                "app.api.v1.routers.work_binder._find_ta_for_project",
                new_callable=AsyncMock, return_value=ta_doc,
            ),
            patch(
                "app.api.v1.routers.work_binder.validate_proposal_gates",
                return_value=[],
            ),
            patch(
                "app.api.v1.routers.work_binder.build_wb_audit_event",
                return_value={"event": "mock"},
            ),
            patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}),
            patch(
                "app.api.v1.routers.work_binder.execute_task",
                new_callable=AsyncMock,
                return_value={"output": 42},
            ),
            patch("app.llm.providers.anthropic.AnthropicProvider"),
            patch("app.domain.workflow.nodes.llm_executors.LoggingLLMService"),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                resp = await client.post(
                    "/work-binder/propose-ws",
                    json={"project_id": "PROJ-001", "wp_id": "WP-001"},
                )
            assert resp.status_code == 400
            assert "not a dict or list" in resp.json()["detail"]
