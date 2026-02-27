"""Tests for LLM step executor."""

import pytest

from app.execution import (
    LLMStepExecutor,
    StepInput,
    ExecutionContext,
    create_test_executor,
)
from app.llm import (
    MockLLMProvider,
    LLMError,
    PromptBuilder,
    OutputParser,
    TelemetryService,
    InMemoryTelemetryStore,
    DocumentCondenser,
)
from app.persistence import (
    InMemoryDocumentRepository,
    InMemoryExecutionRepository,
)


@pytest.fixture
def repos():
    return InMemoryDocumentRepository(), InMemoryExecutionRepository()


@pytest.fixture
def telemetry_store():
    return InMemoryTelemetryStore()


@pytest.fixture
def mock_provider():
    return MockLLMProvider(
        default_response='{"status": "completed", "result": "test"}',
    )


@pytest.fixture
def executor(mock_provider, telemetry_store):
    return LLMStepExecutor(
        llm_provider=mock_provider,
        prompt_builder=PromptBuilder(),
        output_parser=OutputParser(),
        telemetry=TelemetryService(telemetry_store),
        condenser=DocumentCondenser(),
        default_model="mock",
    )


class TestLLMStepExecutor:
    """Tests for LLMStepExecutor."""
    
    @pytest.mark.asyncio
    async def test_execute_success(self, executor, repos):
        """Successful step execution."""
        doc_repo, exec_repo = repos
        
        ctx = await ExecutionContext.create(
            workflow_id="test",
            scope_type="project",
            scope_id="p1",
            document_repo=doc_repo,
            execution_repo=exec_repo,
        )
        
        result = await executor.execute(
            step_id="step-1",
            role="PM",
            task_prompt="Generate output",
            context=ctx,
            output_type="test-doc",
        )
        
        assert result.success is True
        assert result.document is not None
        assert result.document.content["status"] == "completed"
    
    @pytest.mark.asyncio
    async def test_execute_records_telemetry(self, executor, repos, telemetry_store):
        """Execution records telemetry."""
        doc_repo, exec_repo = repos
        
        ctx = await ExecutionContext.create(
            workflow_id="test",
            scope_type="project",
            scope_id="p1",
            document_repo=doc_repo,
            execution_repo=exec_repo,
        )
        
        await executor.execute(
            step_id="step-1",
            role="PM",
            task_prompt="Generate output",
            context=ctx,
        )
        
        calls = await telemetry_store.get_execution_calls(ctx.execution_id)
        assert len(calls) == 1
        assert calls[0].step_id == "step-1"
    
    @pytest.mark.asyncio
    async def test_execute_with_inputs(self, executor, repos):
        """Execution with input documents."""
        doc_repo, exec_repo = repos
        
        ctx = await ExecutionContext.create(
            workflow_id="test",
            scope_type="project",
            scope_id="p1",
            document_repo=doc_repo,
            execution_repo=exec_repo,
        )
        
        inputs = [
            StepInput(
                document_type="requirements",
                content={"items": ["req1", "req2"]},
                title="Requirements",
            )
        ]
        
        result = await executor.execute(
            step_id="step-1",
            role="BA",
            task_prompt="Analyze requirements",
            context=ctx,
            inputs=inputs,
        )
        
        assert result.success is True
    
    @pytest.mark.asyncio
    async def test_execute_validation_failure(self, repos, telemetry_store):
        """Handles validation failure."""
        doc_repo, exec_repo = repos
        
        provider = MockLLMProvider(
            default_response='{"incomplete": true}',
        )
        executor = LLMStepExecutor(
            llm_provider=provider,
            prompt_builder=PromptBuilder(),
            output_parser=OutputParser(),
            telemetry=TelemetryService(telemetry_store),
            default_model="mock",
        )
        
        ctx = await ExecutionContext.create(
            workflow_id="test",
            scope_type="project",
            scope_id="p1",
            document_repo=doc_repo,
            execution_repo=exec_repo,
        )
        
        result = await executor.execute(
            step_id="step-1",
            role="PM",
            task_prompt="Generate output",
            context=ctx,
            required_fields=["name", "value"],
        )
        
        assert result.success is False
        assert result.validation_errors is not None
        assert len(result.validation_errors) > 0
    
    @pytest.mark.asyncio
    async def test_execute_llm_error(self, repos, telemetry_store):
        """Handles LLM errors."""
        doc_repo, exec_repo = repos
        
        provider = MockLLMProvider()
        # Set error for all retry attempts
        provider.set_error_on_next(LLMError.api_error("Bad request", 400))
        
        executor = LLMStepExecutor(
            llm_provider=provider,
            prompt_builder=PromptBuilder(),
            output_parser=OutputParser(),
            telemetry=TelemetryService(telemetry_store),
            default_model="mock",
        )
        
        ctx = await ExecutionContext.create(
            workflow_id="test",
            scope_type="project",
            scope_id="p1",
            document_repo=doc_repo,
            execution_repo=exec_repo,
        )
        
        result = await executor.execute(
            step_id="step-1",
            role="PM",
            task_prompt="Generate output",
            context=ctx,
        )
        
        assert result.success is False
        assert "Bad request" in result.error_message
    
    @pytest.mark.asyncio
    async def test_execute_saves_document(self, executor, repos):
        """Execution saves output document."""
        doc_repo, exec_repo = repos
        
        ctx = await ExecutionContext.create(
            workflow_id="test",
            scope_type="project",
            scope_id="p1",
            document_repo=doc_repo,
            execution_repo=exec_repo,
        )
        
        await executor.execute(
            step_id="step-1",
            role="PM",
            task_prompt="Generate output",
            context=ctx,
            output_type="strategy-doc",
        )
        
        # Verify document was saved
        docs = await doc_repo.list_by_scope("project", "p1")
        assert len(docs) == 1
        assert docs[0].document_type == "strategy-doc"


