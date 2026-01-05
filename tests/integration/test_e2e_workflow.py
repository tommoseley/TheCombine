"""End-to-end workflow integration tests."""

import pytest
import json
from pathlib import Path
from uuid import uuid4
from decimal import Decimal

from app.execution import (
    ExecutionContext,
    LLMStepExecutor,
    StepInput,
    WorkflowDefinition,
    WorkflowLoader,
)
from app.llm import (
    MockLLMProvider,
    PromptBuilder,
    OutputParser,
    DocumentCondenser,
    TelemetryService,
    InMemoryTelemetryStore,
)
from app.persistence import (
    InMemoryDocumentRepository,
    InMemoryExecutionRepository,
    ExecutionStatus,
)


# Sample LLM responses for strategy workflow
DISCOVERY_RESPONSE = json.dumps({
    "project_name": "Test Project",
    "objectives": [
        {"id": "obj-1", "description": "Build MVP", "priority": "high"}
    ],
    "stakeholders": [
        {"name": "Product Owner", "role": "Decision Maker", "influence": "high"}
    ],
    "constraints": [
        {"type": "budget", "description": "Limited budget", "impact": "Use existing infra"}
    ],
    "risks": [],
    "assumptions": ["Team has skills"],
    "scope_summary": "Build MVP"
})

REQUIREMENTS_RESPONSE = json.dumps({
    "functional_requirements": [
        {"id": "FR-1", "title": "User Login", "description": "Users can log in", "priority": "must-have"}
    ],
    "non_functional_requirements": [
        {"id": "NFR-1", "category": "performance", "description": "Fast load"}
    ]
})

ARCHITECTURE_RESPONSE = json.dumps({
    "overview": {
        "summary": "Microservices",
        "architecture_style": "microservices",
        "key_decisions": ["Use FastAPI"]
    },
    "components": [
        {"id": "api", "name": "API", "responsibility": "Handle requests"}
    ],
    "technology_stack": {"backend": ["Python"], "database": ["PostgreSQL"]}
})

REVIEW_RESPONSE = json.dumps({
    "overall_assessment": {"status": "approved", "confidence_score": 85, "summary": "Complete"},
    "findings": [],
    "recommendation": {"action": "proceed", "rationale": "All good"}
})


