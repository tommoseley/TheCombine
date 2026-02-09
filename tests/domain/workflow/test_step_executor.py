"""Tests for step executor."""

import pytest
from typing import Any, Dict, Optional

from app.domain.workflow.step_executor import StepExecutor, ExecutionResult
from app.domain.workflow.step_state import StepState, StepStatus
from app.domain.workflow.models import (
    Workflow, WorkflowStep, ScopeConfig, DocumentTypeConfig, InputReference
)
from app.domain.workflow.prompt_loader import PromptLoader
from app.domain.workflow.gates.clarification import ClarificationGate
from app.domain.workflow.gates.qa import QAGate


class MockDocumentStore:
    """Mock document store for testing."""
    
    def __init__(self):
        self.documents: Dict[str, Any] = {}
        self.entities: Dict[str, Any] = {}
    
    def add_document(self, doc_type: str, scope: str, scope_id: Optional[str], content: Dict):
        key = f"{doc_type}:{scope}:{scope_id or 'root'}"
        self.documents[key] = content
    
    def get_document(self, doc_type: str, scope: str, scope_id: Optional[str] = None):
        key = f"{doc_type}:{scope}:{scope_id or 'root'}"
        return self.documents.get(key)
    
    def get_entity(self, entity_type: str, scope: str, scope_id: Optional[str] = None):
        key = f"{entity_type}:{scope}:{scope_id or 'root'}"
        return self.entities.get(key)