class TestClarificationHandling:
    """Tests for clarification flow."""
    
    @pytest.mark.asyncio
    async def test_detect_clarification_needed(self, repos, telemetry_store):
        """Detects when clarification is needed."""
        doc_repo, exec_repo = repos
        
        provider = MockLLMProvider(
            default_response="I need more information. What is the budget?",
        )
        executor = LLMStepExecutor(
            llm_provider=provider,
            prompt_builder=PromptBuilder(),
            output_parser=OutputParser(),
            telemetry=TelemetryService(telemetry_store),
            default_model="mock",
        )
        
        ctx = await ExecutionContext.create(
            workflow_id="test",
            scope_type="project",
            scope_id="p1",
            document_repo=doc_repo,
            execution_repo=exec_repo,
        )
        
        result = await executor.execute(
            step_id="step-1",
            role="PM",
            task_prompt="Generate output",
            context=ctx,
            allow_clarification=True,
        )
        
        assert result.success is False
        assert result.needs_clarification is True
        assert ctx.step_progress["step-1"].status == "waiting_input"
    
    @pytest.mark.asyncio
    async def test_continue_with_clarification(self, repos, telemetry_store):
        """Can continue after clarification."""
        doc_repo, exec_repo = repos
        
        # First call needs clarification, second succeeds
        responses = iter([
            "I need more information. What is the budget?",
            '{"status": "completed", "budget": 10000}',
        ])
        
        def response_fn(messages, system):
            return next(responses)
        
        provider = MockLLMProvider(response_fn=response_fn)
        executor = LLMStepExecutor(
            llm_provider=provider,
            prompt_builder=PromptBuilder(),
            output_parser=OutputParser(),
            telemetry=TelemetryService(telemetry_store),
            default_model="mock",
        )
        
        ctx = await ExecutionContext.create(
            workflow_id="test",
            scope_type="project",
            scope_id="p1",
            document_repo=doc_repo,
            execution_repo=exec_repo,
        )
        
        # First execution
        result1 = await executor.execute(
            step_id="step-1",
            role="PM",
            task_prompt="Generate output",
            context=ctx,
        )
        assert result1.needs_clarification is True
        
        # Continue with answer
        result2 = await executor.continue_with_clarification(
            step_id="step-1",
            role="PM",
            task_prompt="Generate output",
            context=ctx,
            clarification_answers={"What is the budget?": "$10,000"},
        )
        
        assert result2.success is True
        assert result2.document is not None


class TestCreateTestExecutor:
    """Tests for test executor factory."""
    
    def test_create_test_executor(self):
        """Can create test executor."""
        executor, store = create_test_executor()
        
        assert executor is not None
        assert store is not None

