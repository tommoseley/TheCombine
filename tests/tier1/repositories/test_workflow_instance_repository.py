"""Tests for WorkflowInstanceRepository.

Per WS-ADR-046-001 Phase 2.
Tier-1 tests using mocked database session.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.api.models.workflow_instance import WorkflowInstance, WorkflowInstanceHistory
from app.api.repositories.workflow_instance_repository import WorkflowInstanceRepository


SAMPLE_BASE_REF = {
    "workflow_id": "software_product_development",
    "version": "1.0.0",
    "pow_class": "reference",
}

SAMPLE_EFFECTIVE = {
    "schema_version": "workflow.v2",
    "workflow_id": "software_product_development",
    "name": "Software Product Development",
    "pow_class": "instance",
    "steps": [{"step_id": "discovery", "produces": "project_discovery"}],
}


@pytest.mark.asyncio
class TestWorkflowInstanceRepository:
    """Tests for WorkflowInstanceRepository CRUD."""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        return db

    @pytest.fixture
    def repo(self, mock_db):
        return WorkflowInstanceRepository(mock_db)

    async def test_create_adds_instance(self, repo, mock_db):
        """Create should add instance to session and flush."""
        # Mock get_by_project_id to return None (no existing instance)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        project_id = uuid4()
        instance = await repo.create(
            project_id=project_id,
            base_workflow_ref=SAMPLE_BASE_REF,
            effective_workflow=SAMPLE_EFFECTIVE,
        )

        assert instance.project_id == project_id
        assert instance.base_workflow_ref == SAMPLE_BASE_REF
        assert instance.effective_workflow == SAMPLE_EFFECTIVE
        assert instance.status == "active"
        mock_db.add.assert_called_once_with(instance)
        mock_db.flush.assert_called_once()

    async def test_create_raises_on_duplicate(self, repo, mock_db):
        """Create should raise ValueError if project already has an instance."""
        existing = WorkflowInstance(
            id=uuid4(),
            project_id=uuid4(),
            base_workflow_ref=SAMPLE_BASE_REF,
            effective_workflow=SAMPLE_EFFECTIVE,
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="already has a workflow instance"):
            await repo.create(
                project_id=existing.project_id,
                base_workflow_ref=SAMPLE_BASE_REF,
                effective_workflow=SAMPLE_EFFECTIVE,
            )

    async def test_get_by_project_id_returns_instance(self, repo, mock_db):
        """get_by_project_id returns instance when found."""
        project_id = uuid4()
        instance = WorkflowInstance(
            id=uuid4(),
            project_id=project_id,
            base_workflow_ref=SAMPLE_BASE_REF,
            effective_workflow=SAMPLE_EFFECTIVE,
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = instance
        mock_db.execute.return_value = mock_result

        result = await repo.get_by_project_id(project_id)
        assert result == instance

    async def test_get_by_project_id_returns_none(self, repo, mock_db):
        """get_by_project_id returns None when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await repo.get_by_project_id(uuid4())
        assert result is None

    async def test_get_by_id_returns_instance(self, repo, mock_db):
        """get_by_id returns instance when found."""
        instance_id = uuid4()
        instance = WorkflowInstance(
            id=instance_id,
            project_id=uuid4(),
            base_workflow_ref=SAMPLE_BASE_REF,
            effective_workflow=SAMPLE_EFFECTIVE,
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = instance
        mock_db.execute.return_value = mock_result

        result = await repo.get_by_id(instance_id)
        assert result == instance

    async def test_update_effective_workflow(self, repo, mock_db):
        """update_effective_workflow replaces the snapshot."""
        instance_id = uuid4()
        instance = WorkflowInstance(
            id=instance_id,
            project_id=uuid4(),
            base_workflow_ref=SAMPLE_BASE_REF,
            effective_workflow=SAMPLE_EFFECTIVE,
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = instance
        mock_db.execute.return_value = mock_result

        new_workflow = {**SAMPLE_EFFECTIVE, "name": "Updated"}
        result = await repo.update_effective_workflow(instance_id, new_workflow)

        assert result.effective_workflow == new_workflow
        mock_db.flush.assert_called()

    async def test_update_effective_workflow_returns_none_if_missing(self, repo, mock_db):
        """update_effective_workflow returns None if instance not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await repo.update_effective_workflow(uuid4(), SAMPLE_EFFECTIVE)
        assert result is None

    async def test_update_status(self, repo, mock_db):
        """update_status changes the status field."""
        instance = WorkflowInstance(
            id=uuid4(),
            project_id=uuid4(),
            base_workflow_ref=SAMPLE_BASE_REF,
            effective_workflow=SAMPLE_EFFECTIVE,
            status="active",
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = instance
        mock_db.execute.return_value = mock_result

        result = await repo.update_status(instance.id, "completed")
        assert result.status == "completed"
        mock_db.flush.assert_called()

    async def test_add_history_appends_entry(self, repo, mock_db):
        """add_history creates an append-only history record."""
        instance_id = uuid4()
        entry = await repo.add_history(
            instance_id=instance_id,
            change_type="created",
            change_detail={"source": "software_product_development"},
            changed_by="system",
        )

        assert entry.instance_id == instance_id
        assert entry.change_type == "created"
        assert entry.change_detail == {"source": "software_product_development"}
        assert entry.changed_by == "system"
        mock_db.add.assert_called_once_with(entry)
        mock_db.flush.assert_called_once()

    async def test_get_history_returns_entries(self, repo, mock_db):
        """get_history returns list of history entries."""
        entry = WorkflowInstanceHistory(
            id=uuid4(),
            instance_id=uuid4(),
            change_type="created",
        )
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [entry]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await repo.get_history(entry.instance_id)
        assert len(result) == 1
        assert result[0] == entry

    async def test_get_history_returns_empty(self, repo, mock_db):
        """get_history returns empty list when no entries."""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await repo.get_history(uuid4())
        assert result == []

    async def test_count_history(self, repo, mock_db):
        """count_history returns number of entries."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        mock_db.execute.return_value = mock_result

        count = await repo.count_history(uuid4())
        assert count == 5


class TestWorkflowInstanceModel:
    """Tests for WorkflowInstance model."""

    def test_to_dict(self):
        project_id = uuid4()
        instance_id = uuid4()
        instance = WorkflowInstance(
            id=instance_id,
            project_id=project_id,
            base_workflow_ref=SAMPLE_BASE_REF,
            effective_workflow=SAMPLE_EFFECTIVE,
            status="active",
        )
        instance.created_at = None
        instance.updated_at = None

        result = instance.to_dict()

        assert result["id"] == str(instance_id)
        assert result["project_id"] == str(project_id)
        assert result["base_workflow_ref"] == SAMPLE_BASE_REF
        assert result["effective_workflow"] == SAMPLE_EFFECTIVE
        assert result["status"] == "active"
        assert result["created_at"] is None
        assert result["updated_at"] is None


class TestWorkflowInstanceHistoryModel:
    """Tests for WorkflowInstanceHistory model."""

    def test_to_dict(self):
        entry = WorkflowInstanceHistory(
            id=uuid4(),
            instance_id=uuid4(),
            change_type="step_added",
            change_detail={"step_id": "new_step"},
            changed_by="tom",
        )
        entry.changed_at = None

        result = entry.to_dict()

        assert result["change_type"] == "step_added"
        assert result["change_detail"] == {"step_id": "new_step"}
        assert result["changed_by"] == "tom"
        assert result["changed_at"] is None
