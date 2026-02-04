"""Tests for WorkflowInstanceService.

Per WS-ADR-046-001 Phase 3.
Tier-1 tests with mocked repository and workbench service.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.api.services.workflow_instance_service import (
    WorkflowInstanceService,
    DriftSummary,
)
from app.api.models.workflow_instance import WorkflowInstance, WorkflowInstanceHistory


SAMPLE_DEFINITION = {
    "schema_version": "workflow.v2",
    "workflow_id": "software_product_development",
    "name": "Software Product Development",
    "description": "End-to-end workflow",
    "pow_class": "reference",
    "tags": ["software_delivery"],
    "steps": [
        {"step_id": "discovery", "produces": "project_discovery"},
        {"step_id": "architecture", "produces": "technical_architecture"},
        {"step_id": "planning", "produces": "implementation_plan"},
    ],
}


@pytest.fixture
def mock_workbench():
    wb = MagicMock()
    wb.get_workflow.return_value = {
        "workflow_id": "software_product_development",
        "version": "1.0.0",
        "definition": SAMPLE_DEFINITION,
    }
    return wb


@pytest.fixture
def service(mock_workbench):
    return WorkflowInstanceService(mock_workbench)


@pytest.fixture
def mock_db():
    return AsyncMock()


class TestDetectChanges:
    """Unit tests for _detect_changes static method."""

    def test_no_changes(self):
        changes = WorkflowInstanceService._detect_changes(
            SAMPLE_DEFINITION, SAMPLE_DEFINITION
        )
        assert len(changes) == 1
        assert changes[0][0] == "updated"

    def test_step_added(self):
        new = {**SAMPLE_DEFINITION, "steps": [
            *SAMPLE_DEFINITION["steps"],
            {"step_id": "testing", "produces": "test_plan"},
        ]}
        changes = WorkflowInstanceService._detect_changes(SAMPLE_DEFINITION, new)
        types = [c[0] for c in changes]
        assert "step_added" in types
        added = next(c for c in changes if c[0] == "step_added")
        assert "testing" in added[1]["step_ids"]

    def test_step_removed(self):
        new = {**SAMPLE_DEFINITION, "steps": SAMPLE_DEFINITION["steps"][:2]}
        changes = WorkflowInstanceService._detect_changes(SAMPLE_DEFINITION, new)
        types = [c[0] for c in changes]
        assert "step_removed" in types
        removed = next(c for c in changes if c[0] == "step_removed")
        assert "planning" in removed[1]["step_ids"]

    def test_step_reordered(self):
        new = {**SAMPLE_DEFINITION, "steps": list(reversed(SAMPLE_DEFINITION["steps"]))}
        changes = WorkflowInstanceService._detect_changes(SAMPLE_DEFINITION, new)
        types = [c[0] for c in changes]
        assert "step_reordered" in types

    def test_metadata_changed(self):
        new = {**SAMPLE_DEFINITION, "name": "Renamed Workflow"}
        changes = WorkflowInstanceService._detect_changes(SAMPLE_DEFINITION, new)
        types = [c[0] for c in changes]
        assert "metadata_changed" in types


class TestComputeDriftSummary:
    """Unit tests for _compute_drift_summary static method."""

    def test_no_drift(self):
        result = WorkflowInstanceService._compute_drift_summary(
            "sw", "1.0.0", SAMPLE_DEFINITION, SAMPLE_DEFINITION
        )
        assert result.is_drifted is False
        assert result.steps_added == []
        assert result.steps_removed == []
        assert result.steps_reordered is False
        assert result.metadata_changed is False

    def test_drift_with_added_steps(self):
        instance = {**SAMPLE_DEFINITION, "steps": [
            *SAMPLE_DEFINITION["steps"],
            {"step_id": "qa", "produces": "qa_report"},
        ]}
        result = WorkflowInstanceService._compute_drift_summary(
            "sw", "1.0.0", SAMPLE_DEFINITION, instance
        )
        assert result.is_drifted is True
        assert "qa" in result.steps_added

    def test_drift_with_removed_steps(self):
        instance = {**SAMPLE_DEFINITION, "steps": SAMPLE_DEFINITION["steps"][:1]}
        result = WorkflowInstanceService._compute_drift_summary(
            "sw", "1.0.0", SAMPLE_DEFINITION, instance
        )
        assert result.is_drifted is True
        assert "architecture" in result.steps_removed
        assert "planning" in result.steps_removed

    def test_drift_with_reorder(self):
        instance = {**SAMPLE_DEFINITION, "steps": list(reversed(SAMPLE_DEFINITION["steps"]))}
        result = WorkflowInstanceService._compute_drift_summary(
            "sw", "1.0.0", SAMPLE_DEFINITION, instance
        )
        assert result.is_drifted is True
        assert result.steps_reordered is True

    def test_drift_with_metadata_change(self):
        instance = {**SAMPLE_DEFINITION, "tags": ["custom_tag"]}
        result = WorkflowInstanceService._compute_drift_summary(
            "sw", "1.0.0", SAMPLE_DEFINITION, instance
        )
        assert result.is_drifted is True
        assert result.metadata_changed is True


@pytest.mark.asyncio
class TestCreateInstance:
    """Tests for create_instance."""

    async def test_create_snapshots_source(self, service, mock_db, mock_workbench):
        """create_instance should snapshot the source definition."""
        project_id = uuid4()

        with patch(
            "app.api.services.workflow_instance_service.WorkflowInstanceRepository"
        ) as MockRepo:
            repo_instance = AsyncMock()
            MockRepo.return_value = repo_instance

            created = WorkflowInstance(
                id=uuid4(),
                project_id=project_id,
                base_workflow_ref={
                    "workflow_id": "software_product_development",
                    "version": "1.0.0",
                    "pow_class": "reference",
                },
                effective_workflow=SAMPLE_DEFINITION,
                status="active",
            )
            repo_instance.create.return_value = created
            repo_instance.add_history.return_value = WorkflowInstanceHistory(
                id=uuid4(),
                instance_id=created.id,
                change_type="created",
            )

            result = await service.create_instance(
                mock_db, project_id, "software_product_development", "1.0.0"
            )

            assert result.project_id == project_id
            assert result.effective_workflow == SAMPLE_DEFINITION
            mock_workbench.get_workflow.assert_called_once_with(
                "software_product_development", "1.0.0"
            )
            repo_instance.create.assert_called_once()
            repo_instance.add_history.assert_called_once()
            mock_db.commit.assert_called_once()

    async def test_create_raises_on_duplicate(self, service, mock_db):
        """create_instance should raise ValueError for duplicate."""
        with patch(
            "app.api.services.workflow_instance_service.WorkflowInstanceRepository"
        ) as MockRepo:
            repo_instance = AsyncMock()
            MockRepo.return_value = repo_instance
            repo_instance.create.side_effect = ValueError("already has")

            with pytest.raises(ValueError, match="already has"):
                await service.create_instance(
                    mock_db, uuid4(), "sw", "1.0.0"
                )


@pytest.mark.asyncio
class TestGetInstance:
    """Tests for get_instance."""

    async def test_returns_instance(self, service, mock_db):
        project_id = uuid4()
        instance = WorkflowInstance(
            id=uuid4(), project_id=project_id,
            base_workflow_ref={}, effective_workflow={},
        )

        with patch(
            "app.api.services.workflow_instance_service.WorkflowInstanceRepository"
        ) as MockRepo:
            repo_instance = AsyncMock()
            MockRepo.return_value = repo_instance
            repo_instance.get_by_project_id.return_value = instance

            result = await service.get_instance(mock_db, project_id)
            assert result == instance

    async def test_returns_none(self, service, mock_db):
        with patch(
            "app.api.services.workflow_instance_service.WorkflowInstanceRepository"
        ) as MockRepo:
            repo_instance = AsyncMock()
            MockRepo.return_value = repo_instance
            repo_instance.get_by_project_id.return_value = None

            result = await service.get_instance(mock_db, uuid4())
            assert result is None


@pytest.mark.asyncio
class TestComputeDrift:
    """Tests for compute_drift integration."""

    async def test_no_drift(self, service, mock_db, mock_workbench):
        """Instance identical to source should show no drift."""
        project_id = uuid4()
        instance = WorkflowInstance(
            id=uuid4(), project_id=project_id,
            base_workflow_ref={
                "workflow_id": "software_product_development",
                "version": "1.0.0",
                "pow_class": "reference",
            },
            effective_workflow=SAMPLE_DEFINITION,
        )

        with patch(
            "app.api.services.workflow_instance_service.WorkflowInstanceRepository"
        ) as MockRepo:
            repo_instance = AsyncMock()
            MockRepo.return_value = repo_instance
            repo_instance.get_by_project_id.return_value = instance

            result = await service.compute_drift(mock_db, project_id)

            assert isinstance(result, DriftSummary)
            assert result.is_drifted is False

    async def test_drift_detected(self, service, mock_db, mock_workbench):
        """Instance with added step should show drift."""
        project_id = uuid4()
        modified = {**SAMPLE_DEFINITION, "steps": [
            *SAMPLE_DEFINITION["steps"],
            {"step_id": "extra", "produces": "extra_doc"},
        ]}
        instance = WorkflowInstance(
            id=uuid4(), project_id=project_id,
            base_workflow_ref={
                "workflow_id": "software_product_development",
                "version": "1.0.0",
                "pow_class": "reference",
            },
            effective_workflow=modified,
        )

        with patch(
            "app.api.services.workflow_instance_service.WorkflowInstanceRepository"
        ) as MockRepo:
            repo_instance = AsyncMock()
            MockRepo.return_value = repo_instance
            repo_instance.get_by_project_id.return_value = instance

            result = await service.compute_drift(mock_db, project_id)

            assert result.is_drifted is True
            assert "extra" in result.steps_added

    async def test_raises_if_no_instance(self, service, mock_db):
        with patch(
            "app.api.services.workflow_instance_service.WorkflowInstanceRepository"
        ) as MockRepo:
            repo_instance = AsyncMock()
            MockRepo.return_value = repo_instance
            repo_instance.get_by_project_id.return_value = None

            with pytest.raises(ValueError, match="No workflow instance"):
                await service.compute_drift(mock_db, uuid4())


@pytest.mark.asyncio
class TestStatusTransitions:
    """Tests for complete_instance and archive_instance."""

    async def test_complete(self, service, mock_db):
        project_id = uuid4()
        instance = WorkflowInstance(
            id=uuid4(), project_id=project_id,
            base_workflow_ref={}, effective_workflow={},
            status="active",
        )

        with patch(
            "app.api.services.workflow_instance_service.WorkflowInstanceRepository"
        ) as MockRepo:
            repo_instance = AsyncMock()
            MockRepo.return_value = repo_instance
            repo_instance.get_by_project_id.return_value = instance

            completed = WorkflowInstance(
                id=instance.id, project_id=project_id,
                base_workflow_ref={}, effective_workflow={},
                status="completed",
            )
            repo_instance.update_status.return_value = completed
            repo_instance.add_history.return_value = WorkflowInstanceHistory(
                id=uuid4(), instance_id=instance.id, change_type="status_changed",
            )

            result = await service.complete_instance(mock_db, project_id)
            assert result.status == "completed"
            repo_instance.update_status.assert_called_once_with(
                instance.id, "completed"
            )
