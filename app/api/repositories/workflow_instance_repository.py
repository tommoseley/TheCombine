"""
WorkflowInstance Repository for The Combine.

Per ADR-046 / WS-ADR-046-001 Phase 2.
Async CRUD for project-scoped workflow instances and append-only history.
"""
from typing import Optional, List
from uuid import UUID, uuid4
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.sql import func

from app.api.models.workflow_instance import WorkflowInstance, WorkflowInstanceHistory

import logging

logger = logging.getLogger(__name__)


class WorkflowInstanceRepository:
    """Repository for workflow instance CRUD operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        project_id: UUID,
        base_workflow_ref: dict,
        effective_workflow: dict,
    ) -> WorkflowInstance:
        """
        Create a new workflow instance for a project.

        Raises ValueError if the project already has an active instance.
        """
        existing = await self.get_by_project_id(project_id)
        if existing:
            raise ValueError(f"Project {project_id} already has a workflow instance")

        instance = WorkflowInstance(
            id=uuid4(),
            project_id=project_id,
            base_workflow_ref=base_workflow_ref,
            effective_workflow=effective_workflow,
            status="active",
        )
        self.db.add(instance)
        await self.db.flush()
        return instance

    async def get_by_project_id(self, project_id: UUID) -> Optional[WorkflowInstance]:
        """Get the workflow instance for a project, or None."""
        query = select(WorkflowInstance).where(WorkflowInstance.project_id == project_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_id(self, instance_id: UUID) -> Optional[WorkflowInstance]:
        """Get a workflow instance by its own ID."""
        query = select(WorkflowInstance).where(WorkflowInstance.id == instance_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_effective_workflow(
        self,
        instance_id: UUID,
        effective_workflow: dict,
    ) -> Optional[WorkflowInstance]:
        """Replace the effective_workflow snapshot."""
        instance = await self.get_by_id(instance_id)
        if not instance:
            return None

        instance.effective_workflow = effective_workflow
        instance.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return instance

    async def update_status(
        self,
        instance_id: UUID,
        status: str,
    ) -> Optional[WorkflowInstance]:
        """Update the instance status (active, completed, archived)."""
        instance = await self.get_by_id(instance_id)
        if not instance:
            return None

        instance.status = status
        instance.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return instance

    async def add_history(
        self,
        instance_id: UUID,
        change_type: str,
        change_detail: Optional[dict] = None,
        changed_by: Optional[str] = None,
    ) -> WorkflowInstanceHistory:
        """Append a history entry for the instance."""
        entry = WorkflowInstanceHistory(
            id=uuid4(),
            instance_id=instance_id,
            change_type=change_type,
            change_detail=change_detail,
            changed_by=changed_by,
        )
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def get_history(
        self,
        instance_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> List[WorkflowInstanceHistory]:
        """Get history entries for an instance, newest first."""
        query = (
            select(WorkflowInstanceHistory)
            .where(WorkflowInstanceHistory.instance_id == instance_id)
            .order_by(WorkflowInstanceHistory.changed_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_history(self, instance_id: UUID) -> int:
        """Count history entries for an instance."""
        query = (
            select(func.count(WorkflowInstanceHistory.id))
            .where(WorkflowInstanceHistory.instance_id == instance_id)
        )
        result = await self.db.execute(query)
        return result.scalar() or 0
