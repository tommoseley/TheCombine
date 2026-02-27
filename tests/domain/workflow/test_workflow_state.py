"""Tests for workflow state."""


from app.domain.workflow.workflow_state import (
    WorkflowState, WorkflowStatus, IterationProgress, AcceptanceDecision
)
from app.domain.workflow.step_state import StepState


class TestWorkflowStatus:
    """Tests for WorkflowStatus enum."""
    
    def test_all_statuses_defined(self):
        assert WorkflowStatus.PENDING.value == "pending"
        assert WorkflowStatus.RUNNING.value == "running"
        assert WorkflowStatus.WAITING_ACCEPTANCE.value == "waiting_acceptance"
        assert WorkflowStatus.COMPLETED.value == "completed"
        assert WorkflowStatus.FAILED.value == "failed"
        assert WorkflowStatus.CANCELLED.value == "cancelled"


class TestIterationProgress:
    """Tests for IterationProgress."""
    
    def test_is_complete_true(self):
        prog = IterationProgress(step_id="s1", total=3, completed=3, current_index=2)
        assert prog.is_complete is True
    
    def test_is_complete_false(self):
        prog = IterationProgress(step_id="s1", total=3, completed=1, current_index=1)
        assert prog.is_complete is False
    
    def test_remaining(self):
        prog = IterationProgress(step_id="s1", total=5, completed=2, current_index=2)
        assert prog.remaining == 3


class TestAcceptanceDecision:
    """Tests for AcceptanceDecision."""
    
    def test_to_dict(self):
        decision = AcceptanceDecision(
            doc_type="implementation_plan",
            scope_id=None,
            accepted=True,
            comment="Looks good",
            decided_by="user_123",
        )
        data = decision.to_dict()
        assert data["doc_type"] == "implementation_plan"
        assert data["accepted"] is True
        assert data["comment"] == "Looks good"

    def test_from_dict(self):
        data = {
            "doc_type": "implementation_plan",
            "scope_id": "wp_1",
            "accepted": False,
            "comment": "Needs work",
            "decided_by": "user_456",
            "decided_at": "2026-01-03T12:00:00+00:00",
        }
        decision = AcceptanceDecision.from_dict(data)
        assert decision.doc_type == "implementation_plan"
        assert decision.scope_id == "wp_1"
        assert decision.accepted is False


class TestWorkflowState:
    """Tests for WorkflowState."""
    
    def test_initial_state(self):
        state = WorkflowState(workflow_id="wf1", project_id="proj1")
        assert state.status == WorkflowStatus.PENDING
        assert state.current_step_id is None
        assert state.completed_steps == []
    
    def test_start(self):
        state = WorkflowState(workflow_id="wf1", project_id="proj1")
        state.start()
        assert state.status == WorkflowStatus.RUNNING
        assert state.started_at is not None
    
    def test_complete(self):
        state = WorkflowState(workflow_id="wf1", project_id="proj1")
        state.start()
        state.complete()
        assert state.status == WorkflowStatus.COMPLETED
        assert state.completed_at is not None
    
    def test_fail(self):
        state = WorkflowState(workflow_id="wf1", project_id="proj1")
        state.start()
        state.fail("Something went wrong")
        assert state.status == WorkflowStatus.FAILED
        assert state.error == "Something went wrong"
    
    def test_cancel(self):
        state = WorkflowState(workflow_id="wf1", project_id="proj1")
        state.start()
        state.cancel()
        assert state.status == WorkflowStatus.CANCELLED
    
    def test_wait_for_acceptance(self):
        state = WorkflowState(workflow_id="wf1", project_id="proj1")
        state.start()
        state.wait_for_acceptance("implementation_plan", "wp_1")
        assert state.status == WorkflowStatus.WAITING_ACCEPTANCE
        assert state.pending_acceptance == "implementation_plan"
        assert state.pending_acceptance_scope_id == "wp_1"
    
    def test_wait_for_clarification(self):
        state = WorkflowState(workflow_id="wf1", project_id="proj1")
        state.start()
        state.wait_for_clarification("discovery")
        assert state.status == WorkflowStatus.WAITING_CLARIFICATION
        assert state.pending_clarification_step_id == "discovery"
    
    def test_resume(self):
        state = WorkflowState(workflow_id="wf1", project_id="proj1")
        state.wait_for_acceptance("doc", None)
        state.resume()
        assert state.status == WorkflowStatus.RUNNING
        assert state.pending_acceptance is None
    
    def test_mark_step_complete(self):
        state = WorkflowState(workflow_id="wf1", project_id="proj1")
        state.mark_step_complete("step1")
        state.mark_step_complete("step2")
        state.mark_step_complete("step1")  # Duplicate
        assert state.completed_steps == ["step1", "step2"]
    
    def test_is_step_complete(self):
        state = WorkflowState(workflow_id="wf1", project_id="proj1")
        assert state.is_step_complete("step1") is False
        state.mark_step_complete("step1")
        assert state.is_step_complete("step1") is True
    
    def test_step_state_management(self):
        state = WorkflowState(workflow_id="wf1", project_id="proj1")
        step_state = StepState(step_id="step1")
        state.set_step_state("step1", step_state)
        retrieved = state.get_step_state("step1")
        assert retrieved.step_id == "step1"
    
    def test_duration(self):
        state = WorkflowState(workflow_id="wf1", project_id="proj1")
        state.start()
        state.complete()
        assert state.duration is not None
        assert state.duration >= 0
    
    def test_duration_none_if_not_complete(self):
        state = WorkflowState(workflow_id="wf1", project_id="proj1")
        state.start()
        assert state.duration is None
    
    def test_serialization_roundtrip(self):
        state = WorkflowState(workflow_id="wf1", project_id="proj1")
        state.start()
        state.mark_step_complete("step1")
        state.iteration_progress["iter1"] = IterationProgress(
            step_id="iter_step", total=3, completed=1, current_index=1,
            entity_ids=["e1", "e2", "e3"]
        )
        
        data = state.to_dict()
        restored = WorkflowState.from_dict(data)
        
        assert restored.workflow_id == "wf1"
        assert restored.status == WorkflowStatus.RUNNING
        assert "step1" in restored.completed_steps
        assert restored.iteration_progress["iter1"].total == 3
