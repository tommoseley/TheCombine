"""Tests for PromptAssemblyService."""

import pytest
from pathlib import Path

from app.domain.services.prompt_assembly_service import (
    PromptAssemblyService,
    WorkflowNode,
)
from app.domain.prompt.errors import PromptAssemblyError


class TestPromptAssemblyService:
    """Tests for PromptAssemblyService."""

    @pytest.fixture
    def service(self):
        """Create service with test paths."""
        return PromptAssemblyService(
            template_root=Path("seed/prompts"),
            workflow_root=Path("seed/workflows"),
        )

    def test_assemble_direct(self, service):
        """Direct assembly with task_ref and includes."""
        result = service.assemble(
            task_ref="tasks/Clarification Questions Generator v1.0",
            includes={
                "PGC_CONTEXT": "seed/prompts/pgc-contexts/project_discovery.v1.txt",
                "OUTPUT_SCHEMA": "seed/schemas/clarification_question_set.v2.json",
            },
            correlation_id="550e8400-e29b-41d4-a716-446655440001",
        )

        assert result.task_ref == "tasks/Clarification Questions Generator v1.0"
        assert len(result.content) > 0
        assert len(result.content_hash) == 64  # SHA-256 hex string
        assert "PGC_CONTEXT" in result.includes_resolved
        assert "OUTPUT_SCHEMA" in result.includes_resolved

    def test_assemble_from_workflow(self, service):
        """Assembly from workflow node configuration."""
        result = service.assemble_from_workflow(
            workflow_id="project_discovery",
            node_id="pgc",
            correlation_id="550e8400-e29b-41d4-a716-446655440002",
        )

        assert result.task_ref == "tasks/Clarification Questions Generator v1.0"
        assert len(result.content) > 0
        assert "PGC_CONTEXT" in result.includes_resolved

    def test_get_workflow_node(self, service):
        """Get workflow node without assembly."""
        node = service.get_workflow_node("project_discovery", "pgc")

        assert node.node_id == "pgc"
        assert node.task_ref == "tasks/Clarification Questions Generator v1.0"
        assert "PGC_CONTEXT" in node.includes
        assert "OUTPUT_SCHEMA" in node.includes

    def test_list_workflows(self, service):
        """List available workflows."""
        workflows = service.list_workflows()

        assert "project_discovery" in workflows
        assert "concierge_intake" in workflows

    def test_list_workflow_nodes(self, service):
        """List nodes in a workflow."""
        nodes = service.list_workflow_nodes("project_discovery")

        assert "pgc" in nodes
        assert "generation" in nodes

    def test_workflow_not_found(self, service):
        """Error on missing workflow."""
        with pytest.raises(PromptAssemblyError) as exc:
            service.assemble_from_workflow("nonexistent", "pgc")

        assert "Workflow not found" in str(exc.value)

    def test_node_not_found(self, service):
        """Error on missing node."""
        with pytest.raises(PromptAssemblyError) as exc:
            service.assemble_from_workflow("project_discovery", "nonexistent")

        assert "not found in workflow" in str(exc.value)

    def test_deterministic_hash(self, service):
        """Same inputs produce same hash."""
        result1 = service.assemble(
            task_ref="tasks/Clarification Questions Generator v1.0",
            includes={
                "PGC_CONTEXT": "seed/prompts/pgc-contexts/project_discovery.v1.txt",
                "OUTPUT_SCHEMA": "seed/schemas/clarification_question_set.v2.json",
            },
        )
        
        result2 = service.assemble(
            task_ref="tasks/Clarification Questions Generator v1.0",
            includes={
                "PGC_CONTEXT": "seed/prompts/pgc-contexts/project_discovery.v1.txt",
                "OUTPUT_SCHEMA": "seed/schemas/clarification_question_set.v2.json",
            },
        )

        assert result1.content_hash == result2.content_hash
        assert result1.content == result2.content