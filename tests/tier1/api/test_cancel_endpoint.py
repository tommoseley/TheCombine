"""Tests for cancel endpoint on document-workflows router (WS-RING0-002).

POST /api/v1/document-workflows/executions/{id}/cancel should:
- Cancel running executions -> status=cancelled, terminal_outcome=cancelled
- Cancel paused executions -> status=cancelled, terminal_outcome=cancelled
- Reject completed executions -> 409 Conflict
- Reject already-cancelled executions -> 409 Conflict
- Return 404 for non-existent executions

These tests operate at the PlanExecutor level (tier-1, no DB) since the
cancel endpoint delegates to the executor.

Uses importlib bypass to avoid circular import through workflow/__init__.py.
"""

import importlib.util
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

# ---------------------------------------------------------------------------
# Load modules via importlib to bypass circular import chain
# ---------------------------------------------------------------------------

# 1. plan_models (no app imports)
_pm_spec = importlib.util.spec_from_file_location(
    "plan_models_cancel_test",
    "app/domain/workflow/plan_models.py",
)
_pm_mod = importlib.util.module_from_spec(_pm_spec)
_pm_spec.loader.exec_module(_pm_mod)
sys.modules.setdefault("app.domain.workflow.plan_models", _pm_mod)

# 2. document_workflow_state (no app imports)
_dws_spec = importlib.util.spec_from_file_location(
    "document_workflow_state_cancel_test",
    "app/domain/workflow/document_workflow_state.py",
)
_dws_mod = importlib.util.module_from_spec(_dws_spec)
_dws_spec.loader.exec_module(_dws_mod)
sys.modules.setdefault("app.domain.workflow.document_workflow_state", _dws_mod)

DocumentWorkflowState = _dws_mod.DocumentWorkflowState
DocumentWorkflowStatus = _dws_mod.DocumentWorkflowStatus

# 3. edge_router (imports plan_models + document_workflow_state)
_er_spec = importlib.util.spec_from_file_location(
    "edge_router_cancel_test",
    "app/domain/workflow/edge_router.py",
)
_er_mod = importlib.util.module_from_spec(_er_spec)
_er_spec.loader.exec_module(_er_mod)

# 4. plan_executor (needs production mock)
_mock_production = MagicMock()
_mock_production.publish_event = AsyncMock()
sys.modules.setdefault("app.api.v1.routers.production", _mock_production)

_pe_spec = importlib.util.spec_from_file_location(
    "plan_executor_cancel_test",
    "app/domain/workflow/plan_executor.py",
    submodule_search_locations=[],
)
_pe_mod = importlib.util.module_from_spec(_pe_spec)
_pe_spec.loader.exec_module(_pe_mod)

PlanExecutor = _pe_mod.PlanExecutor
PlanExecutorError = _pe_mod.PlanExecutorError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_state(status: DocumentWorkflowStatus, terminal_outcome=None) -> DocumentWorkflowState:
    """Create a minimal state with given status."""
    state = DocumentWorkflowState(
        execution_id="exec-cancel-test",
        workflow_id="test_wf",
        project_id="proj-1",
        document_type="project_discovery",
        current_node_id="generation",
        status=status,
    )
    if terminal_outcome:
        state.terminal_outcome = terminal_outcome
    return state


@pytest.fixture
def executor():
    """Create PlanExecutor with mocked dependencies."""
    pe = PlanExecutor.__new__(PlanExecutor)
    pe._db_session = AsyncMock()
    pe._persistence = AsyncMock()
    pe._ops_service = MagicMock()
    pe._outcome_recorder = None
    pe._thread_manager = None
    pe._executors = {}
    pe._plan_registry = MagicMock()
    pe._emit_station_changed = AsyncMock()
    pe._record_governance_outcome = AsyncMock()
    pe._persist_produced_documents = AsyncMock()
    return pe


# ===================================================================
# Test: Cancel running execution
# ===================================================================

class TestCancelRunningExecution:
    """POST /cancel on a running execution should succeed."""

    @pytest.mark.asyncio
    async def test_cancel_running_sets_cancelled(self, executor):
        """Cancel a running execution -> status=completed, terminal_outcome=cancelled."""
        state = _make_state(DocumentWorkflowStatus.RUNNING)
        executor._persistence.load = AsyncMock(return_value=state)
        executor._persistence.save = AsyncMock()

        result = await executor.cancel_execution("exec-cancel-test")

        assert result.status == DocumentWorkflowStatus.COMPLETED
        assert result.terminal_outcome == "cancelled"


# ===================================================================
# Test: Cancel paused execution
# ===================================================================

class TestCancelPausedExecution:
    """POST /cancel on a paused execution should succeed."""

    @pytest.mark.asyncio
    async def test_cancel_paused_sets_cancelled(self, executor):
        """Cancel a paused execution -> status=completed, terminal_outcome=cancelled."""
        state = _make_state(DocumentWorkflowStatus.PAUSED)
        executor._persistence.load = AsyncMock(return_value=state)
        executor._persistence.save = AsyncMock()

        result = await executor.cancel_execution("exec-cancel-test")

        assert result.status == DocumentWorkflowStatus.COMPLETED
        assert result.terminal_outcome == "cancelled"


# ===================================================================
# Test: Cancel completed execution -> 409
# ===================================================================

class TestCancelCompletedExecution:
    """POST /cancel on a completed execution should fail with conflict."""

    @pytest.mark.asyncio
    async def test_cancel_completed_raises(self, executor):
        """Cancel on completed execution raises PlanExecutorError."""
        state = _make_state(DocumentWorkflowStatus.COMPLETED, terminal_outcome="stabilized")
        executor._persistence.load = AsyncMock(return_value=state)

        with pytest.raises(PlanExecutorError, match="[Cc]annot cancel.*completed"):
            await executor.cancel_execution("exec-cancel-test")


# ===================================================================
# Test: Cancel already cancelled execution -> 409
# ===================================================================

class TestCancelAlreadyCancelledExecution:
    """POST /cancel on an already cancelled execution should fail with conflict."""

    @pytest.mark.asyncio
    async def test_cancel_already_cancelled_raises(self, executor):
        """Cancel on already cancelled execution raises PlanExecutorError."""
        state = _make_state(DocumentWorkflowStatus.COMPLETED, terminal_outcome="cancelled")
        executor._persistence.load = AsyncMock(return_value=state)

        with pytest.raises(PlanExecutorError, match="[Cc]annot cancel.*completed"):
            await executor.cancel_execution("exec-cancel-test")


# ===================================================================
# Test: Cancel non-existent execution -> 404
# ===================================================================

class TestCancelNonExistentExecution:
    """POST /cancel on a non-existent execution should return 404."""

    @pytest.mark.asyncio
    async def test_cancel_not_found_raises(self, executor):
        """Cancel on non-existent execution raises PlanExecutorError."""
        executor._persistence.load = AsyncMock(return_value=None)

        with pytest.raises(PlanExecutorError, match="not found"):
            await executor.cancel_execution("exec-nonexistent")
