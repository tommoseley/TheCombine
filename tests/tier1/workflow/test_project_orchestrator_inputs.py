"""Tests for project orchestrator input document assembly.

Verifies that _start_document_production loads required input documents
from the database and passes them to PlanExecutor.start_execution().

Bug: _start_document_production passed initial_context={} to every DCW,
so no LLM step received its required input documents.
"""

import os
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

# ---------------------------------------------------------------------------
# Stub packages whose __init__.py triggers circular imports.
# app.api.__init__ imports routers -> circular through plan_executor
# app.domain.workflow.__init__ imports plan_executor -> circular through routers
# ---------------------------------------------------------------------------
_this_dir = os.path.dirname(__file__)
_root = os.path.join(_this_dir, "..", "..", "..")

if "app.api" not in sys.modules:
    _api_stub = types.ModuleType("app.api")
    _api_stub.__path__ = [os.path.join(_root, "app", "api")]
    _api_stub.__package__ = "app.api"
    sys.modules["app.api"] = _api_stub

if "app.domain.workflow" not in sys.modules:
    _wf_stub = types.ModuleType("app.domain.workflow")
    _wf_stub.__path__ = [os.path.join(_root, "app", "domain", "workflow")]
    _wf_stub.__package__ = "app.domain.workflow"
    sys.modules["app.domain.workflow"] = _wf_stub

# Wire stub into parent so patch() can resolve dotted paths
import app.domain  # noqa: E402
app.domain.workflow = sys.modules["app.domain.workflow"]

from app.domain.workflow.project_orchestrator import (  # noqa: E402
    ProjectOrchestrator,
    OrchestrationState,
    TrackState,
)
from app.domain.workflow.production_state import ProductionState  # noqa: E402

MODULE = "app.domain.workflow.project_orchestrator"


@pytest.fixture
def project_uuid():
    return uuid4()


@pytest.fixture
def mock_db():
    return AsyncMock()


def _make_orchestrator(mock_db, project_uuid, doc_type):
    """Create an orchestrator with minimal state for testing _start_document_production."""
    orch = ProjectOrchestrator(mock_db)
    orch._state = OrchestrationState(
        orchestration_id="orch-test123",
        project_id=str(project_uuid),
        tracks={
            doc_type: TrackState(
                document_type=doc_type,
                state=ProductionState.READY_FOR_PRODUCTION,
            ),
        },
    )
    # Mock _emit_event to avoid importing production router
    orch._emit_event = AsyncMock()
    return orch


def _mock_document(doc_type_id, content):
    """Create a mock Document with the given type and content."""
    doc = MagicMock()
    doc.doc_type_id = doc_type_id
    doc.content = content
    doc.id = uuid4()
    return doc


def _mock_plan(document_type, requires_inputs):
    """Create a mock WorkflowPlan."""
    plan = MagicMock()
    plan.document_type = document_type
    plan.requires_inputs = requires_inputs
    return plan


def _setup_executor_mock():
    """Create mocked PlanExecutor class and instance."""
    mock_instance = AsyncMock()
    mock_instance.start_execution.return_value = MagicMock(execution_id="exec-test123")
    mock_cls = MagicMock(return_value=mock_instance)
    return mock_cls, mock_instance


def _make_mock_modules(mock_executor_cls):
    """Create mock module stubs for local imports in _start_document_production.

    Returns dict suitable for patch.dict(sys.modules, ...).
    """
    pe_mod = types.ModuleType("app.domain.workflow.plan_executor")
    pe_mod.PlanExecutor = mock_executor_cls

    ps_mod = types.ModuleType("app.domain.workflow.pg_state_persistence")
    ps_mod.PgStatePersistence = MagicMock()

    # For nodes subpackage
    nodes_mod = types.ModuleType("app.domain.workflow.nodes")
    nodes_mod.__path__ = [os.path.join(_root, "app", "domain", "workflow", "nodes")]
    nodes_mod.__package__ = "app.domain.workflow.nodes"

    llm_mod = types.ModuleType("app.domain.workflow.nodes.llm_executors")
    llm_mod.create_llm_executors = AsyncMock(return_value={})

    return {
        "app.domain.workflow.plan_executor": pe_mod,
        "app.domain.workflow.pg_state_persistence": ps_mod,
        "app.domain.workflow.nodes": nodes_mod,
        "app.domain.workflow.nodes.llm_executors": llm_mod,
    }


