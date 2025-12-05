# tests/test_orchestrator.py

"""Tests for Orchestrator."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from workforce.orchestrator import Orchestrator
from workforce.state import PipelineState
from workforce.schemas.artifacts import Epic, QAResult
from workforce.utils.errors import InvalidStateTransitionError


@pytest.fixture
def orchestrator():
    """Create Orchestrator instance for testing."""
    # Mock canon manager to avoid file I/O
    mock_canon_manager = Mock()
    mock_canon_manager.buffer_manager.register_pipeline_reference = Mock(return_value=Mock(version="1.0", state="ACTIVE"))
    mock_canon_manager.buffer_manager.unregister_pipeline_reference = Mock()
    mock_canon_manager.buffer_manager._pipeline_refs = {}  # Empty dict for in-flight tracking
    mock_canon_manager.version_changed = Mock(return_value=False)
    mock_canon_manager.reload_canon_with_buffer_swap = Mock()
    mock_canon_manager.version_store.get_current_version = Mock(return_value=Mock(__str__=lambda self: "1.0"))
    
    orch = Orchestrator(canon_manager=mock_canon_manager)
    return orch


def test_initial_state(orchestrator):
    """Test Orchestrator starts in IDLE state."""
    assert orchestrator.state == PipelineState.IDLE


def test_state_transition_valid(orchestrator):
    """Test valid state transition."""
    orchestrator._transition_to(PipelineState.PM_PHASE)
    assert orchestrator.state == PipelineState.PM_PHASE


def test_state_transition_invalid(orchestrator):
    """Test invalid state transition raises error."""
    with pytest.raises(InvalidStateTransitionError):
        orchestrator._transition_to(PipelineState.COMMIT_PHASE)


def test_state_transition_logged(orchestrator):
    """Test state transitions are logged."""
    orchestrator._transition_to(PipelineState.PM_PHASE)
    assert len(orchestrator.phase_history) == 1
    assert orchestrator.phase_history[0].to_state == PipelineState.PM_PHASE


def test_generate_pipeline_id(orchestrator, sample_epic):
    """Test pipeline ID generation."""
    id1 = orchestrator._generate_pipeline_id(sample_epic)
    id2 = orchestrator._generate_pipeline_id(sample_epic)
    
    assert id1 != id2
    assert sample_epic.epic_id in id1


def test_pipeline_acquires_buffer_reference(orchestrator, sample_epic):
    """Test pipeline acquires buffer reference at start."""
    with patch.object(orchestrator, '_execute_phases', return_value=Mock(success=True)):
        orchestrator.execute_pipeline(sample_epic)
    
    # Verify register was called
    orchestrator.canon_manager.buffer_manager.register_pipeline_reference.assert_called()


def test_pipeline_releases_buffer_reference(orchestrator, sample_epic):
    """Test pipeline releases buffer reference at end."""
    with patch.object(orchestrator, '_execute_phases', return_value=Mock(success=True)):
        orchestrator.execute_pipeline(sample_epic)
    
    # Verify unregister was called
    orchestrator.canon_manager.buffer_manager.unregister_pipeline_reference.assert_called()


def test_pipeline_releases_buffer_on_exception(orchestrator, sample_epic):
    """Test pipeline releases buffer even on exception."""
    with patch.object(orchestrator, '_execute_phases', side_effect=Exception("Test error")):
        result = orchestrator.execute_pipeline(sample_epic)
    
    assert result.success is False
    # Verify unregister was still called
    orchestrator.canon_manager.buffer_manager.unregister_pipeline_reference.assert_called()


def test_reset_clears_state(orchestrator):
    """Test /reset clears ephemeral state."""
    orchestrator.current_epic = Mock()
    orchestrator.artifacts = {'test': 'data'}
    orchestrator.phase_history = [Mock()]
    
    orchestrator.ALLOW_RESET_IN_CRITICAL_PHASES = True
    result = orchestrator.handle_reset()
    
    assert result.success is True
    assert orchestrator.current_epic is None
    assert len(orchestrator.artifacts) == 0
    assert len(orchestrator.phase_history) == 0


def test_reset_blocked_in_critical_phase(orchestrator):
    """Test /reset blocked during QA phase in production."""
    orchestrator.ALLOW_RESET_IN_CRITICAL_PHASES = False
    orchestrator.state = PipelineState.QA_PHASE
    
    result = orchestrator.handle_reset()
    
    assert result.success is False
    assert "blocked" in result.reason.lower()


def test_reset_allowed_in_dev_mode(orchestrator):
    """Test /reset allowed in all phases in dev mode."""
    orchestrator.ALLOW_RESET_IN_CRITICAL_PHASES = True
    orchestrator.state = PipelineState.COMMIT_PHASE
    
    result = orchestrator.handle_reset()
    
    assert result.success is True
    assert orchestrator.state == PipelineState.IDLE


def test_reset_warns_about_in_flight(orchestrator):
    """Test /reset warns about in-flight pipelines."""
    orchestrator.ALLOW_RESET_IN_CRITICAL_PHASES = True
    orchestrator.canon_manager.buffer_manager._pipeline_refs = {'p1': Mock()}
    
    result = orchestrator.handle_reset()
    
    assert result.in_flight_discarded == 1
    assert len(result.warnings) > 0


def test_qa_loop_bounded_attempts(orchestrator, sample_epic):
    """Test QA rejection loop is bounded."""
    # TODO: Implement when mentor invocation is available
    pass


def test_version_check_before_pipeline(orchestrator, sample_epic):
    """Test version check performed before pipeline execution."""
    with patch.object(orchestrator, '_execute_phases', return_value=Mock(success=True)):
        orchestrator.execute_pipeline(sample_epic)
    
    # Verify version check was called
    orchestrator.canon_manager.version_changed.assert_called()