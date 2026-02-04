"""
WorkflowInstanceService for The Combine.

Per ADR-046 / WS-ADR-046-001 Phase 3.
Business logic for instance lifecycle, snapshot creation, and drift computation.
"""
from dataclasses import dataclass, field
from typing import Optional, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.repositories.workflow_instance_repository import WorkflowInstanceRepository
from app.api.models.workflow_instance import WorkflowInstance, WorkflowInstanceHistory
from app.api.services.admin_workbench_service import AdminWorkbenchService

import logging

logger = logging.getLogger(__name__)


@dataclass
class DriftSummary:
    """Computed drift between an instance and its source POW."""
    base_workflow_id: str
    base_version: str
    steps_added: List[str] = field(default_factory=list)
    steps_removed: List[str] = field(default_factory=list)
    steps_reordered: bool = False
    metadata_changed: bool = False
    is_drifted: bool = False


class WorkflowInstanceService:
    """Service for POW instance lifecycle operations."""

    def __init__(self, workbench_service: AdminWorkbenchService):
        self._workbench = workbench_service

    async def create_instance(
        self,
        db: AsyncSession,
        project_id: UUID,
        workflow_id: str,
        version: str,
        changed_by: Optional[str] = None,
    ) -> WorkflowInstance:
        """
        Create a workflow instance by snapshotting a source POW.

        Args:
            db: Database session
            project_id: Project to assign the instance to
            workflow_id: Source POW identifier in combine-config
            version: Source POW version
            changed_by: User or system identifier

        Returns:
            Created WorkflowInstance

        Raises:
            ValueError: If project already has an instance
            PackageNotFoundError: If source workflow not found
        """
        repo = WorkflowInstanceRepository(db)

        # Load source definition from combine-config
        source = self._workbench.get_workflow(workflow_id, version)
        definition = source["definition"]

        base_ref = {
            "workflow_id": workflow_id,
            "version": version,
            "pow_class": definition.get("pow_class", "reference"),
        }

        instance = await repo.create(
            project_id=project_id,
            base_workflow_ref=base_ref,
            effective_workflow=definition,
        )

        await repo.add_history(
            instance_id=instance.id,
            change_type="created",
            change_detail={
                "source_workflow_id": workflow_id,
                "source_version": version,
            },
            changed_by=changed_by,
        )

        await db.commit()
        logger.info(
            f"Created workflow instance for project {project_id} "
            f"from {workflow_id} v{version}"
        )
        return instance

    async def get_instance(
        self,
        db: AsyncSession,
        project_id: UUID,
    ) -> Optional[WorkflowInstance]:
        """Get the current workflow instance for a project."""
        repo = WorkflowInstanceRepository(db)
        return await repo.get_by_project_id(project_id)

    async def update_instance(
        self,
        db: AsyncSession,
        project_id: UUID,
        effective_workflow: dict,
        changed_by: Optional[str] = None,
    ) -> WorkflowInstance:
        """
        Update the effective workflow of an instance.

        Computes the change type by diffing old vs new steps.

        Raises:
            ValueError: If no instance exists for the project
        """
        repo = WorkflowInstanceRepository(db)
        instance = await repo.get_by_project_id(project_id)
        if not instance:
            raise ValueError(f"No workflow instance for project {project_id}")

        old_workflow = instance.effective_workflow
        change_types = self._detect_changes(old_workflow, effective_workflow)

        instance = await repo.update_effective_workflow(
            instance.id, effective_workflow
        )

        for change_type, detail in change_types:
            await repo.add_history(
                instance_id=instance.id,
                change_type=change_type,
                change_detail=detail,
                changed_by=changed_by,
            )

        await db.commit()
        return instance

    async def compute_drift(
        self,
        db: AsyncSession,
        project_id: UUID,
    ) -> DriftSummary:
        """
        Compute drift between instance and its source POW.

        Read-time operation -- nothing is stored.

        Raises:
            ValueError: If no instance exists for the project
        """
        repo = WorkflowInstanceRepository(db)
        instance = await repo.get_by_project_id(project_id)
        if not instance:
            raise ValueError(f"No workflow instance for project {project_id}")

        base_ref = instance.base_workflow_ref
        workflow_id = base_ref["workflow_id"]
        version = base_ref["version"]

        try:
            source = self._workbench.get_workflow(workflow_id, version)
            source_def = source["definition"]
        except Exception:
            # Source no longer available -- everything is drift
            return DriftSummary(
                base_workflow_id=workflow_id,
                base_version=version,
                is_drifted=True,
                metadata_changed=True,
            )

        return self._compute_drift_summary(
            base_workflow_id=workflow_id,
            base_version=version,
            source_def=source_def,
            instance_def=instance.effective_workflow,
        )

    async def get_history(
        self,
        db: AsyncSession,
        project_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[List[WorkflowInstanceHistory], int]:
        """
        Get audit trail for a project's workflow instance.

        Returns (entries, total_count).

        Raises:
            ValueError: If no instance exists for the project
        """
        repo = WorkflowInstanceRepository(db)
        instance = await repo.get_by_project_id(project_id)
        if not instance:
            raise ValueError(f"No workflow instance for project {project_id}")

        entries = await repo.get_history(instance.id, limit=limit, offset=offset)
        total = await repo.count_history(instance.id)
        return entries, total

    async def complete_instance(
        self,
        db: AsyncSession,
        project_id: UUID,
        changed_by: Optional[str] = None,
    ) -> WorkflowInstance:
        """Mark the instance as completed."""
        return await self._transition_status(
            db, project_id, "completed", changed_by
        )

    async def archive_instance(
        self,
        db: AsyncSession,
        project_id: UUID,
        changed_by: Optional[str] = None,
    ) -> WorkflowInstance:
        """Mark the instance as archived."""
        return await self._transition_status(
            db, project_id, "archived", changed_by
        )

    # =========================================================================
    # Private helpers
    # =========================================================================

    async def _transition_status(
        self,
        db: AsyncSession,
        project_id: UUID,
        new_status: str,
        changed_by: Optional[str],
    ) -> WorkflowInstance:
        repo = WorkflowInstanceRepository(db)
        instance = await repo.get_by_project_id(project_id)
        if not instance:
            raise ValueError(f"No workflow instance for project {project_id}")

        old_status = instance.status
        instance = await repo.update_status(instance.id, new_status)

        await repo.add_history(
            instance_id=instance.id,
            change_type="status_changed",
            change_detail={"from": old_status, "to": new_status},
            changed_by=changed_by,
        )

        await db.commit()
        return instance

    @staticmethod
    def _detect_changes(
        old_workflow: dict, new_workflow: dict
    ) -> list[tuple[str, dict]]:
        """Detect what changed between two workflow definitions."""
        changes = []

        old_steps = old_workflow.get("steps", [])
        new_steps = new_workflow.get("steps", [])
        old_ids = [s.get("step_id") for s in old_steps]
        new_ids = [s.get("step_id") for s in new_steps]

        added = [sid for sid in new_ids if sid not in old_ids]
        removed = [sid for sid in old_ids if sid not in new_ids]

        if added:
            changes.append(("step_added", {"step_ids": added}))
        if removed:
            changes.append(("step_removed", {"step_ids": removed}))

        # Check reorder (only among common steps)
        common_old = [sid for sid in old_ids if sid in new_ids]
        common_new = [sid for sid in new_ids if sid in old_ids]
        if common_old != common_new:
            changes.append(("step_reordered", {
                "old_order": common_old,
                "new_order": common_new,
            }))

        # Check metadata changes (name, description, tags)
        for key in ("name", "description", "tags"):
            if old_workflow.get(key) != new_workflow.get(key):
                changes.append(("metadata_changed", {
                    "field": key,
                    "old": old_workflow.get(key),
                    "new": new_workflow.get(key),
                }))
                break  # One metadata_changed entry is enough

        if not changes:
            changes.append(("updated", {"note": "Content changed"}))

        return changes

    @staticmethod
    def _compute_drift_summary(
        base_workflow_id: str,
        base_version: str,
        source_def: dict,
        instance_def: dict,
    ) -> DriftSummary:
        """Compute a DriftSummary by comparing source and instance definitions."""
        source_steps = source_def.get("steps", [])
        instance_steps = instance_def.get("steps", [])
        source_ids = [s.get("step_id") for s in source_steps]
        instance_ids = [s.get("step_id") for s in instance_steps]

        added = [sid for sid in instance_ids if sid not in source_ids]
        removed = [sid for sid in source_ids if sid not in instance_ids]

        common_source = [sid for sid in source_ids if sid in instance_ids]
        common_instance = [sid for sid in instance_ids if sid in source_ids]
        reordered = common_source != common_instance

        meta_changed = any(
            source_def.get(k) != instance_def.get(k)
            for k in ("name", "description", "tags")
        )

        is_drifted = bool(added or removed or reordered or meta_changed)

        return DriftSummary(
            base_workflow_id=base_workflow_id,
            base_version=base_version,
            steps_added=added,
            steps_removed=removed,
            steps_reordered=reordered,
            metadata_changed=meta_changed,
            is_drifted=is_drifted,
        )