@pytest.mark.asyncio
async def test_start_document_production_loads_input_documents(
    mock_db, project_uuid,
):
    """_start_document_production must load required input documents from DB
    and pass them as initial_context['input_documents'] to start_execution."""
    orch = _make_orchestrator(mock_db, project_uuid, "technical_architecture")

    # Plan requires two input documents (TA requires PD + IP)
    plan = _mock_plan("technical_architecture", ["project_discovery", "implementation_plan"])
    mock_registry = MagicMock()
    mock_registry.get_by_document_type.return_value = plan

    # DB returns a document for each required input
    pd_doc = _mock_document("project_discovery", {"title": "PD content"})
    ip_doc = _mock_document("implementation_plan", {"title": "IP content"})

    pd_result = MagicMock()
    pd_result.scalar_one_or_none.return_value = pd_doc
    ip_result = MagicMock()
    ip_result.scalar_one_or_none.return_value = ip_doc
    mock_db.execute = AsyncMock(side_effect=[pd_result, ip_result])

    mock_executor_cls, mock_executor = _setup_executor_mock()
    mock_mods = _make_mock_modules(mock_executor_cls)

    with (
        patch(f"{MODULE}.get_plan_registry", return_value=mock_registry),
        patch.dict(sys.modules, mock_mods),
    ):
        await orch._start_document_production(str(project_uuid), "technical_architecture")

    # Verify start_execution was called with input documents
    mock_executor.start_execution.assert_called_once()
    call_kwargs = mock_executor.start_execution.call_args.kwargs
    initial_context = call_kwargs["initial_context"]

    assert "input_documents" in initial_context
    assert initial_context["input_documents"]["project_discovery"] == {"title": "PD content"}
    assert initial_context["input_documents"]["implementation_plan"] == {"title": "IP content"}


@pytest.mark.asyncio
async def test_start_document_production_warns_on_missing_input(
    mock_db, project_uuid,
):
    """When a required input document is missing from DB, execution still starts
    and input_documents reflects the missing entry (key absent)."""
    orch = _make_orchestrator(mock_db, project_uuid, "technical_architecture")

    plan = _mock_plan("technical_architecture", ["project_discovery", "implementation_plan"])
    mock_registry = MagicMock()
    mock_registry.get_by_document_type.return_value = plan

    # Only project_discovery exists; implementation_plan is missing
    pd_doc = _mock_document("project_discovery", {"title": "PD content"})

    pd_result = MagicMock()
    pd_result.scalar_one_or_none.return_value = pd_doc
    missing_result = MagicMock()
    missing_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(side_effect=[pd_result, missing_result])

    mock_executor_cls, mock_executor = _setup_executor_mock()
    mock_mods = _make_mock_modules(mock_executor_cls)

    with (
        patch(f"{MODULE}.get_plan_registry", return_value=mock_registry),
        patch.dict(sys.modules, mock_mods),
    ):
        await orch._start_document_production(str(project_uuid), "technical_architecture")

    # Execution must still start (no crash)
    mock_executor.start_execution.assert_called_once()
    call_kwargs = mock_executor.start_execution.call_args.kwargs
    initial_context = call_kwargs["initial_context"]

    # Found input is present, missing input is absent
    assert "input_documents" in initial_context
    assert initial_context["input_documents"]["project_discovery"] == {"title": "PD content"}
    assert "implementation_plan" not in initial_context["input_documents"]


@pytest.mark.asyncio
async def test_start_document_production_no_inputs_required(
    mock_db, project_uuid,
):
    """For a document type with no requires_inputs, initial_context still has
    an empty input_documents dict."""
    orch = _make_orchestrator(mock_db, project_uuid, "concierge_intake")
    orch._state.tracks["concierge_intake"] = TrackState(
        document_type="concierge_intake",
        state=ProductionState.READY_FOR_PRODUCTION,
    )

    plan = _mock_plan("concierge_intake", [])
    mock_registry = MagicMock()
    mock_registry.get_by_document_type.return_value = plan

    mock_executor_cls, mock_executor = _setup_executor_mock()
    mock_mods = _make_mock_modules(mock_executor_cls)

    with (
        patch(f"{MODULE}.get_plan_registry", return_value=mock_registry),
        patch.dict(sys.modules, mock_mods),
    ):
        await orch._start_document_production(str(project_uuid), "concierge_intake")

    mock_executor.start_execution.assert_called_once()
    call_kwargs = mock_executor.start_execution.call_args.kwargs
    initial_context = call_kwargs["initial_context"]

    assert "input_documents" in initial_context
    assert initial_context["input_documents"] == {}
