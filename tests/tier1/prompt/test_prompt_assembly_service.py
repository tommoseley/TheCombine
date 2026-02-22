"""Tests for PromptAssemblyService.

Uses combine-config as the canonical source for prompts and schemas.
Workflow definitions are test-owned fixtures (written to tmp_path)
since the PromptAssemblyService's flat-file workflow loading doesn't
match combine-config's hierarchical release structure.
"""

import json
import pytest

from app.domain.services.prompt_assembly_service import (
    PromptAssemblyService,
)
from app.domain.prompt.errors import PromptAssemblyError


@pytest.fixture
def _workflow_dir(tmp_path):
    """Create test workflow files in tmp_path using combine-config references."""
    workflow_dir = tmp_path / "workflows"
    workflow_dir.mkdir()

    # project_discovery workflow with nodes that use combine-config paths/URNs
    pd_workflow = {
        "workflow_id": "project_discovery",
        "version": "1.0.0",
        "nodes": [
            {
                "node_id": "pgc",
                "type": "pgc",
                "task_ref": "tasks/Clarification Questions Generator v1.1",
                "includes": {
                    "PGC_CONTEXT": "combine-config/prompts/pgc/project_discovery.v1/releases/1.0.0/pgc.prompt.txt",
                    "OUTPUT_SCHEMA": "schema:project_discovery:1.4.0",
                },
            },
            {
                "node_id": "generation",
                "type": "task",
                "task_ref": "prompt:template:document_generator:1.0.0",
                "includes": {
                    "ROLE_PROMPT": "prompt:role:technical_architect:1.0.0",
                    "TASK_PROMPT": "prompt:task:project_discovery:1.4.0",
                    "OUTPUT_SCHEMA": "schema:project_discovery:1.4.0",
                },
                "produces": "project_discovery",
            },
        ],
    }
    (workflow_dir / "project_discovery.v1.json").write_text(
        json.dumps(pd_workflow)
    )

    # concierge_intake workflow (minimal, for list_workflows test)
    ci_workflow = {
        "workflow_id": "concierge_intake",
        "version": "1.0.0",
        "nodes": [
            {
                "node_id": "entry",
                "type": "task",
                "task_ref": "prompt:task:concierge_intent_reflection:1.0.0",
                "includes": {},
            },
        ],
    }
    (workflow_dir / "concierge_intake.v1.json").write_text(
        json.dumps(ci_workflow)
    )

    return workflow_dir


@pytest.fixture
def service(_workflow_dir):
    """Create service with combine-config prompts and test workflow dir."""
    return PromptAssemblyService(
        workflow_root=_workflow_dir,
    )


class TestPromptAssemblyService:
    """Tests for PromptAssemblyService.

    Uses combine-config as canonical source via PackageLoader.
    Workflow definitions are test-owned fixtures.
    """

    def test_assemble_direct(self, service):
        """Direct assembly with task_ref and includes."""
        result = service.assemble(
            task_ref="tasks/Clarification Questions Generator v1.1",
            includes={
                "PGC_CONTEXT": "combine-config/prompts/pgc/project_discovery.v1/releases/1.0.0/pgc.prompt.txt",
                "OUTPUT_SCHEMA": "schema:project_discovery:1.4.0",
            },
            correlation_id="550e8400-e29b-41d4-a716-446655440001",
        )

        assert result.task_ref == "tasks/Clarification Questions Generator v1.1"
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

        assert result.task_ref == "tasks/Clarification Questions Generator v1.1"
        assert len(result.content) > 0
        assert "PGC_CONTEXT" in result.includes_resolved

    def test_get_workflow_node(self, service):
        """Get workflow node without assembly."""
        node = service.get_workflow_node("project_discovery", "pgc")

        assert node.node_id == "pgc"
        assert node.task_ref == "tasks/Clarification Questions Generator v1.1"
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
            task_ref="tasks/Clarification Questions Generator v1.1",
            includes={
                "PGC_CONTEXT": "combine-config/prompts/pgc/project_discovery.v1/releases/1.0.0/pgc.prompt.txt",
                "OUTPUT_SCHEMA": "schema:project_discovery:1.4.0",
            },
        )

        result2 = service.assemble(
            task_ref="tasks/Clarification Questions Generator v1.1",
            includes={
                "PGC_CONTEXT": "combine-config/prompts/pgc/project_discovery.v1/releases/1.0.0/pgc.prompt.txt",
                "OUTPUT_SCHEMA": "schema:project_discovery:1.4.0",
            },
        )

        assert result1.content_hash == result2.content_hash
        assert result1.content == result2.content