class TestStrategyWorkflowE2E:
    """End-to-end tests for strategy workflow."""
    
    @pytest.fixture
    def repos(self):
        return InMemoryDocumentRepository(), InMemoryExecutionRepository()
    
    @pytest.fixture
    def telemetry_store(self):
        return InMemoryTelemetryStore()
    
    @pytest.fixture
    def mock_provider(self):
        """Provider that returns appropriate response per step."""
        def response_fn(messages, system):
            system_lower = system.lower() if system else ""
            if "analyst" in system_lower:
                return REQUIREMENTS_RESPONSE
            elif "architect" in system_lower:
                return ARCHITECTURE_RESPONSE
            elif "quality" in system_lower:
                return REVIEW_RESPONSE
            return DISCOVERY_RESPONSE
        
        return MockLLMProvider(response_fn=response_fn)
    
    @pytest.fixture
    def executor(self, mock_provider, telemetry_store):
        return LLMStepExecutor(
            llm_provider=mock_provider,
            prompt_builder=PromptBuilder(),
            output_parser=OutputParser(),
            telemetry=TelemetryService(telemetry_store),
            condenser=DocumentCondenser(),
            default_model="mock",
        )
    
    @pytest.mark.asyncio
    async def test_complete_workflow_execution(self, executor, repos, telemetry_store):
        """Execute complete strategy workflow."""
        doc_repo, exec_repo = repos
        
        ctx = await ExecutionContext.create(
            workflow_id="strategy-document",
            scope_type="project",
            scope_id="test-project",
            document_repo=doc_repo,
            execution_repo=exec_repo,
        )
        
        # Step 1: Discovery
        result1 = await executor.execute(
            step_id="discovery",
            role="PM",
            task_prompt="Analyze project",
            context=ctx,
            output_type="project-discovery",
            required_fields=["project_name", "objectives"],
        )
        assert result1.success, f"Discovery failed: {result1.error_message}"
        
        # Step 2: Requirements
        discovery_doc = await ctx.get_input_document("project-discovery")
        inputs = [StepInput("project-discovery", discovery_doc.content, "Discovery")]
        
        result2 = await executor.execute(
            step_id="requirements",
            role="BA",
            task_prompt="Create requirements",
            context=ctx,
            inputs=inputs,
            output_type="requirements-doc",
            required_fields=["functional_requirements"],
        )
        assert result2.success, f"Requirements failed: {result2.error_message}"
        
        # Step 3: Architecture
        req_doc = await ctx.get_input_document("requirements-doc")
        inputs = [
            StepInput("project-discovery", discovery_doc.content, "Discovery"),
            StepInput("requirements-doc", req_doc.content, "Requirements"),
        ]
        
        result3 = await executor.execute(
            step_id="architecture",
            role="Architect",
            task_prompt="Design architecture",
            context=ctx,
            inputs=inputs,
            output_type="architecture-doc",
            required_fields=["overview", "components"],
        )
        assert result3.success, f"Architecture failed: {result3.error_message}"
        
        # Step 4: Review
        arch_doc = await ctx.get_input_document("architecture-doc")
        inputs = [
            StepInput("project-discovery", discovery_doc.content, "Discovery"),
            StepInput("requirements-doc", req_doc.content, "Requirements"),
            StepInput("architecture-doc", arch_doc.content, "Architecture"),
        ]
        
        result4 = await executor.execute(
            step_id="review",
            role="QA",
            task_prompt="Review documents",
            context=ctx,
            inputs=inputs,
            output_type="strategy-review",
            required_fields=["overall_assessment", "recommendation"],
        )
        assert result4.success, f"Review failed: {result4.error_message}"
        
        # Verify all documents created
        docs = await doc_repo.list_by_scope("project", "test-project")
        assert len(docs) == 4
        
        # Verify telemetry
        calls = await telemetry_store.get_execution_calls(ctx.execution_id)
        assert len(calls) == 4

    
    @pytest.mark.asyncio
    async def test_workflow_with_clarification(self, repos, telemetry_store):
        """Workflow pauses for clarification then continues."""
        doc_repo, exec_repo = repos
        
        call_count = {"count": 0}
        
        def response_fn(messages, system):
            call_count["count"] += 1
            if call_count["count"] == 1:
                return "I need more information. What is the target market?"
            return DISCOVERY_RESPONSE
        
        provider = MockLLMProvider(response_fn=response_fn)
        executor = LLMStepExecutor(
            llm_provider=provider,
            prompt_builder=PromptBuilder(),
            output_parser=OutputParser(),
            telemetry=TelemetryService(telemetry_store),
            default_model="mock",
        )
        
        ctx = await ExecutionContext.create(
            workflow_id="strategy-document",
            scope_type="project",
            scope_id="test-clarification",
            document_repo=doc_repo,
            execution_repo=exec_repo,
        )
        
        # First attempt - needs clarification
        result1 = await executor.execute(
            step_id="discovery",
            role="PM",
            task_prompt="Create discovery",
            context=ctx,
            output_type="project-discovery",
            allow_clarification=True,
        )
        
        assert result1.needs_clarification is True
        assert ctx.step_progress["discovery"].status == "waiting_input"
        
        # Continue with answer
        result2 = await executor.continue_with_clarification(
            step_id="discovery",
            role="PM",
            task_prompt="Create discovery",
            context=ctx,
            clarification_answers={"What is the target market?": "Enterprise B2B"},
            output_type="project-discovery",
        )
        
        assert result2.success is True
        assert result2.document is not None


class TestWorkflowDefinitionIntegration:
    """Tests for workflow definition loading."""
    
    def test_load_strategy_workflow(self):
        """Can load strategy workflow definition."""
        loader = WorkflowLoader(Path("seed/workflows"))
        workflow = loader.load("strategy-document")
        
        assert workflow is not None
        assert workflow.workflow_id == "strategy-document"
    
    def test_workflow_execution_order(self):
        """Workflow has correct execution order."""
        loader = WorkflowLoader(Path("seed/workflows"))
        workflow = loader.load("strategy-document")
        
        order = workflow.get_execution_order()
        
        assert order[0] == "discovery"
        assert order[-1] == "review"
    
    def test_workflow_validates(self):
        """Strategy workflow passes validation."""
        loader = WorkflowLoader(Path("seed/workflows"))
        workflow = loader.load("strategy-document")
        
        errors = workflow.validate()
        assert len(errors) == 0
