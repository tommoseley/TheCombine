"""
Tier-1 tests for ProjectTreeResponse workflow fields (ADR-046 Phase 6).

Validates that ProjectTreeResponse includes has_workflow and workflow_status,
and that the WorkflowInstance model has proper FK cascade on project deletion.
"""

from app.api.v1.routers.projects import ProjectTreeResponse, ProjectResponse
from app.api.models.workflow_instance import WorkflowInstance


class TestProjectTreeResponseWorkflowFields:
    """Test that ProjectTreeResponse carries workflow info."""

    def test_defaults_no_workflow(self):
        """Without workflow fields, has_workflow defaults to False."""
        resp = ProjectTreeResponse(
            project=ProjectResponse(
                id="abc",
                project_id="T-001",
                name="Test",
            ),
            documents=[],
        )
        assert resp.has_workflow is False
        assert resp.workflow_status is None

    def test_with_workflow_active(self):
        """When workflow exists, has_workflow is True and status is set."""
        resp = ProjectTreeResponse(
            project=ProjectResponse(
                id="abc",
                project_id="T-001",
                name="Test",
            ),
            documents=[],
            has_workflow=True,
            workflow_status="active",
        )
        assert resp.has_workflow is True
        assert resp.workflow_status == "active"

    def test_with_workflow_completed(self):
        """Workflow status can be completed."""
        resp = ProjectTreeResponse(
            project=ProjectResponse(
                id="abc",
                project_id="T-001",
                name="Test",
            ),
            documents=[],
            has_workflow=True,
            workflow_status="completed",
        )
        assert resp.has_workflow is True
        assert resp.workflow_status == "completed"

    def test_serialization_includes_fields(self):
        """Serialized dict includes workflow fields."""
        resp = ProjectTreeResponse(
            project=ProjectResponse(
                id="abc",
                project_id="T-001",
                name="Test",
            ),
            documents=[],
            has_workflow=True,
            workflow_status="active",
        )
        data = resp.model_dump()
        assert "has_workflow" in data
        assert "workflow_status" in data
        assert data["has_workflow"] is True
        assert data["workflow_status"] == "active"


class TestWorkflowInstanceFKCascade:
    """Verify FK cascade is defined correctly on the model."""

    def test_project_id_fk_has_cascade_delete(self):
        """WorkflowInstance.project_id FK specifies CASCADE on delete."""
        col = WorkflowInstance.__table__.columns["project_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        fk = fks[0]
        assert fk.ondelete == "CASCADE"

    def test_project_id_is_unique(self):
        """One active instance per project -- unique constraint."""
        col = WorkflowInstance.__table__.columns["project_id"]
        assert col.unique is True

    def test_project_id_not_nullable(self):
        """project_id is required."""
        col = WorkflowInstance.__table__.columns["project_id"]
        assert col.nullable is False
