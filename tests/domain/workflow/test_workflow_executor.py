"""Tests for workflow executor."""

import pytest
from typing import Dict, Any

from app.domain.workflow.workflow_executor import WorkflowExecutor, WorkflowExecutionResult
from app.domain.workflow.workflow_state import WorkflowState, WorkflowStatus, AcceptanceDecision
from app.domain.workflow.context import WorkflowContext
from app.domain.workflow.step_executor import StepExecutor, ExecutionResult
from app.domain.workflow.step_state import StepState, StepStatus
from app.domain.workflow.gates.clarification import ClarificationGate
from app.domain.workflow.gates.qa import QAGate
from app.domain.workflow.models import (
    Workflow, WorkflowStep, ScopeConfig, DocumentTypeConfig,
    EntityTypeConfig, IterationConfig
)


class MockLLMService:
    """Mock LLM service for testing."""
    
    def __init__(self, responses: Dict[str, str]):
        self._responses = responses
        self._call_count = 0
    
    async def complete(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        self._call_count += 1
        if str(self._call_count) in self._responses:
            return self._responses[str(self._call_count)]
        return self._responses.get("default", '{"result": "ok"}')


class MockPromptLoader:
    """Mock prompt loader that returns dummy prompts."""
    
    def load_role(self, role_name: str) -> str:
        return f"You are a {role_name}."
    
    def load_task(self, task_name: str) -> str:
        return f"Perform task: {task_name}. Return valid JSON."
    
    def role_exists(self, role_name: str) -> bool:
        return True
    
    def task_exists(self, task_name: str) -> bool:
        return True


@pytest.fixture
def simple_workflow():
    """Create a simple workflow with 2 steps."""
    return Workflow(
        schema_version="workflow.v1",
        workflow_id="test_wf",
        revision="1",
        effective_date="2026-01-01",
        name="Test Workflow",
        description="",
        scopes={"project": ScopeConfig(parent=None)},
        document_types={
            "discovery": DocumentTypeConfig(name="Discovery", scope="project"),
            "backlog": DocumentTypeConfig(name="Backlog", scope="project"),
        },
        entity_types={},
        steps=[
            WorkflowStep(
                step_id="step1",
                scope="project",
                role="PM",
                task_prompt="Discovery",
                produces="discovery",
                inputs=[],
            ),
            WorkflowStep(
                step_id="step2",
                scope="project",
                role="PM",
                task_prompt="Backlog",
                produces="backlog",
                inputs=[],
            ),
        ],
    )


@pytest.fixture
def step_executor():
    """Create step executor with mocks."""
    llm = MockLLMService({"default": '{"result": "success"}'})
    return StepExecutor(
        prompt_loader=MockPromptLoader(),
        clarification_gate=ClarificationGate(),
        qa_gate=QAGate(),
        llm_service=llm,
    )


class TestWorkflowExecutor:
    """Tests for WorkflowExecutor."""
    
    @pytest.mark.asyncio
    async def test_start_creates_state(self, simple_workflow, step_executor):
        """start() creates initial state and context."""
        executor = WorkflowExecutor(step_executor)
        result = await executor.start(simple_workflow, "proj_1")
        
        assert result.state.workflow_id == "test_wf"
        assert result.state.project_id == "proj_1"
        assert result.context.project_id == "proj_1"
    
    @pytest.mark.asyncio
    async def test_execute_single_step(self, step_executor):
        """Execute workflow with single step."""
        workflow = Workflow(
            schema_version="workflow.v1",
            workflow_id="single",
            revision="1",
            effective_date="2026-01-01",
            name="Single Step",
            description="",
            scopes={"project": ScopeConfig(parent=None)},
            document_types={
                "output": DocumentTypeConfig(name="Output", scope="project"),
            },
            entity_types={},
            steps=[
                WorkflowStep(
                    step_id="only_step",
                    scope="project",
                    role="PM",
                    task_prompt="Do it",
                    produces="output",
                    inputs=[],
                ),
            ],
        )
        
        executor = WorkflowExecutor(step_executor)
        result = await executor.start(workflow, "proj_1")
        
        assert result.state.status == WorkflowStatus.COMPLETED
        assert "only_step" in result.state.completed_steps
    
    @pytest.mark.asyncio
    async def test_execute_multiple_steps(self, simple_workflow, step_executor):
        """Execute workflow with multiple steps."""
        executor = WorkflowExecutor(step_executor)
        result = await executor.start(simple_workflow, "proj_1")
        
        assert result.state.status == WorkflowStatus.COMPLETED
        assert "step1" in result.state.completed_steps
        assert "step2" in result.state.completed_steps
    
    @pytest.mark.asyncio
    async def test_stores_documents(self, simple_workflow, step_executor):
        """Step outputs are stored in context."""
        executor = WorkflowExecutor(step_executor)
        result = await executor.start(simple_workflow, "proj_1")
        
        doc1 = result.context.get_document("discovery", "project")
        doc2 = result.context.get_document("backlog", "project")
        
        assert doc1 is not None
        assert doc2 is not None

    
    @pytest.mark.asyncio
    async def test_pause_at_acceptance(self, step_executor):
        """Workflow pauses when document requires acceptance."""
        workflow = Workflow(
            schema_version="workflow.v1",
            workflow_id="acceptance_wf",
            revision="1",
            effective_date="2026-01-01",
            name="Acceptance Workflow",
            description="",
            scopes={"project": ScopeConfig(parent=None)},
            document_types={
                "review_doc": DocumentTypeConfig(
                    name="Review Doc",
                    scope="project",
                    acceptance_required=True,
                    accepted_by=["PM"],
                ),
            },
            entity_types={},
            steps=[
                WorkflowStep(
                    step_id="review_step",
                    scope="project",
                    role="PM",
                    task_prompt="Review",
                    produces="review_doc",
                    inputs=[],
                ),
            ],
        )
        
        executor = WorkflowExecutor(step_executor)
        result = await executor.start(workflow, "proj_1")
        
        assert result.paused is True
        assert result.state.status == WorkflowStatus.WAITING_ACCEPTANCE
        assert result.state.pending_acceptance == "review_doc"
    
    @pytest.mark.asyncio
    async def test_resume_after_acceptance(self, step_executor):
        """Workflow resumes after acceptance decision."""
        workflow = Workflow(
            schema_version="workflow.v1",
            workflow_id="resume_wf",
            revision="1",
            effective_date="2026-01-01",
            name="Resume Workflow",
            description="",
            scopes={"project": ScopeConfig(parent=None)},
            document_types={
                "doc1": DocumentTypeConfig(
                    name="Doc1",
                    scope="project",
                    acceptance_required=True,
                ),
                "doc2": DocumentTypeConfig(name="Doc2", scope="project"),
            },
            entity_types={},
            steps=[
                WorkflowStep(
                    step_id="s1", scope="project", role="PM",
                    task_prompt="S1", produces="doc1", inputs=[],
                ),
                WorkflowStep(
                    step_id="s2", scope="project", role="PM",
                    task_prompt="S2", produces="doc2", inputs=[],
                ),
            ],
        )
        
        executor = WorkflowExecutor(step_executor)
        result = await executor.start(workflow, "proj_1")
        
        assert result.paused is True
        assert result.state.status == WorkflowStatus.WAITING_ACCEPTANCE
        
        decision = AcceptanceDecision(
            doc_type="doc1", scope_id=None, accepted=True,
            comment="OK", decided_by="user"
        )
        result = await executor.process_acceptance(
            workflow, result.state, result.context, decision
        )
        
        assert result.state.status == WorkflowStatus.COMPLETED
        assert "s2" in result.state.completed_steps
    
    @pytest.mark.asyncio
    async def test_rejection_fails_workflow(self, step_executor):
        """Rejection fails the workflow."""
        workflow = Workflow(
            schema_version="workflow.v1",
            workflow_id="reject_wf",
            revision="1",
            effective_date="2026-01-01",
            name="Reject Workflow",
            description="",
            scopes={"project": ScopeConfig(parent=None)},
            document_types={
                "doc": DocumentTypeConfig(
                    name="Doc", scope="project", acceptance_required=True,
                ),
            },
            entity_types={},
            steps=[
                WorkflowStep(
                    step_id="s1", scope="project", role="PM",
                    task_prompt="S1", produces="doc", inputs=[],
                ),
            ],
        )
        
        executor = WorkflowExecutor(step_executor)
        result = await executor.start(workflow, "proj_1")
        
        decision = AcceptanceDecision(
            doc_type="doc", scope_id=None, accepted=False,
            comment="Not good", decided_by="user"
        )
        result = await executor.process_acceptance(
            workflow, result.state, result.context, decision
        )
        
        assert result.state.status == WorkflowStatus.FAILED
        assert "rejected" in result.state.error.lower()


class TestIterationExecution:
    """Tests for iteration step execution."""
    
    @pytest.fixture
    def iteration_workflow(self):
        """Workflow with iteration step."""
        return Workflow(
            schema_version="workflow.v1",
            workflow_id="iter_wf",
            revision="1",
            effective_date="2026-01-01",
            name="Iteration Workflow",
            description="",
            scopes={
                "project": ScopeConfig(parent=None),
                "epic": ScopeConfig(parent="project"),
            },
            document_types={
                "backlog": DocumentTypeConfig(name="Backlog", scope="project"),
                "epic_arch": DocumentTypeConfig(name="Epic Arch", scope="epic"),
            },
            entity_types={
                "epic": EntityTypeConfig(
                    name="Epic",
                    parent_doc_type="backlog",
                    creates_scope="epic",
                ),
            },
            steps=[
                WorkflowStep(
                    step_id="iter_epics",
                    scope="epic",
                    iterate_over=IterationConfig(
                        doc_type="backlog",
                        collection_field="epics",
                        entity_type="epic",
                    ),
                    steps=[
                        WorkflowStep(
                            step_id="epic_step",
                            scope="epic",
                            role="Architect",
                            task_prompt="Design",
                            produces="epic_arch",
                            inputs=[],
                        ),
                    ],
                ),
            ],
        )
    
    @pytest.fixture
    def iter_step_executor(self):
        """Step executor with mocks for iteration tests."""
        llm = MockLLMService({"default": '{"design": "done"}'})
        return StepExecutor(
            prompt_loader=MockPromptLoader(),
            clarification_gate=ClarificationGate(),
            qa_gate=QAGate(),
            llm_service=llm,
        )
    
    @pytest.mark.asyncio
    async def test_iteration_processes_all_items(self, iteration_workflow, iter_step_executor):
        """Iteration processes each item in collection."""
        executor = WorkflowExecutor(iter_step_executor)
        
        context = WorkflowContext(iteration_workflow, "proj_1")
        context.store_document("backlog", {
            "epics": [
                {"id": "epic_1", "name": "Auth"},
                {"id": "epic_2", "name": "Payments"},
            ]
        })
        
        state = WorkflowState(workflow_id="iter_wf", project_id="proj_1")
        state.start()
        
        result = await executor.run_until_pause(iteration_workflow, state, context)
        
        assert result.state.status == WorkflowStatus.COMPLETED
        assert "iter_epics" in result.state.completed_steps
        
        arch1 = result.context.get_document("epic_arch", "epic", "epic_1")
        arch2 = result.context.get_document("epic_arch", "epic", "epic_2")
        assert arch1 is not None
        assert arch2 is not None
    
    @pytest.mark.asyncio
    async def test_empty_iteration_completes(self, iteration_workflow, iter_step_executor):
        """Empty collection still completes step."""
        executor = WorkflowExecutor(iter_step_executor)
        
        context = WorkflowContext(iteration_workflow, "proj_1")
        context.store_document("backlog", {"epics": []})
        
        state = WorkflowState(workflow_id="iter_wf", project_id="proj_1")
        state.start()
        
        result = await executor.run_until_pause(iteration_workflow, state, context)
        
        assert result.state.status == WorkflowStatus.COMPLETED
        assert "iter_epics" in result.state.completed_steps