class MockLLMService:
    """Mock LLM service for testing."""
    
    def __init__(self, responses: list):
        self._responses = iter(responses)
    
    async def complete(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        return next(self._responses)


@pytest.fixture
def simple_workflow():
    return Workflow(
        schema_version="workflow.v1",
        workflow_id="test",
        revision="1",
        effective_date="2026-01-01",
        name="Test",
        description="",
        scopes={"project": ScopeConfig(parent=None)},
        document_types={
            "test_output": DocumentTypeConfig(name="Test Output", scope="project")
        },
        entity_types={},
        steps=[],
    )


@pytest.fixture
def simple_step():
    return WorkflowStep(
        step_id="test_step",
        scope="project",
        role="Technical Architect 1.0",
        task_prompt="project_discovery",
        produces="test_output",
        inputs=[],
    )


@pytest.fixture
def store():
    return MockDocumentStore()


class TestStepExecutor:
    """Tests for StepExecutor."""
    
    @pytest.mark.asyncio
    async def test_execute_success(self, simple_workflow, simple_step, store):
        """Successful execution returns COMPLETED state."""
        llm = MockLLMService(['{"result": "success"}'])
        executor = StepExecutor(
            prompt_loader=PromptLoader(),
            clarification_gate=ClarificationGate(),
            qa_gate=QAGate(),
            llm_service=llm,
        )
        state = StepState(step_id="test_step")
        result = await executor.execute(simple_step, simple_workflow, store, state)
        
        assert result.state.status == StepStatus.COMPLETED
        assert result.output == {"result": "success"}
    
    @pytest.mark.asyncio
    async def test_execute_invalid_json_retries_then_fails(self, simple_workflow, simple_step, store):
        """Invalid JSON triggers remediation, eventually fails."""
        llm = MockLLMService(["not json", "still not json", "nope"])
        executor = StepExecutor(
            prompt_loader=PromptLoader(),
            clarification_gate=ClarificationGate(),
            qa_gate=QAGate(),
            llm_service=llm,
            max_remediation_attempts=3,
        )
        state = StepState(step_id="test_step", max_attempts=3)
        result = await executor.execute(simple_step, simple_workflow, store, state)
        
        assert result.state.status == StepStatus.FAILED
        assert result.state.attempt == 3
    
    @pytest.mark.asyncio
    async def test_execute_remediation_recovers(self, simple_workflow, simple_step, store):
        """Second attempt can succeed after first fails."""
        llm = MockLLMService(["bad", '{"result": "fixed"}'])
        executor = StepExecutor(
            prompt_loader=PromptLoader(),
            clarification_gate=ClarificationGate(),
            qa_gate=QAGate(),
            llm_service=llm,
            max_remediation_attempts=3,
        )
        state = StepState(step_id="test_step", max_attempts=3)
        result = await executor.execute(simple_step, simple_workflow, store, state)
        
        assert result.state.status == StepStatus.COMPLETED
        assert result.state.attempt == 2
    
    @pytest.mark.asyncio
    async def test_execute_extracts_json_from_markdown(self, simple_workflow, simple_step, store):
        """JSON in markdown code block is extracted."""
        llm = MockLLMService(['```json\n{"result": "in_block"}\n```'])
        executor = StepExecutor(
            prompt_loader=PromptLoader(),
            clarification_gate=ClarificationGate(),
            qa_gate=QAGate(),
            llm_service=llm,
        )
        state = StepState(step_id="test_step")
        result = await executor.execute(simple_step, simple_workflow, store, state)
        
        assert result.state.status == StepStatus.COMPLETED
        assert result.output == {"result": "in_block"}
    
    @pytest.mark.asyncio
    async def test_execute_with_inputs(self, simple_workflow, store):
        """Step with inputs resolves them before execution."""
        store.add_document("input_doc", "project", None, {"data": "value"})
        simple_workflow.document_types["input_doc"] = DocumentTypeConfig(
            name="Input Doc", scope="project"
        )
        step = WorkflowStep(
            step_id="test_step",
            scope="project",
            role="Technical Architect 1.0",
            task_prompt="project_discovery",
            produces="test_output",
            inputs=[InputReference(scope="project", doc_type="input_doc")],
        )
        llm = MockLLMService(['{"result": "with_input"}'])
        executor = StepExecutor(
            prompt_loader=PromptLoader(),
            clarification_gate=ClarificationGate(),
            qa_gate=QAGate(),
            llm_service=llm,
        )
        state = StepState(step_id="test_step")
        result = await executor.execute(step, simple_workflow, store, state)
        
        assert result.state.status == StepStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_execute_missing_required_input_fails(self, simple_workflow, store):
        """Missing required input fails before LLM call."""
        step = WorkflowStep(
            step_id="test_step",
            scope="project",
            role="Technical Architect 1.0",
            task_prompt="project_discovery",
            produces="test_output",
            inputs=[InputReference(scope="project", doc_type="missing", required=True)],
        )
        llm = MockLLMService(['{"never": "called"}'])
        executor = StepExecutor(
            prompt_loader=PromptLoader(),
            clarification_gate=ClarificationGate(),
            qa_gate=QAGate(),
            llm_service=llm,
        )
        state = StepState(step_id="test_step")
        result = await executor.execute(step, simple_workflow, store, state)
        
        assert result.state.status == StepStatus.FAILED
        assert "Input resolution failed" in result.state.error
    
    @pytest.mark.asyncio
    async def test_state_tracks_raw_response(self, simple_workflow, simple_step, store):
        """Raw LLM response is captured in state."""
        llm = MockLLMService(['{"result": "captured"}'])
        executor = StepExecutor(
            prompt_loader=PromptLoader(),
            clarification_gate=ClarificationGate(),
            qa_gate=QAGate(),
            llm_service=llm,
        )
        state = StepState(step_id="test_step")
        result = await executor.execute(simple_step, simple_workflow, store, state)
        
        assert result.state.raw_llm_response == '{"result": "captured"}'
    
    @pytest.mark.asyncio
    async def test_qa_history_tracks_attempts(self, simple_workflow, simple_step, store):
        """QA history accumulates across attempts."""
        llm = MockLLMService(["bad1", "bad2", '{"result": "ok"}'])
        executor = StepExecutor(
            prompt_loader=PromptLoader(),
            clarification_gate=ClarificationGate(),
            qa_gate=QAGate(),
            llm_service=llm,
            max_remediation_attempts=3,
        )
        state = StepState(step_id="test_step", max_attempts=3)
        result = await executor.execute(simple_step, simple_workflow, store, state)
        
        assert result.state.status == StepStatus.COMPLETED
        assert len(result.state.qa_history) == 3
        assert result.state.qa_history[0].passed is False
        assert result.state.qa_history[1].passed is False
        assert result.state.qa_history[2].passed is True
